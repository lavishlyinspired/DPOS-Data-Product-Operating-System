from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, UTC
from typing import Optional


def utc_now():
    return datetime.now(UTC)


class Domain(BaseModel):
    id: str
    name: str
    description: str = ""
    owner: EmailStr
    team: str
    slack_channel: Optional[str] = None
    cost_center: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)