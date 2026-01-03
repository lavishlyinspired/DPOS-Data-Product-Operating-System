from pydantic import BaseModel, Field
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class Incident(BaseModel):
    id: str
    target_id: str
    incident_type: str
    description: str
    status: str = "open"
    severity: str = "medium"
    timestamp: datetime = Field(default_factory=utc_now)