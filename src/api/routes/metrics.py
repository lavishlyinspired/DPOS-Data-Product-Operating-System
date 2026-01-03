from fastapi import APIRouter
from src.metrics.aggregator import MetricsAggregator

router = APIRouter()

@router.get("/{product_id}/error_rate")
def error_rate(product_id: str):
    return MetricsAggregator().get_hourly_avg(product_id, "error_rate")