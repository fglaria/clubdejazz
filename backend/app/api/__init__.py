"""API route handlers."""

from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.fee_rates import router as fee_rates_router
from app.api.memberships import router as memberships_router
from app.api.users import router as users_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(memberships_router)
api_router.include_router(fee_rates_router)
api_router.include_router(events_router)
api_router.include_router(admin_router)
