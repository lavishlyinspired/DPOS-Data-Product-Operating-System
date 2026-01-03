from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, UTC
from typing import List, Optional


def utc_now():
    return datetime.now(UTC)


class DataProduct(BaseModel):
    id: str
    name: str
    title: str
    description: str = ""
    owner: EmailStr
    domain_id: str  # FK to Domain
    status: str = 'active' # draft|active|deprecated|retired
    version: str = '1.0.0'
    type: str = 'master' # master|event|state|derived
    
    # Feature 3: Semantic Search
    embedding: Optional[List[float]] = None
    
    documentation_url: Optional[str] = None
    source_code_url: Optional[str] = None
    
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)