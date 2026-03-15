#!/usr/bin/env python3
"""
Import SOCIOS_CCCJC members from CSV files into the intranet database.

Idempotent: members already in the DB (matched by RUT) are skipped.
Payments already recorded (matched by membership + period) are skipped.

Usage:
    # From anywhere — auto-loads backend/.env
    python intranet/import_members.py

    # Dry run (parse + validate, no DB writes)
    python intranet/import_members.py --dry-run

    # Explicit CSV dir or DB URL
    python intranet/import_members.py --csv-dir /path/to/csvs --database-url postgresql://...

CSV files expected in --csv-dir:
    - "SOCIOS_CCCJC.xlsx - FUNDADORES.csv"
    - "SOCIOS_CCCJC.xlsx - NUMERARIOS.csv"
    - "SOCIOS_CCCJC.xlsx - PAGO CUOTAS.csv"
"""
import argparse
import asyncio
import csv
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add backend to path so we can import app.models
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.membership import Membership, MembershipStatus, MembershipType
from app.models.payment import FeeRate, FeeType, Payment, PaymentMethod, PaymentStatus
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def normalize_rut(raw: str) -> str:
    """Normalize RUT to 'XXXXXXXX-X' (no dots, uppercase K)."""
    rut = raw.strip().upper().replace(".", "")
    rut = re.sub(r"[^\dKk-]", "", rut)
    return rut


def parse_name(nombres: str) -> tuple[str, str | None]:
    """Split NOMBRES into (first_name, middle_name).

    'CAMILA ANGÉLICA' -> ('Camila', 'Angélica')
    'JUAN'            -> ('Juan', None)
    """
    parts = nombres.strip().split()
    if not parts:
        return ("", None)
    first = parts[0].title()
    middle = " ".join(p.title() for p in parts[1:]) if len(parts) > 1 else None
    return first, middle


def temp_password(rut: str) -> str:
    """Temporary password: RUT digits + verifier (no dots/dash)."""
    return re.sub(r"[^0-9Kk]", "", rut)


def _parse_date(s: str, fallback: date) -> date:
    for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return fallback


