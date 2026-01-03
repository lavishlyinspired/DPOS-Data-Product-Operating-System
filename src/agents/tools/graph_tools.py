from langchain_core.tools import tool
from src.graph.manager import Neo4jManager

@tool
def get_product_status(product_id: str) -> str:
    """Get status of a data product by ID."""
    with Neo4jManager() as mgr:
        q = "MATCH (p:DataProduct {id: $id}) RETURN p"
        res = mgr.execute_query(q, {"id": product_id})
        return str(res[0]) if res else "Not found"


# Export the tool for convenience
graph_tool = get_product_status