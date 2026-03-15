from fastapi import APIRouter, HTTPException, Query, status

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminDependency, DbSession
from app.models.membership import Membership, MembershipStatus, MembershipType
from app.models.user import User
from app.schemas.admin import MembershipApprove, MembershipAssign, MembershipListResponse, MembershipStatusUpdate
from app.services.membership_service import MembershipServiceDependency

router: APIRouter = APIRouter(prefix="/memberships")


@router.get(path="", response_model=list[MembershipListResponse])
async def list_memberships(
    admin: AdminDependency,
    membership_service: MembershipServiceDependency,
    status_filter: MembershipStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Membership]:
    """List all memberships (admin only)."""
    return await membership_service.get_all(status_filter=status_filter, limit=limit, offset=offset)


@router.get("/pending/count")
async def count_pending_memberships(
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Count pending membership applications."""
    return await membership_service.count_type(membership_status=MembershipStatus.PENDING)


@router.post("/{membership_id}/review")
async def review_membership(
    membership_id: str,
    review: MembershipApprove,
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Approve or reject a membership application."""
    return await membership_service.review(membership_id=membership_id, admin_id=admin.id, review=review)


@router.patch("/{membership_id}/status")
async def update_membership_status(
    membership_id: str,
    update: MembershipStatusUpdate,
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Update membership status (suspend, expire, etc.)."""
    return await membership_service.update_status(membership_id=membership_id, update=update)


@router.post("/assign", response_model=MembershipListResponse, status_code=201)
async def assign_membership(
    body: MembershipAssign,
    admin: AdminDependency,
    db: DbSession,
) -> Membership:
    """Assign an active membership to an existing user (admin only)."""

    # Fetch user
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Check no ACTIVE or PENDING membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == body.user_id,
            Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.PENDING]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya tiene una membresía activa o pendiente",
        )

    # Resolve membership type
    result = await db.execute(
        select(MembershipType).where(MembershipType.code == body.membership_type_code.upper())
    )
    membership_type = result.scalar_one_or_none()
    if not membership_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de membresía no válido")

    # Create active membership
    membership = Membership(
        user_id=body.user_id,
        membership_type_id=membership_type.id,
        status=MembershipStatus.ACTIVE,
        start_date=date.today(),
        approved_by=admin.id,
        approved_at=datetime.now(),
    )
    db.add(membership)
    await db.commit()

    # Re-query with relationships loaded
    result = await db.execute(
        select(Membership)
        .where(Membership.id == membership.id)
        .options(
            selectinload(Membership.user),
            selectinload(Membership.membership_type),
        )
    )
    return result.scalar_one()
