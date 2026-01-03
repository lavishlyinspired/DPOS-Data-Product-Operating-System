from pydantic import BaseModel

class SLA(BaseModel):
    id: str
    name: str
    product_id: str
    freshness_seconds: int
    availability_percent: float
    latency_p99_ms: int