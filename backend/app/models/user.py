"""User model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.membership import Membership, OrganizationDetails
    from app.models.role import UserRole


class User(Base):
    """User model for club members."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(50))
    last_name_1: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name_2: Mapped[str | None] = mapped_column(String(50))
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    member_number: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="user",
        foreign_keys="Membership.user_id",
    )
    organization_details: Mapped["OrganizationDetails | None"] = relationship(
        "OrganizationDetails", back_populates="user", uselist=False
    )
    roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user")

    @property
    def full_name(self) -> str:
        """Return full name in Chilean format."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name_1)
        if self.last_name_2:
            parts.append(self.last_name_2)
        return " ".join(parts)
