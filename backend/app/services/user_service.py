
from uuid import UUID
from typing import Annotated

from fastapi import HTTPException, status, Depends
from sqlalchemy import select, Result

from app.core.deps import AsyncSession, DbSession
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas import Token, UserRegister


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, user_email: str, password: str) -> Token:
        """Login and get access token."""
        # Find user by email
        query = (
            select(User)
            .where(User.email == user_email)
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        access_token = create_access_token(subject=str(user.id))
        return Token(access_token=access_token)

    async def get_all(self,
        *,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> list[User]:
        """List all users"""
        query = (
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if active_only:
            query = query.where(User.is_active.is_(True))

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_one(self, user_id: str) -> User:
        """Get a user by user_id."""
        try:
            uid: UUID = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID",
            )

        query = (
            select(User)
            .where(User.id == uid)
        )

        result: Result = await self.db.execute(query)
        user: User | None = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user

    async def create_one(self, user_in: UserRegister) -> User:
        """Create a new user."""
        # Check if email already exists
        result: Result = await self.db.execute(
            select(User)
            .where(User.email == user_in.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if RUT already exists
        result = await self.db.execute(
            select(User)
            .where(User.rut == user_in.rut)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RUT already registered",
            )

        # Create user
        password_hash: str = get_password_hash(user_in.password)
        user: User = User(
            email=user_in.email,
            password_hash=password_hash,
            first_name=user_in.first_name,
            middle_name=user_in.middle_name,
            last_name_1=user_in.last_name_1,
            last_name_2=user_in.last_name_2,
            rut=user_in.rut,
            phone=user_in.phone,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def update_status(self,
        *,
        user_id: str,
        self_id: UUID,
        is_active: bool
    ) -> dict:
        """Activate or deactivate a user by user_id."""
        user: User = await self.get_one(user_id=user_id)

        if user.id == self_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own status",
            )

        user.is_active = is_active
        await self.db.commit()

        message: str = f"User {'activated' if is_active else 'deactivated'} successfully"
        return {
            "id": str(user.id),
            "is_active": user.is_active,
            "message": message,
        }


def get_user_service(db: DbSession) -> UserService:
    """Get User Service"""
    return UserService(db=db)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
