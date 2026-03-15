from fastapi import APIRouter, Query

from sqlalchemy import select
from app.core.deps import AdminDependency, DbSession
from app.models.membership import Membership, MembershipStatus
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.admin import UserStatusUpdate, PasswordReset, UserSummary
from app.core.security import get_password_hash
from app.services.user import UserServiceDependency


router: APIRouter = APIRouter(prefix="/users")


@router.get(path="", response_model=list[UserResponse])
async def list_users(
    admin: AdminDependency,
    user_service: UserServiceDependency,
    active_only: bool = Query(False),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    """List all users (admin only)."""
    return await user_service.get_all(active_only=active_only, limit=limit, offset=offset)


@router.get(path="/without-membership", response_model=list[UserSummary])
async def list_users_without_membership(
    admin: AdminDependency,
    db: DbSession,
) -> list[UserSummary]:
    """List active users with no ACTIVE or PENDING membership (admin only)."""
    subquery = (
        select(Membership.user_id)
        .where(Membership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.PENDING]))
    )
    result = await db.execute(
        select(User)
        .where(User.is_active.is_(True))
        .where(~User.id.in_(subquery))
        .order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(path="/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin: AdminDependency,
    user_service: UserServiceDependency
) -> User:
    """Get a specific user (admin only)."""
    return await user_service.get_one(user_id=user_id)


@router.patch(path="/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: UserStatusUpdate,
    admin: AdminDependency,
    user_service: UserServiceDependency
) -> dict:
    """Activate or deactivate a user (admin only)."""
    return await user_service.update_status(user_id=user_id, self_id=admin.id, is_active=body.is_active)


@router.patch(path="/{user_id}/password")
async def reset_user_password(
    user_id: str,
    body: PasswordReset,
    admin: AdminDependency,
    user_service: UserServiceDependency,
) -> dict:
    """Reset a user's password (admin only)."""
    user = await user_service.get_one(user_id=user_id)
    user.password_hash = get_password_hash(body.new_password)
    await user_service.db.commit()
    return {"user_id": str(user.id), "message": "Contraseña actualizada"}
