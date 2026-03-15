from fastapi import APIRouter, Query

from app.core.deps import AdminDependency
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.admin import UserStatusUpdate
from app.services.user_service import UserServiceDependency


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
