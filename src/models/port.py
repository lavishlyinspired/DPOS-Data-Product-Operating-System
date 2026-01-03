from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class InputPort(BaseModel):
    id: str
    name: str
    product_id: str
    type: str # database|kafka|api|s3|file
    connection_string: Optional[str] = None
    topic: Optional[str] = None
    database: Optional[str] = None
    table_name: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    refresh_frequency: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=utc_now)


class OutputPort(BaseModel):
    id: str
    name: str
    product_id: str
    type: str # kafka|api|s3|database|file
    topic: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    http_method: Optional[str] = None
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    format: Optional[str] = None
    database: Optional[str] = None
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    is_public: bool = False
    requires_approval: bool = False
    status: str = "active"
    created_at: datetime = Field(default_factory=utc_now)