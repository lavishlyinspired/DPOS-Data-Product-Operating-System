from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class Tag(BaseModel):
    name: str
    category: str # classification|business|technical|compliance
    description: Optional[str] = None
    color: Optional[str] = "#000000"
    requires_approval: bool = False
    created_at: datetime = Field(default_factory=utc_now)