from pydantic import BaseModel, Field as PydanticField
from datetime import datetime, UTC
from typing import List, Optional, Any


def utc_now():
    return datetime.now(UTC)


class Field(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str] = None
    nullable: bool = True
    unique: bool = False
    is_pii: bool = False
    pii_type: Optional[str] = None
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    default_value: Optional[Any] = None
    # Statistics
    null_rate: float = 0.0
    sample_values: List[str] = []


class Schema(BaseModel):
    id: str
    product_id: str
    version: str
    format: str = 'avro' # avro|json|parquet
    is_current: bool = True
    raw_schema: Optional[str] = None
    fields: List[Field] = []
    created_at: datetime = PydanticField(default_factory=utc_now)