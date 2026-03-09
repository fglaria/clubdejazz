"""Event schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventResponse(BaseModel):
    """Event response."""

    id: UUID
    title: str
    description: str | None
    event_date: datetime
    location: str | None
    address: str | None
    image_url: str | None
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}
