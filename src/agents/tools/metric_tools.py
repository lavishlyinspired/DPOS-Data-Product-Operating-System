from langchain_core.tools import tool
from src.metrics.aggregator import MetricsAggregator


@tool
def get_metrics(product_id: str) -> str:
    """Get metrics for a product."""
    agg = MetricsAggregator()
    val = agg.get_hourly_avg(product_id, "error_rate")
    return f"Error Rate for {product_id}: {val}"


# Export the tool for convenience
metric_tool = get_metrics