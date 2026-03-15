from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import AdminDependency, DbSession
from app.models import Event
from app.schemas.admin import EventCreate, EventUpdate
from app.schemas.event import EventResponse

router: APIRouter = APIRouter(prefix="/events", tags=["events"])


@router.get(path="", response_model=list[EventResponse])
async def list_all_events(
    admin: AdminDependency,
    db: DbSession,
    include_unpublished: bool = Query(True),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[Event]:
    """List all events including unpublished (admin only)."""
    query = (
        select(Event)
        .order_by(Event.event_date.desc())
        .limit(limit)
        .offset(offset)
    )

    if not include_unpublished:
        query = query.where(Event.is_published.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(path="", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    admin: AdminDependency,
    db: DbSession,
) -> Event:
    """Create a new event (admin only)."""
    event = Event(
        title=event_data.title,
        description=event_data.description,
        event_date=event_data.event_date,
        location=event_data.location,
        address=event_data.address,
        image_url=event_data.image_url,
        is_published=event_data.is_published,
        created_by=admin.id,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return event


@router.get(path="/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    admin: AdminDependency,
    db: DbSession,
) -> Event:
    """Get any event including unpublished (admin only)."""
    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.patch(path="/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    admin: AdminDependency,
    db: DbSession,
) -> Event:
    """Update an event (admin only)."""
    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    return event


@router.delete(path="/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    admin: AdminDependency,
    db: DbSession,
) -> None:
    """Delete an event (admin only)."""
    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    await db.delete(event)
    await db.commit()
