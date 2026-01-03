from pydantic import BaseModel, Field
from datetime import datetime, UTC
from typing import Optional, List


def utc_now():
    return datetime.now(UTC)


class Rule(BaseModel):
    id: str
    name: str
    type: str # null_rate|uniqueness|range|pattern|freshness|referential|enum
    field: Optional[str] = None
    threshold: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    max_age_seconds: Optional[int] = None
    reference_product: Optional[str] = None
    reference_field: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    severity: str = 'error'
    enabled: bool = True


class Contract(BaseModel):
    id: str
    name: str
    product_id: str
    description: Optional[str] = None
    version: str = '1.0.0'
    enforcement_mode: str = 'strict'
    rules: List[Rule] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)

class SLA(BaseModel):
    id: str
    name: str
    product_id: str
    freshness_seconds: int
    availability_percent: float
    latency_p99_ms: int
    support_tier: str = 'gold'