from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class Pipeline(BaseModel):
    id: str
    name: str
    type: str # etl|elt|streaming|batch
    orchestrator: str # airflow|dagster|prefect|custom
    dag_id: Optional[str] = None
    schedule: Optional[str] = None
    status: str = "active"
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    has_fallback: bool = False
    fallback_source: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)