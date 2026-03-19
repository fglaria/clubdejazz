"""Admin-specific schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.membership import MembershipStatus
from app.models.payment import FeeType, PaymentMethod, PaymentStatus
from app.schemas.user import UserUpdate


# === Membership Admin Schemas ===

class MembershipApprove(BaseModel):
    """Approve or reject membership application."""

    action: str = Field(..., pattern="^(approve|reject)$")
    notes: str | None = None


class MembershipStatusUpdate(BaseModel):
    """Update membership status."""

    status: MembershipStatus
    notes: str | None = None


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None = None
    member_number: int | None = None

    model_config = {"from_attributes": True}


class UserSummaryWithRoles(UserSummary):
    """UserSummary extended with role names. Used in membership list only."""
    roles: list[str] = []

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: list) -> list[str]:
        if v and hasattr(v[0], "role"):
            return [ur.role.name for ur in v]
        return v


class UserStatusUpdate(BaseModel):
    is_active: bool


class MembershipTypeSummary(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class MembershipListResponse(BaseModel):
    """Membership with user info for admin list."""

    id: UUID
    user_id: UUID
    user: UserSummaryWithRoles
    membership_type: MembershipTypeSummary
    status: MembershipStatus
    start_date: date
    end_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


# === Payment Admin Schemas ===

class PaymentCreate(BaseModel):
    """Record a new payment (admin)."""

    membership_id: UUID
    fee_rate_id: UUID
    payment_method: PaymentMethod
    amount_clp: Decimal = Field(..., gt=0)
    payment_date: date
    period_month: int | None = Field(None, ge=1, le=12)
    period_year: int | None = Field(None, ge=2020, le=2100)
    gateway_transaction_id: str | None = None
    transfer_proof_url: str | None = None
    notes: str | None = None


class PaymentConfirm(BaseModel):
    """Confirm or reject a pending payment."""

    action: str = Field(..., pattern="^(confirm|reject)$")
    notes: str | None = None


class PaymentConfirmResponse(BaseModel):
    id: str
    status: str
    message: str


class FeeRateSummary(BaseModel):
    fee_type: FeeType

    model_config = {"from_attributes": True}


class PaymentMembershipSummary(BaseModel):
    user: UserSummary
    start_date: date

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    """Payment response with related info."""

    id: UUID
    membership_id: UUID
    membership: PaymentMembershipSummary
    fee_rate: FeeRateSummary
    amount_clp: Decimal
    payment_method: PaymentMethod
    payment_date: date
    period_month: int | None
    period_year: int | None
    status: PaymentStatus
    gateway_transaction_id: str | None
    transfer_proof_url: str | None
    notes: str | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# === Event Admin Schemas ===

class EventCreate(BaseModel):
    """Create a new event."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    event_date: datetime
    location: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    image_url: str | None = Field(None, max_length=500)
    is_published: bool = False


class EventUpdate(BaseModel):
    """Update an event."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    event_date: datetime | None = None
    location: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    image_url: str | None = Field(None, max_length=500)
    is_published: bool | None = None


# === Fee Rate Admin Schemas ===

class FeeRateCreate(BaseModel):
    """Create a new fee rate."""

    fee_type: FeeType
    membership_type_id: UUID
    amount_utm: Decimal = Field(..., gt=0)
    utm_to_clp_rate: Decimal | None = Field(None, gt=0)
    amount_clp: Decimal | None = Field(None, gt=0)
    effective_from: date
    effective_until: date | None = None
    reason: str | None = None


# === Member Admin Schemas ===

class AdminMemberCreate(BaseModel):
    """Create a new user + active membership (admin)."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name_1: str = Field(..., min_length=1, max_length=50)
    rut: str = Field(..., min_length=8, max_length=12)
    middle_name: str | None = Field(None, max_length=50)
    last_name_2: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    membership_type_code: str = Field(..., description="NUMERARIO, HONORARIO, FUNDADOR, ESTUDIANTE")


class PasswordReset(BaseModel):
    """Reset a user's password (admin)."""

    new_password: str = Field(..., min_length=8)


class MembershipAssign(BaseModel):
    """Assign an existing user to an active membership (admin)."""

    user_id: UUID
    membership_type_code: str = Field(..., description="NUMERARIO, HONORARIO, FUNDADOR, ESTUDIANTE")


# === Role Admin Schemas ===

class RoleAssignmentResponse(BaseModel):
    """Role info as assigned to a user. Built manually — not from_attributes on UserRole."""
    id: UUID           # Role.id
    name: str          # Role.name
    description: str | None  # Role.description
    assigned_at: datetime    # UserRole.assigned_at


class UserRoleUpdate(BaseModel):
    """Set a user's role (exclusive — replaces any existing role)."""
    role_name: str


# === User Profile Update Schema ===

class UserProfileUpdate(UserUpdate):
    """Update user profile fields (admin). Extends UserUpdate with admin-only fields."""
    email: EmailStr | None = None
    rut: str | None = Field(None, min_length=8, max_length=12)
    is_active: bool | None = None
