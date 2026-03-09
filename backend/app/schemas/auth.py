"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    middle_name: str | None = Field(None, max_length=50)
    last_name_1: str = Field(..., min_length=1, max_length=50)
    last_name_2: str | None = Field(None, max_length=50)
    rut: str = Field(..., min_length=8, max_length=12)
    phone: str | None = Field(None, max_length=20)


class UserLogin(BaseModel):
    """User login request (OAuth2 compatible)."""

    username: str  # email
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    sub: str | None = None
