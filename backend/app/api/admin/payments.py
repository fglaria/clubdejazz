from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.deps import AdminDependency, DbSession
from app.models.payment import Payment, PaymentStatus, FeeRate
from app.models.membership import Membership
from app.schemas.admin import (
    PaymentConfirm,
    PaymentCreate,
    PaymentResponse,
)

router: APIRouter = APIRouter(prefix="/payments")


@router.get(path="", response_model=list[PaymentResponse])
async def list_payments(
    admin: AdminDependency,
    db: DbSession,
    status_filter: PaymentStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List all payments (admin only)."""
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

    result = await db.execute(query)
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
    from uuid import UUID

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
        payment.confirmed_at = datetime.now()
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
