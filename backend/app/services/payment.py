from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, Result
from sqlalchemy.orm import selectinload

from app.core.deps import AsyncSession, DbSession
from app.models.payment import Payment, PaymentStatus, FeeRate
from app.models.membership import Membership
from app.schemas.admin import PaymentCreate, PaymentConfirm
from app.services.fee_rate import FeeRateServiceDependency
from app.services.membership import MembershipServiceDependency

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self,
        status_filter: PaymentStatus | None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Payment]:
        """List all payments."""
        query = (
            select(Payment)
            .options(
                selectinload(Payment.membership).selectinload(Membership.user),
                selectinload(Payment.fee_rate),
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if status_filter:
            query = query.where(Payment.status == status_filter)

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_one(self, payment_id: str) -> Payment:
        try:
            pid: UUID = UUID(payment_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment ID",
            )

        query = (
            select(Payment)
            .where(Payment.id == pid)
            .options(
                selectinload(Payment.membership).selectinload(Membership.user),
                selectinload(Payment.fee_rate),
            )
        )

        result: Result = await self.db.execute(query)
        payment: Payment | None = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        return payment

    async def create_one(self,
        payment_data: PaymentCreate,
        membership_service: MembershipServiceDependency,
        fee_rate_service: FeeRateServiceDependency
    ):
        """Record a new payment."""
        # Verify membership exists
        membership_id: str = str(payment_data.membership_id)
        membership: Membership = await membership_service.get_one(
            membership_id=membership_id
        )

        # Verify fee rate exists
        fee_rate_id: str = str(payment_data.fee_rate_id)
        fee_rate: FeeRate = await fee_rate_service.get_one(fee_rate_id=fee_rate_id)

        payment: Payment = Payment(
            membership_id=membership.id,
            fee_rate_id=fee_rate.id,
            payment_method=payment_data.payment_method,
            amount_clp=payment_data.amount_clp,
            payment_date=payment_data.payment_date,
            period_month=payment_data.period_month,
            period_year=payment_data.period_year,
            status=PaymentStatus.PENDING,
            gateway_transaction_id=payment_data.gateway_transaction_id,
            transfer_proof_url=payment_data.transfer_proof_url,
            notes=payment_data.notes,
        )

        self.db.add(payment)
        await self.db.commit()

        return await self.get_one(payment_id=str(payment.id))

    async def confirm(self, payment_id: str, confirmation: PaymentConfirm, admin_id: UUID) -> dict:
        """Confirm or reject a pending payment."""
        payment: Payment = await self.get_one(payment_id=payment_id)
        if payment.status != PaymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment is not pending (current: {payment.status.value})",
            )

        if confirmation.action == "confirm":
            payment.status = PaymentStatus.CONFIRMED
            payment.confirmed_by = admin_id
            payment.confirmed_at = datetime.now(timezone.utc)
        else:
            payment.status = PaymentStatus.REJECTED

        if confirmation.notes:
            existing_notes = payment.notes or ""
            payment.notes = f"{existing_notes}\n[Admin] {confirmation.notes}".strip()

        await self.db.commit()

        return {
            "id": str(payment.id),
            "status": payment.status.value,
            "message": f"Payment {confirmation.action}ed successfully",
        }


def get_payment_service(db: DbSession) -> PaymentService:
    """Get Payment Service"""
    return PaymentService(db=db)


PaymentServiceDependency = Annotated[PaymentService, Depends(get_payment_service)]
