"""Membership endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Membership, MembershipStatus, MembershipType
from app.schemas.membership import MembershipApply, MembershipResponse, MembershipTypeResponse

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.get("/types", response_model=list[MembershipTypeResponse])
async def list_membership_types(db: DbSession) -> list[MembershipType]:
    """List all membership types."""
    result = await db.execute(select(MembershipType))
    return list(result.scalars().all())


@router.post("/apply", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_membership(
    application: MembershipApply,
    current_user: CurrentUser,
    db: DbSession,
) -> Membership:
    """Apply for a membership."""
    # Check if user already has an active or pending membership
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .where(Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.PENDING]))
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active or pending membership",
        )

    # Get membership type
    result = await db.execute(
        select(MembershipType).where(MembershipType.code == application.membership_type_code.upper())
    )
    membership_type = result.scalar_one_or_none()
    if not membership_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Membership type '{application.membership_type_code}' not found",
        )

    # Create membership application
    membership = Membership(
        user_id=current_user.id,
        membership_type_id=membership_type.id,
        status=MembershipStatus.PENDING,
        start_date=date.today(),
        sponsored_by_1=application.sponsored_by_1,
        sponsored_by_2=application.sponsored_by_2,
        notes=application.notes,
    )
    db.add(membership)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership.id)
        .options(selectinload(Membership.membership_type))
    )
    return result.scalar_one()


@router.get("/me", response_model=list[MembershipResponse])
async def get_my_memberships(
    current_user: CurrentUser,
    db: DbSession,
) -> list[Membership]:
    """Get current user's memberships."""
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .options(selectinload(Membership.membership_type))
        .order_by(Membership.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{membership_id}", response_model=MembershipResponse)
async def get_membership(
    membership_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> Membership:
    """Get a specific membership (owner only for now)."""
    from uuid import UUID

    try:
        mid = UUID(membership_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid membership ID")

    result = await db.execute(
        select(Membership)
        .where(Membership.id == mid)
        .options(selectinload(Membership.membership_type))
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    # For now, only allow owner to view (TODO: add admin check)
    if membership.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return membership
