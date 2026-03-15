from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.core.deps import AdminDependency, DbSession
from app.models.payment import Payment, PaymentStatus, FeeRate
from app.models.membership import Membership
from app.schemas.admin import (
    PaymentConfirm,
    PaymentCreate,
    PaymentResponse,
)
from app.services.payment import PaymentServiceDependency

router: APIRouter = APIRouter(prefix="/payments")


@router.get(path="", response_model=list[PaymentResponse])
async def list_payments(
    admin: AdminDependency,
    payment_service: PaymentServiceDependency,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
) -> list[dict]:
    """List all payments (admin only)."""
    return await payment_service.get_all(status_filter=status_filter, limit=limit, offset=offset)


@router.post(path="", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Record a new payment (admin only)."""
    # Verify membership exists
    result = await db.execute(
        select(Membership)
        .where(Membership.id == payment_data.membership_id)
        .options(selectinload(Membership.user))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Verify fee rate exists
    result = await db.execute(
        select(FeeRate).where(FeeRate.id == payment_data.fee_rate_id)
    )
    fee_rate = result.scalar_one_or_none()
    if not fee_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fee rate not found",
        )

    payment = Payment(
        membership_id=payment_data.membership_id,
        fee_rate_id=payment_data.fee_rate_id,
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

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return {
        "id": payment.id,
        "membership_id": payment.membership_id,
        "user_email": membership.user.email,
        "user_full_name": membership.user.full_name,
        "fee_type": fee_rate.fee_type,
        "amount_clp": payment.amount_clp,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date,
        "period_month": payment.period_month,
        "period_year": payment.period_year,
        "status": payment.status,
        "gateway_transaction_id": payment.gateway_transaction_id,
        "transfer_proof_url": payment.transfer_proof_url,
        "notes": payment.notes,
        "confirmed_by": payment.confirmed_by,
        "confirmed_at": payment.confirmed_at,
        "created_at": payment.created_at,
    }


@router.post(path="/{payment_id}/confirm")
async def confirm_payment(
    payment_id: str,
    confirmation: PaymentConfirm,
    admin: AdminDependency,
    db: DbSession,
) -> dict:
    """Confirm or reject a pending payment."""
    try:
        pid = UUID(payment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment ID",
        )

    result = await db.execute(
        select(Payment).where(Payment.id == pid)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment is not pending (current: {payment.status.value})",
        )

    if confirmation.action == "confirm":
        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_by = admin.id
        payment.confirmed_at = datetime.now(timezone.utc)
    else:
        payment.status = PaymentStatus.REJECTED

    if confirmation.notes:
        existing_notes = payment.notes or ""
        payment.notes = f"{existing_notes}\n[Admin] {confirmation.notes}".strip()

    await db.commit()

    return {
        "id": str(payment.id),
        "status": payment.status.value,
        "message": f"Payment {confirmation.action}ed successfully",
    }
