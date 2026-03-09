"""Payment and FeeRate models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.models.membership import Membership, MembershipType
    from app.models.user import User


class FeeType(str, enum.Enum):
    """Fee type enum."""

    MONTHLY = "MONTHLY"
    REGISTRATION = "REGISTRATION"
    EXTRAORDINARY = "EXTRAORDINARY"


class PaymentMethod(str, enum.Enum):
    """Payment method enum."""

    GATEWAY = "GATEWAY"
    BANK_TRANSFER = "BANK_TRANSFER"


class PaymentStatus(str, enum.Enum):
    """Payment status enum."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"


class FeeRate(Base):
    """Historical fee rate configuration."""

    __tablename__ = "fee_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fee_type: Mapped[FeeType] = mapped_column(Enum(FeeType), nullable=False)
    membership_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_types.id"), nullable=False
    )
    amount_utm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    utm_to_clp_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    amount_clp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    membership_type: Mapped["MembershipType"] = relationship(
        "MembershipType", back_populates="fee_rates"
    )
    creator: Mapped["User | None"] = relationship("User")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="fee_rate")


class Payment(Base):
    """Payment record."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id"), nullable=False
    )
    fee_rate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_rates.id"), nullable=False
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False
    )
    amount_clp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_month: Mapped[int | None] = mapped_column(Integer)
    period_year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255))
    transfer_proof_url: Mapped[str | None] = mapped_column(String(500))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    membership: Mapped["Membership"] = relationship("Membership", back_populates="payments")
    fee_rate: Mapped["FeeRate"] = relationship("FeeRate", back_populates="payments")
    confirmer: Mapped["User | None"] = relationship("User")