def parse_fundadores(filepath: Path) -> list[dict]:
    """Parse FUNDADORES CSV into a list of member dicts."""
    members = []
    with open(filepath, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip().isdigit():
                continue
            corr = int(row[0])
            apellido_pat = row[1].strip().title()
            apellido_mat = row[2].strip().title()
            nombres = row[3].strip()
            rut = row[4].strip()
            email = row[5].strip() or None
            phone = row[6].strip() or None
            fecha = row[7].strip()

            first_name, middle_name = parse_name(nombres)
            members.append({
                "corr": corr,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name_1": apellido_pat,
                "last_name_2": apellido_mat,
                "rut": normalize_rut(rut),
                "rut_raw": rut,
                "email": email,
                "phone": phone,
                "membership_type": "FUNDADOR",
                "start_date": _parse_date(fecha, date(2022, 8, 19)),
                "skip_reason": None,
            })
    return members


def parse_numerarios(filepath: Path) -> list[dict]:
    """Parse NUMERARIOS CSV into a list of member dicts."""
    members = []
    with open(filepath, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip().isdigit():
                continue
            corr = int(row[0])
            apellido_pat = row[1].strip().title()
            apellido_mat = row[2].strip().title()
            nombres = row[3].strip()
            rut = row[4].strip()
            email = row[5].strip() or None
            phone = row[6].strip() or None
            fecha = row[7].strip()
            notes = row[8].strip() if len(row) > 8 else ""

            first_name, middle_name = parse_name(nombres)
            skip_reason = f"duplicate: {notes}" if "DOBLE" in notes.upper() else None

            members.append({
                "corr": corr,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name_1": apellido_pat,
                "last_name_2": apellido_mat,
                "rut": normalize_rut(rut),
                "rut_raw": rut,
                "email": email,
                "phone": phone,
                "membership_type": "NUMERARIO",
                "start_date": _parse_date(fecha, date(2023, 5, 16)),
                "skip_reason": skip_reason,
            })
    return members


# Maps lowercase column header -> (year, month)
_PAYMENT_COLS: dict[str, tuple[int, int]] = {
    "nov 2023": (2023, 11), "dic 2023": (2023, 12),
    "enero 2024": (2024, 1), "febrero 2024": (2024, 2),
    "marzo 2024": (2024, 3), "abril 2024": (2024, 4),
    "mayo 2024": (2024, 5), "junio 2024": (2024, 6),
    "julio 2024": (2024, 7), "agosto 2024": (2024, 8),
    "sept 2024": (2024, 9), "oct 2024": (2024, 10),
    "nov 2024": (2024, 11), "dic 2024": (2024, 12),
}


def parse_payments(filepath: Path) -> dict[str, list[tuple[int, int, Decimal]]]:
    """Parse PAGO CUOTAS CSV.

    Returns: rut_normalized -> [(year, month, amount_clp), ...]
    Only includes members with at least one payment.
    """
    with open(filepath, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    # Find header row and build col_index -> (year, month) map
    col_map: dict[int, tuple[int, int]] = {}
    header_idx = None
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            key = cell.strip().lower()
            if key in _PAYMENT_COLS:
                col_map[j] = _PAYMENT_COLS[key]
                header_idx = i

    if header_idx is None:
        print("WARNING: No payment column headers found in PAGO CUOTAS file.")
        return {}

    result: dict[str, list[tuple[int, int, Decimal]]] = {}
    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip().isdigit():
            continue
        rut_raw = row[4].strip() if len(row) > 4 else ""
        if not rut_raw:
            continue
        rut = normalize_rut(rut_raw)

        payments = []
        for col_idx, (year, month) in col_map.items():
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip()
            if not cell:
                continue
            # Parse "$5,000" -> 5000
            amount_str = re.sub(r"[^\d]", "", cell)
            if amount_str:
                payments.append((year, month, Decimal(amount_str)))

        if payments:
            result[rut] = payments

    return result


# ---------------------------------------------------------------------------
# Database import
# ---------------------------------------------------------------------------

async def get_membership_type(session: AsyncSession, code: str) -> MembershipType:
    result = await session.execute(
        select(MembershipType).where(MembershipType.code == code)
    )
    mt = result.scalar_one_or_none()
    if mt is None:
        raise RuntimeError(
            f"Membership type '{code}' not found. Ensure seed data is loaded first."
        )
    return mt


async def get_or_create_fee_rate(
    session: AsyncSession, membership_type: MembershipType
) -> FeeRate:
    """Get or create a $5,000 CLP/month historical fee rate (effective Nov 2023)."""
    effective_from = date(2023, 11, 1)
    result = await session.execute(
        select(FeeRate).where(
            FeeRate.membership_type_id == membership_type.id,
            FeeRate.fee_type == FeeType.MONTHLY,
            FeeRate.effective_from == effective_from,
        )
    )
    fee_rate = result.scalar_one_or_none()
    if fee_rate is None:
        fee_rate = FeeRate(
            fee_type=FeeType.MONTHLY,
            membership_type_id=membership_type.id,
            amount_utm=Decimal("0.10"),
            amount_clp=Decimal("5000"),
            effective_from=effective_from,
            reason="Tarifa histórica importada desde planilla SOCIOS_CCCJC",
        )
        session.add(fee_rate)
        await session.flush()
        print(f"  [fee_rate] Created $5,000/month for {membership_type.code}")
    return fee_rate


def _to_ascii_slug(text: str) -> str:
    """Convert accented text to lowercase ASCII slug (e.g. 'Rayén' -> 'rayen')."""
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-zA-Z0-9]", "", ascii_only).lower()


def _make_email_placeholder(first_name: str, last_name_1: str) -> str:
    """Generate placeholder email: firstname_lastname@noemail.com"""
    slug_first = _to_ascii_slug(first_name)
    slug_last = _to_ascii_slug(last_name_1)
    return f"{slug_first}_{slug_last}@noemail.com"


async def import_member(
    session: AsyncSession,
    member: dict,
    membership_type: MembershipType,
    dry_run: bool,
) -> tuple[User | None, Membership | None, str]:
    """Upsert a single member. Returns (user, membership, status)."""
    rut = member["rut"]

    # Already exists?
    result = await session.execute(select(User).where(User.rut == rut))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        result = await session.execute(
            select(Membership).where(
                Membership.user_id == existing_user.id,
                Membership.membership_type_id == membership_type.id,
            )
        )
        existing_membership = result.scalar_one_or_none()
        return existing_user, existing_membership, "skipped"

    # Resolve email
    email = member["email"] or _make_email_placeholder(
        member["first_name"], member["last_name_1"]
    )

    # Guard against duplicate email (rare edge case)
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        rut_digits = re.sub(r"[^0-9Kk]", "", rut)
        email = f"{email.split('@')[0]}.{rut_digits}@noemail.com"

    password = temp_password(rut)
    password_hash = pwd_context.hash(password[:72])

    user = User(
        email=email,
        password_hash=password_hash,
        first_name=member["first_name"],
        middle_name=member["middle_name"],
        last_name_1=member["last_name_1"],
        last_name_2=member["last_name_2"],
        rut=rut,
        member_number=member.get("corr"),
        phone=member["phone"],
        is_active=True,
        email_verified=False,
    )

    start_dt = datetime.combine(member["start_date"], datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    membership = Membership(
        membership_type_id=membership_type.id,
        status=MembershipStatus.ACTIVE,
        start_date=member["start_date"],
        approved_at=start_dt,
        notes="Importado desde planilla SOCIOS_CCCJC",
    )

    if not dry_run:
        session.add(user)
        await session.flush()
        membership.user_id = user.id
        session.add(membership)
        await session.flush()

    return user, membership if not dry_run else None, "created"


async def import_payments_for_member(
    session: AsyncSession,
    membership: Membership,
    fee_rate: FeeRate,
    payment_records: list[tuple[int, int, Decimal]],
) -> int:
    """Add payment records for a member. Returns count of new records."""
    count = 0
    for year, month, amount in payment_records:
        result = await session.execute(
            select(Payment).where(
                Payment.membership_id == membership.id,
                Payment.period_year == year,
                Payment.period_month == month,
            )
        )
        if result.scalar_one_or_none():
            continue  # already imported
        session.add(
            Payment(
                membership_id=membership.id,
                fee_rate_id=fee_rate.id,
                payment_method=PaymentMethod.BANK_TRANSFER,
                amount_clp=amount,
                payment_date=date(year, month, 1),
                period_month=month,
                period_year=year,
                status=PaymentStatus.CONFIRMED,
                notes="Importado desde planilla SOCIOS_CCCJC",
            )
        )
        count += 1
    if count:
        await session.flush()
    return count


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_import(database_url: str, csv_dir: Path, dry_run: bool) -> None:
    if database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_url = database_url

    engine = create_async_engine(async_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    fundadores_path = csv_dir / "SOCIOS_CCCJC.xlsx - FUNDADORES.csv"
    numerarios_path = csv_dir / "SOCIOS_CCCJC.xlsx - NUMERARIOS.csv"
    payments_path   = csv_dir / "SOCIOS_CCCJC.xlsx - PAGO CUOTAS.csv"

    for p in (fundadores_path, numerarios_path, payments_path):
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)

    print("Parsing CSV files...")
    fundadores   = parse_fundadores(fundadores_path)
    numerarios   = parse_numerarios(numerarios_path)
    payment_data = parse_payments(payments_path)

    print(f"  Fundadores:                {len(fundadores)}")
    print(f"  Numerarios:                {len(numerarios)}")
    print(f"  Members with payments:     {len(payment_data)}")

    if dry_run:
        print("\n  ⚠️  DRY RUN — no changes will be written to DB\n")

    stats = {"created": 0, "skipped": 0, "errors": 0, "payments": 0}

    async with session_maker() as session:
        async with session.begin():
            fundador_type  = await get_membership_type(session, "FUNDADOR")
            numerario_type = await get_membership_type(session, "NUMERARIO")

            fundador_fee  = await get_or_create_fee_rate(session, fundador_type)
            numerario_fee = await get_or_create_fee_rate(session, numerario_type)

            fee_rates = {"FUNDADOR": fundador_fee, "NUMERARIO": numerario_fee}
            mtypes    = {"FUNDADOR": fundador_type, "NUMERARIO": numerario_type}

            for member in fundadores + numerarios:
                if member.get("skip_reason"):
                    print(
                        f"  SKIP  #{member['corr']:3d} "
                        f"{member['last_name_1']}, {member['first_name']}"
                        f" — {member['skip_reason']}"
                    )
                    stats["skipped"] += 1
                    continue

                mtype = mtypes[member["membership_type"]]
                try:
                    user, membership, status = await import_member(
                        session, member, mtype, dry_run
                    )

                    tag = "✓" if status == "created" else "·"
                    print(
                        f"  {tag} {status:8s} #{member['corr']:3d} "
                        f"{member['last_name_1']}, {member['first_name']}"
                        f" [{member['membership_type'][:3]}]"
                        + (f"  pwd: {temp_password(member['rut'])}" if status == "created" else "")
                    )

                    if status == "created":
                        stats["created"] += 1
                    else:
                        stats["skipped"] += 1

                    # Import payments (only when we have a real membership id)
                    if membership and not dry_run and member["rut"] in payment_data:
                        fee_rate = fee_rates[member["membership_type"]]
                        n = await import_payments_for_member(
                            session, membership, fee_rate, payment_data[member["rut"]]
                        )
                        stats["payments"] += n
                        if n:
                            print(f"    └─ {n} payment(s) added")

                except Exception as e:
                    print(f"  ERROR #{member['corr']} {member['last_name_1']}: {e}")
                    stats["errors"] += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  Created:  {stats['created']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Payments: {stats['payments']}")
    print(f"  Errors:   {stats['errors']}")

    await engine.dispose()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _load_env_file(path: Path) -> dict[str, str]:
    """Minimal .env parser (no external deps)."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("'\"")
    return env


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import SOCIOS_CCCJC members from CSV files into the intranet DB."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing the CSV files (default: same dir as this script)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without writing to the database",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL connection URL (overrides DATABASE_URL env var and .env file)",
    )
    args = parser.parse_args()

    # Resolve DATABASE_URL: CLI arg > env var > backend/.env file
    database_url = (
        args.database_url
        or os.environ.get("DATABASE_URL")
        or _load_env_file(Path(__file__).parent / "backend" / ".env").get("DATABASE_URL")
    )

    if not database_url:
        print(
            "ERROR: DATABASE_URL not set.\n"
            "  Set it via --database-url, the DATABASE_URL env var, "
            "or backend/.env"
        )
        sys.exit(1)

    asyncio.run(run_import(database_url, args.csv_dir, args.dry_run))


if __name__ == "__main__":
    main()
