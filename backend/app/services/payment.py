from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, Result
from sqlalchemy.orm import selectinload

from app.core.deps import AsyncSession, DbSession
from app.models.payment import Payment, PaymentStatus
from app.models.membership import Membership


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self,
        status_filter: PaymentStatus | None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]: # TODO return list[Payment]
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
        # TODO return list(result.scalars().all())
        payments = result.scalars().all()

        return [
            {
                "id": p.id,
                "membership_id": p.membership_id,
                "user_email": p.membership.user.email,
                "user_full_name": p.membership.user.full_name,
                "fee_type": p.fee_rate.fee_type,
                "amount_clp": p.amount_clp,
                "payment_method": p.payment_method,
                "payment_date": p.payment_date,
                "period_month": p.period_month,
                "period_year": p.period_year,
                "status": p.status,
                "gateway_transaction_id": p.gateway_transaction_id,
                "transfer_proof_url": p.transfer_proof_url,
                "notes": p.notes,
                "confirmed_by": p.confirmed_by,
                "confirmed_at": p.confirmed_at,
                "created_at": p.created_at,
            }
            for p in payments
        ]



def get_payment_service(db: DbSession) -> PaymentService:
    """Get Payment Service"""
    return PaymentService(db=db)


PaymentServiceDependency = Annotated[PaymentService, Depends(get_payment_service)]
