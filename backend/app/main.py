"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api import api_router
from app.config import get_settings
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: test database connection
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        result.scalar()
    yield
    # Shutdown: dispose engine
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="Club de Jazz API",
    description="Member management system for Club de Jazz de Concepción",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
