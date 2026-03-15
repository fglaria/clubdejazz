from fastapi import APIRouter, Query, status

from app.core.deps import AdminDependency
from app.models.payment import Payment, PaymentStatus
from app.schemas.admin import (
    PaymentConfirm,
    PaymentConfirmResponse,
    PaymentCreate,
    PaymentResponse,
)
from app.services.fee_rate import FeeRateServiceDependency
from app.services.membership import MembershipServiceDependency
from app.services.payment import PaymentServiceDependency

router: APIRouter = APIRouter(prefix="/payments")


@router.get(path="", response_model=list[PaymentResponse])
async def list_payments(
    admin: AdminDependency,
    payment_service: PaymentServiceDependency,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
) -> list[Payment]:
    """List all payments (admin only)."""
    return await payment_service.get_all(status_filter=status_filter, limit=limit, offset=offset)


@router.post(path="", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    admin: AdminDependency,
    payment_service: PaymentServiceDependency,
    membership_service: MembershipServiceDependency,
    fee_rate_service: FeeRateServiceDependency,
) -> Payment:
    """Record a new payment (admin only)."""
    return await payment_service.create_one(
        payment_data=payment_data,
        membership_service=membership_service,
        fee_rate_service=fee_rate_service,
    )


@router.post(path="/{payment_id}/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    payment_id: str,
    confirmation: PaymentConfirm,
    admin: AdminDependency,
    payment_service: PaymentServiceDependency
) -> dict:
    """Confirm or reject a pending payment."""
    return await payment_service.confirm(
        payment_id=payment_id,
        confirmation=confirmation,
        admin_id=admin.id
    )
