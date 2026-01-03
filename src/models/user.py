from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, UTC


def utc_now():
    return datetime.now(UTC)


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    department: Optional[str] = None
    role: str # owner|steward|consumer|admin
    domain_affinities: List[str] = [] # For recommendations
    last_active: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)