from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.deps import AdminDependency, DbSession
from app.models.membership import Membership, MembershipStatus, MembershipType
from app.schemas.admin import (
    MembershipApprove,
    MembershipListResponse,
    MembershipStatusUpdate
)

router: APIRouter = APIRouter(prefix="/memberships")


@router.get(path="", response_model=list[MembershipListResponse])
async def list_memberships(
    admin: AdminDependency,
    db: DbSession,
    status_filter: MembershipStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List all memberships (admin only)."""
    query = (
        select(Membership)
        .options(
            selectinload(Membership.user),
            selectinload(Membership.membership_type),
        )
        .order_by(Membership.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter:
        query = query.where(Membership.status == status_filter)

    result = await db.execute(query)
    memberships = result.scalars().all()

    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "user_email": m.user.email,
            "user_full_name": m.user.full_name,
            "membership_type_code": m.membership_type.code,
            "membership_type_name": m.membership_type.name,
            "status": m.status,
            "start_date": m.start_date,
            "end_date": m.end_date,
            "created_at": m.created_at,
        }
        for m in memberships
    ]


@router.get("/pending/count")
async def count_pending_memberships(
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Count pending membership applications."""
    result = await db.execute(
        select(func.count(Membership.id))
        .where(Membership.status == MembershipStatus.PENDING)
    )
    count = result.scalar_one()
    return {"count": count}


@router.post("/{membership_id}/review")
async def review_membership(
    membership_id: str,
    review: MembershipApprove,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Approve or reject a membership application."""
    from uuid import UUID

    try:
        mid = UUID(membership_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid membership ID",
        )

    result = await db.execute(
        select(Membership)
        .where(Membership.id == mid)
        .options(selectinload(Membership.membership_type))
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    if membership.status != MembershipStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Membership is not pending (current: {membership.status.value})",
        )

    if review.action == "approve":
        membership.status = MembershipStatus.ACTIVE
        membership.approved_by = admin.id
        membership.approved_at = datetime.now()
    else:
        membership.status = MembershipStatus.CANCELLED

    if review.notes:
        existing_notes = membership.notes or ""
        membership.notes = f"{existing_notes}\n[Admin] {review.notes}".strip()

    await db.commit()

    return {
        "id": str(membership.id),
        "status": membership.status.value,
        "message": f"Membership {review.action}d successfully",
    }


@router.patch("/{membership_id}/status")
async def update_membership_status(
    membership_id: str,
    update: MembershipStatusUpdate,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Update membership status (suspend, expire, etc.)."""
    from uuid import UUID

    try:
        mid = UUID(membership_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid membership ID",
        )

    result = await db.execute(
        select(Membership).where(Membership.id == mid)
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    old_status = membership.status
    membership.status = update.status

    if update.notes:
        existing_notes = membership.notes or ""
        membership.notes = f"{existing_notes}\n[Admin] {old_status.value} -> {update.status.value}: {update.notes}".strip()

    await db.commit()

    return {
        "id": str(membership.id),
        "old_status": old_status.value,
        "new_status": membership.status.value,
    }
