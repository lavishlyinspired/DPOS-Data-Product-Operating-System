from pydantic import BaseModel, Field
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class Metric(BaseModel):
    id: str
    target_id: str
    metric_type: str
    value: float
    timestamp: datetime = Field(default_factory=utc_now)