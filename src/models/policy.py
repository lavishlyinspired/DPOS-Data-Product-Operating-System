from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class PolicyRule(BaseModel):
    id: str
    policy_id: str
    type: str # null_rate|uniqueness|range|pattern|freshness|referential|enum
    description: Optional[str] = None
    threshold_override: Optional[float] = None
    enforcement_override: Optional[str] = None
    field: Optional[str] = None # Target specific field
    enabled: bool = True


class Policy(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    scope: str # GLOBAL|DOMAIN|PRODUCT
    target_id: Optional[str] = None # If DOMAIN or PRODUCT
    priority: int = 100
    is_active: bool = True
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)