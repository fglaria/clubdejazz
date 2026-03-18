from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminDependency, DbSession
from app.core.security import get_password_hash
from app.models.membership import Membership, MembershipStatus
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.admin import (
    PasswordReset,
    RoleAssignmentResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserSummary,
)
from app.schemas.user import UserResponse
from app.services.user import UserServiceDependency


router: APIRouter = APIRouter(prefix="/users")


async def _get_user_with_roles(user_id: str, db) -> User:
    """Load a user by UUID string, with roles eager-loaded. Raises 404 if not found."""
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    result = await db.execute(
        select(User)
        .where(User.id == uid)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


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
) -> list[User]:
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


@router.get(path="/{user_id}/roles", response_model=list[RoleAssignmentResponse])
async def get_user_roles(
    user_id: str,
    admin: AdminDependency,
    db: DbSession,
) -> list[RoleAssignmentResponse]:
    """Get all roles assigned to a user (admin only)."""
    user = await _get_user_with_roles(user_id, db)
    return [
        RoleAssignmentResponse(
            id=ur.role.id,
            name=ur.role.name,
            description=ur.role.description,
            assigned_at=ur.assigned_at,
        )
        for ur in user.roles
    ]


@router.post(path="/{user_id}/roles")
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Assign or revoke a role from a user (admin only)."""
    # Determine what roles the caller can manage
    caller_role_names = {ur.role.name for ur in admin.roles}
    if "SUPER_ADMIN" in caller_role_names:
        manageable = {"MEMBER", "ADMIN", "SUPER_ADMIN"}
    elif "ADMIN" in caller_role_names:
        manageable = {"ADMIN"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    # Self-modification guard — check before loading target user
    try:
        target_uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if target_uid == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar tus propios roles",
        )

    # Load target user with roles
    target = await _get_user_with_roles(user_id, db)

    # ADMIN-only callers cannot touch SUPER_ADMIN users
    target_role_names = {ur.role.name for ur in target.roles}
    if "SUPER_ADMIN" not in caller_role_names and "SUPER_ADMIN" in target_role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar roles de un Super Admin",
        )

    # Resolve the role by name
    role_result = await db.execute(
        select(Role).where(Role.name == body.role_name.upper())
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol '{body.role_name}' no encontrado",
        )

    # Check permission for this specific role
    if role.name not in manageable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para gestionar este rol",
        )

    # Find existing assignment
    existing_result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == target.id,
            UserRole.role_id == role.id,
        )
    )
    existing_ur = existing_result.scalar_one_or_none()

    if body.action == "assign":
        if existing_ur:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya tiene este rol",
            )
        new_ur = UserRole(user_id=target.id, role_id=role.id)
        db.add(new_ur)
        await db.commit()
        await db.refresh(new_ur)  # required: prevents MissingGreenlet on expired attributes
        return {
            "user_id": str(target.id),
            "role_name": role.name,
            "action": "assign",
            "message": "Rol asignado",
        }

    else:  # revoke
        if not existing_ur:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario no tiene este rol",
            )

        # Last SUPER_ADMIN guard
        if role.name == "SUPER_ADMIN":
            count = await db.scalar(
                select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id)
            )
            if count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede revocar el único Super Admin",
                )

        await db.execute(
            delete(UserRole).where(
                UserRole.user_id == target.id,
                UserRole.role_id == role.id,
            )
        )
        await db.commit()
        return {
            "user_id": str(target.id),
            "role_name": role.name,
            "action": "revoke",
            "message": "Rol revocado",
        }
