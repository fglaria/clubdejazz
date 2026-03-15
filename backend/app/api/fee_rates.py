"""Fee rate endpoints."""

from fastapi import APIRouter

from app.models import FeeRate
from app.schemas.membership import FeeRateResponse
from app.services.fee_rate import FeeRateServiceDependency

router = APIRouter(prefix="/fee-rates", tags=["fee-rates"])


@router.get(path="/current", response_model=list[FeeRateResponse])
async def get_current_fee_rates(fee_rate_service: FeeRateServiceDependency) -> list[FeeRate]:
    """Get current active fee rates."""
    return fee_rate_service.get_current()


@router.get(path="/history/{membership_type_id}", response_model=list[FeeRateResponse])
async def get_fee_rate_history(
    membership_type_id: str,
    fee_rate_service: FeeRateServiceDependency
) -> list[FeeRate]:
    """Get fee rate history for a membership type."""
    return await fee_rate_service.get_membership_type_history(membership_type_id=membership_type_id)
