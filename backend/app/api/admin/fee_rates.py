from fastapi import APIRouter, status

from app.core.deps import AdminDependency
from app.models.payment import FeeRate
from app.schemas.admin import FeeRateCreate
from app.schemas.membership import FeeRateResponse
from app.services.fee_rate import FeeRateServiceDependency


router: APIRouter = APIRouter(prefix="/fee-rates", tags=["fee-rates"])


@router.post(path="", response_model=FeeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_rate(
    fee_data: FeeRateCreate,
    admin: AdminDependency,
    fee_rate_service: FeeRateServiceDependency,
) -> FeeRate:
    """Create a new fee rate (admin only)."""
    return await fee_rate_service.create_one(fee_data=fee_data, admin_id=admin.id)
