"""User endpoints."""

from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas import UserMe, UserUpdate
from app.services.user import UserServiceDependency

router = APIRouter(prefix="/users", tags=["users"])


@router.get(path="/me", response_model=UserMe)
async def get_me(current_user: CurrentUser) -> UserMe:
    """Get current user profile."""
    return UserMe(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        middle_name=current_user.middle_name,
        last_name_1=current_user.last_name_1,
        last_name_2=current_user.last_name_2,
        rut=current_user.rut,
        phone=current_user.phone,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        full_name=current_user.full_name,
    )


@router.put(path="/me", response_model=UserMe)
async def update_me(
    user_in: UserUpdate,
    current_user: CurrentUser,
    user_service: UserServiceDependency,
) -> UserMe:
    """Update current user profile."""
    current_user = user_service.update_one(user_in=user_in, current_user=current_user)

    return UserMe(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        middle_name=current_user.middle_name,
        last_name_1=current_user.last_name_1,
        last_name_2=current_user.last_name_2,
        rut=current_user.rut,
        phone=current_user.phone,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        full_name=current_user.full_name,
    )
