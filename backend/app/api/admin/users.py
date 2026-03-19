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
    UserProfileUpdate,
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


@router.patch(path="/{user_id}", response_model=UserResponse)
async def update_user_profile(
    user_id: str,
    body: UserProfileUpdate,
    admin: AdminDependency,
    db: DbSession,
) -> User:
    """Update a user's personal data (admin only)."""
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Check email uniqueness
    if body.email is not None and body.email != user.email:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya está en uso")

    # Check RUT uniqueness
    if body.rut is not None and body.rut != user.rut:
        existing = await db.execute(select(User).where(User.rut == body.rut))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El RUT ya está en uso")

    # Apply non-None fields
    for field in ("first_name", "middle_name", "last_name_1", "last_name_2", "phone", "email", "rut", "is_active"):
        val = getattr(body, field)
        if val is not None:
            setattr(user, field, val)

    await db.commit()
    await db.refresh(user)
    return user


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
async def set_user_role(
    user_id: str,
    body: UserRoleUpdate,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Set a user's role, replacing any existing role (admin only)."""
    # Determine what roles the caller can manage
    caller_role_names = {ur.role.name for ur in admin.roles}
    if "SUPER_ADMIN" in caller_role_names:
        manageable = {"MEMBER", "ADMIN", "SUPER_ADMIN"}
    elif "ADMIN" in caller_role_names:
        manageable = {"MEMBER", "ADMIN"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    # Self-modification guard
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

    # Resolve the new role by name
    role_result = await db.execute(
        select(Role).where(Role.name == body.role_name.upper())
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol '{body.role_name}' no encontrado",
        )

    # Check permission for the new role
    if role.name not in manageable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para gestionar este rol",
        )

    # Last SUPER_ADMIN guard — block demoting the last super admin
    if "SUPER_ADMIN" in target_role_names and role.name != "SUPER_ADMIN":
        super_admin_role_id = next(ur.role_id for ur in target.roles if ur.role.name == "SUPER_ADMIN")
        count = await db.scalar(
            select(func.count()).select_from(UserRole).where(UserRole.role_id == super_admin_role_id)
        )
        if count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede cambiar el rol del único Super Admin",
            )

    # Atomically replace existing role with the new one
    await db.execute(delete(UserRole).where(UserRole.user_id == target.id))
    db.add(UserRole(user_id=target.id, role_id=role.id))
    await db.commit()
    return {
        "user_id": str(target.id),
        "role_name": role.name,
        "message": "Rol actualizado",
    }
