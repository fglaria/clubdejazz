from uuid import UUID
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, Result

from app.core.deps import AsyncSession, DbSession
from app.models.payment import FeeRate
from app.models.membership import MembershipType
from app.schemas.admin import FeeRateCreate


class FeeRateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current(self):
        """Get current active fee rates."""
        today: date = date.today()
        query = (
            select(FeeRate)
            .where(FeeRate.effective_from <= today)
            .where((FeeRate.effective_until.is_(None)) | (FeeRate.effective_until >= today))
            .order_by(FeeRate.membership_type_id, FeeRate.fee_type)
        )

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_membership_type_history(self, membership_type_id: str) -> list[FeeRate]:
        """Get fee rate history for a membership type."""
        try:
            mt_id: UUID = UUID(membership_type_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid membership type ID"
            )

        query = (
            select(FeeRate)
            .where(FeeRate.membership_type_id == mt_id)
            .order_by(FeeRate.effective_from.desc())
        )

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_one(self, fee_data: FeeRateCreate, admin_id: UUID) -> FeeRate:
        """Create a new fee rate."""
        # Verify membership type exists
        query = (
            select(MembershipType)
            .where(MembershipType.id == fee_data.membership_type_id)
        )

        result: Result = await self.db.execute(query)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership type not found",
            )

        fee_rate: FeeRate = FeeRate(
            fee_type=fee_data.fee_type,
            membership_type_id=fee_data.membership_type_id,
            amount_utm=fee_data.amount_utm,
            utm_to_clp_rate=fee_data.utm_to_clp_rate,
            amount_clp=fee_data.amount_clp,
            effective_from=fee_data.effective_from,
            effective_until=fee_data.effective_until,
            reason=fee_data.reason,
            created_by=admin_id,
        )

        self.db.add(fee_rate)
        await self.db.commit()
        await self.db.refresh(fee_rate)

        return fee_rate


def get_fee_rate_service(db: DbSession) -> FeeRateService:
    """Get FeeRateService Service"""
    return FeeRateService(db=db)


FeeRateServiceDependency = Annotated[FeeRateService, Depends(get_fee_rate_service)]
