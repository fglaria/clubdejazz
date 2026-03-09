"""Fee rate endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DbSession
from app.models import FeeRate
from app.schemas.membership import FeeRateResponse

router = APIRouter(prefix="/fee-rates", tags=["fee-rates"])


@router.get("/current", response_model=list[FeeRateResponse])
async def get_current_fee_rates(db: DbSession) -> list[FeeRate]:
    """Get current active fee rates."""
    today = date.today()
    result = await db.execute(
        select(FeeRate)
        .where(FeeRate.effective_from <= today)
        .where((FeeRate.effective_until.is_(None)) | (FeeRate.effective_until >= today))
        .order_by(FeeRate.membership_type_id, FeeRate.fee_type)
    )
    return list(result.scalars().all())


@router.get("/history/{membership_type_id}", response_model=list[FeeRateResponse])
async def get_fee_rate_history(
    membership_type_id: str,
    db: DbSession,
) -> list[FeeRate]:
    """Get fee rate history for a membership type."""
    from uuid import UUID

    try:
        mt_id = UUID(membership_type_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid membership type ID")

    result = await db.execute(
        select(FeeRate)
        .where(FeeRate.membership_type_id == mt_id)
        .order_by(FeeRate.effective_from.desc())
    )
    return list(result.scalars().all())
