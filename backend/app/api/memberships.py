"""Membership endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser
from app.models import Membership, MembershipType
from app.schemas.membership import MembershipApply, MembershipResponse, MembershipTypeResponse
from app.services.membership_service import MembershipServiceDependency

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.get(path="/types", response_model=list[MembershipTypeResponse])
async def list_membership_types(
        membership_dependency: MembershipServiceDependency
) -> list[MembershipType]:
    """List all membership types."""
    return await membership_dependency.get_types()


@router.post(path="/apply", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_membership(
    application: MembershipApply,
    current_user: CurrentUser,
    membership_service: MembershipServiceDependency
) -> Membership:
    """Apply for a membership."""
    return await membership_service.apply(user_id=current_user.id, application=application)


@router.get(path="/me", response_model=list[MembershipResponse])
async def get_my_memberships(
    current_user: CurrentUser,
    membership_service: MembershipServiceDependency
) -> list[Membership]:
    """Get current user's memberships."""
    return await membership_service.of_user(user_id=current_user.id)


@router.get(path="/{membership_id}", response_model=MembershipResponse)
async def get_membership(
    membership_id: str,
    current_user: CurrentUser,
    membership_service: MembershipServiceDependency
) -> Membership:
    """Get a specific membership (owner only for now)."""
    membership: Membership = await membership_service.get_one(membership_id=membership_id)

    # For now, only allow owner to view (TODO: add admin check)
    if membership.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return membership
