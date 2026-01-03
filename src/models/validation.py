from pydantic import BaseModel, Field
from datetime import datetime, UTC
from typing import Optional


def utc_now():
    return datetime.now(UTC)


class ValidationReport(BaseModel):
    id: str
    product_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    trigger: str  # e.g., "batch", "stream"
    batch_id: Optional[str] = None
    result: str  # "passed", "failed", "warning"
    action: str = "passed"  # "passed", "blocked", "quarantined", "warned"
    total_records: int = 0
    passed_records: int = 0
    failed_records: int = 0
    violations: str = "[]"  # JSON string of violations
    triggered_by: str = "validator_system"  # e.g., "validator_system", "user"