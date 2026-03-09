"""User schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    middle_name: str | None = Field(None, max_length=50)
    last_name_1: str = Field(..., min_length=1, max_length=50)
    last_name_2: str | None = Field(None, max_length=50)
    rut: str = Field(..., min_length=8, max_length=12)
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update schema (all fields optional)."""

    first_name: str | None = Field(None, min_length=1, max_length=50)
    middle_name: str | None = Field(None, max_length=50)
    last_name_1: str | None = Field(None, min_length=1, max_length=50)
    last_name_2: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)


class UserResponse(UserBase):
    """User response schema."""

    id: UUID
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMe(UserResponse):
    """Current user response with additional info."""

    full_name: str

    model_config = {"from_attributes": True}
