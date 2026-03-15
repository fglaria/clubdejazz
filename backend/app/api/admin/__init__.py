from fastapi import APIRouter

from app.api.admin.memberships import router as memberships_router
from app.api.admin.payments import router as payments_router
from app.api.admin.events import router as events_router
from app.api.admin.fee_rates import router as fee_rates_router
from app.api.admin.users import router as users_router
from app.api.admin.members import router as members_router


router: APIRouter = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(router=memberships_router)
router.include_router(router=payments_router)
router.include_router(router=events_router)
router.include_router(router=fee_rates_router)
router.include_router(router=users_router)
router.include_router(router=members_router)
