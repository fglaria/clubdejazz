"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models import User
from app.schemas import Token, UserRegister, UserResponse
from app.services.user import UserServiceDependency

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(path="/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    user_service: UserServiceDependency
) -> User:
    """Register a new user."""
    return await user_service.create_one(user_in=user_in)


@router.post(path="/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserServiceDependency
) -> Token:
    """Login and get access token."""
    return await user_service.login(user_email=form_data.username, password=form_data.password)
