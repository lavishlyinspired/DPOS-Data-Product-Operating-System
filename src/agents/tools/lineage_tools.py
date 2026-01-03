from langchain_core.tools import tool
from src.lineage.engine import LineageEngine


@tool
def trace_upstream(product_id: str) -> str:
    """Get upstream lineage for a product."""
    engine = LineageEngine()
    res = engine.get_upstream(product_id)
    return str(res)


# Export the tool for convenience
lineage_tool = trace_upstream