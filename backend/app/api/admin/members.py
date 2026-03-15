"""Admin member creation endpoint."""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminDependency, DbSession
from app.core.security import get_password_hash
from app.models.membership import Membership, MembershipStatus, MembershipType
from app.models.user import User
from app.schemas.admin import AdminMemberCreate, MembershipListResponse

router: APIRouter = APIRouter(prefix="/members")


@router.post(path="", response_model=MembershipListResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    body: AdminMemberCreate,
    admin: AdminDependency,
    db: DbSession,
) -> Membership:
    """Create a new user with an active membership (admin only)."""

    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya registrado")

    # Check RUT uniqueness
    result = await db.execute(select(User).where(User.rut == body.rut))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RUT ya registrado")

    # Resolve membership type
    result = await db.execute(
        select(MembershipType).where(MembershipType.code == body.membership_type_code.upper())
    )
    membership_type = result.scalar_one_or_none()
    if not membership_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de membresía no válido")

    # Create user (flush to get user.id without committing)
    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        first_name=body.first_name,
        middle_name=body.middle_name,
        last_name_1=body.last_name_1,
        last_name_2=body.last_name_2,
        rut=body.rut,
        phone=body.phone,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()  # populates user.id, no commit yet

    # Create active membership
    membership = Membership(
        user_id=user.id,
        membership_type_id=membership_type.id,
        status=MembershipStatus.ACTIVE,
        start_date=date.today(),
        approved_by=admin.id,
        approved_at=datetime.now(),
    )
    db.add(membership)
    await db.commit()  # single commit — atomic

    # Re-query with relationships loaded (required for async SQLAlchemy)
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership.id)
        .options(
            selectinload(Membership.user),
            selectinload(Membership.membership_type),
        )
    )
    return result.scalar_one()
