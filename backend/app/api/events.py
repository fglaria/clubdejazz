"""Event endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DbSession
from app.models import Event
from app.schemas.event import EventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
async def list_events(db: DbSession) -> list[Event]:
    """List published events (public)."""
    result = await db.execute(
        select(Event)
        .where(Event.is_published.is_(True))
        .order_by(Event.event_date.desc())
    )
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: DbSession) -> Event:
    """Get a specific event (public, if published)."""
    from uuid import UUID

    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid event ID")

    result = await db.execute(
        select(Event).where(Event.id == eid).where(Event.is_published.is_(True))
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return event
