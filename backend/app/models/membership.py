"""Membership and MembershipType models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.payment import FeeRate, Payment
    from app.models.user import User


class MembershipStatus(str, enum.Enum):
    """Membership status enum."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class MembershipType(Base):
    """Membership type configuration."""

    __tablename__ = "membership_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    can_vote: Mapped[bool] = mapped_column(Boolean, default=True)
    can_be_elected: Mapped[bool] = mapped_column(Boolean, default=True)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0")
    )
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_study_certificate: Mapped[bool] = mapped_column(Boolean, default=False)
    max_age: Mapped[int | None] = mapped_column(Integer)
    allows_organization: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership", back_populates="membership_type"
    )
    fee_rates: Mapped[list["FeeRate"]] = relationship(
        "FeeRate", back_populates="membership_type"
    )


class Membership(Base):
    """User membership record."""

    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    membership_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_types.id"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus), default=MembershipStatus.PENDING
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    sponsored_by_1: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    sponsored_by_2: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="memberships", foreign_keys=[user_id]
    )
    membership_type: Mapped["MembershipType"] = relationship(
        "MembershipType", back_populates="memberships"
    )
    sponsor_1: Mapped["User | None"] = relationship("User", foreign_keys=[sponsored_by_1])
    sponsor_2: Mapped["User | None"] = relationship("User", foreign_keys=[sponsored_by_2])
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="membership")

class OrganizationDetails(Base):
    """Organization details for Honorario persona jurídica."""

    __tablename__ = "organization_details"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_rut: Mapped[str | None] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="organization_details")


