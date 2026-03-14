from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import AdminDependency, DbSession
from app.models.payment import FeeRate
from app.models.membership import MembershipType
from app.schemas.admin import FeeRateCreate
from app.schemas.membership import FeeRateResponse


router: APIRouter = APIRouter(prefix="/fee-rates")


@router.post(path="", response_model=FeeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_rate(
    fee_data: FeeRateCreate,
    admin: AdminDependency,
    db: DbSession,
) -> FeeRate:
    """Create a new fee rate (admin only)."""
    # Verify membership type exists
    result = await db.execute(
        select(MembershipType).where(MembershipType.id == fee_data.membership_type_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership type not found",
        )

    fee_rate = FeeRate(
        fee_type=fee_data.fee_type,
        membership_type_id=fee_data.membership_type_id,
        amount_utm=fee_data.amount_utm,
        utm_to_clp_rate=fee_data.utm_to_clp_rate,
        amount_clp=fee_data.amount_clp,
        effective_from=fee_data.effective_from,
        effective_until=fee_data.effective_until,
        reason=fee_data.reason,
        created_by=admin.id,
    )

    db.add(fee_rate)
    await db.commit()
    await db.refresh(fee_rate)

    return fee_rate
