from fastapi import APIRouter, Query

from app.core.deps import AdminDependency
from app.models.membership import Membership, MembershipStatus
from app.schemas.admin import (
    MembershipApprove,
    MembershipAssign,
    MembershipListResponse,
    MembershipStatusUpdate
)
from app.services.membership import MembershipServiceDependency

router: APIRouter = APIRouter(prefix="/memberships")


@router.get(path="", response_model=list[MembershipListResponse])
async def list_memberships(
    admin: AdminDependency,
    membership_service: MembershipServiceDependency,
    status_filter: MembershipStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Membership]:
    """List all memberships (admin only)."""
    return await membership_service.get_all(status_filter=status_filter, limit=limit, offset=offset)


@router.get(path="/pending/count")
async def count_pending_memberships(
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Count pending membership applications."""
    return await membership_service.count_type(membership_status=MembershipStatus.PENDING)


@router.post(path="/{membership_id}/review")
async def review_membership(
    membership_id: str,
    review: MembershipApprove,
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Approve or reject a membership application."""
    return await membership_service.review(membership_id=membership_id, admin_id=admin.id, review=review)


@router.patch(path="/{membership_id}/status")
async def update_membership_status(
    membership_id: str,
    update: MembershipStatusUpdate,
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> dict:
    """Update membership status (suspend, expire, etc.)."""
    return await membership_service.update_status(membership_id=membership_id, update=update)


@router.post(path="/assign", response_model=MembershipListResponse, status_code=201)
async def assign_membership(
    body: MembershipAssign,
    admin: AdminDependency,
    membership_service: MembershipServiceDependency
) -> Membership:
    """Assign an active membership to an existing user (admin only)."""
    return await membership_service.assign_to_user(body=body, admin_id=admin.id)
