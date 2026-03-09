"""Membership schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.membership import MembershipStatus


class MembershipTypeResponse(BaseModel):
    """Membership type response."""

    id: UUID
    code: str
    name: str
    description: str | None
    can_vote: bool
    can_be_elected: bool
    discount_percentage: Decimal
    is_free: bool
    requires_study_certificate: bool
    max_age: int | None
    allows_organization: bool

    model_config = {"from_attributes": True}


class MembershipApply(BaseModel):
    """Membership application request."""

    membership_type_code: str = Field(..., description="NUMERARIO, HONORARIO, FUNDADOR, ESTUDIANTE")
    sponsored_by_1: UUID | None = Field(None, description="First sponsor user ID")
    sponsored_by_2: UUID | None = Field(None, description="Second sponsor user ID")
    notes: str | None = None


class MembershipResponse(BaseModel):
    """Membership response."""

    id: UUID
    user_id: UUID
    membership_type: MembershipTypeResponse
    status: MembershipStatus
    start_date: date
    end_date: date | None
    sponsored_by_1: UUID | None
    sponsored_by_2: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeeRateResponse(BaseModel):
    """Fee rate response."""

    id: UUID
    fee_type: str
    membership_type_id: UUID
    amount_utm: Decimal
    utm_to_clp_rate: Decimal | None
    amount_clp: Decimal | None
    effective_from: date
    effective_until: date | None

    model_config = {"from_attributes": True}
