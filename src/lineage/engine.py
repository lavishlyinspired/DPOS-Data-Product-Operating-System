from src.graph.manager import Neo4jManager
from typing import List, Dict, Any

class LineageEngine:
    def __init__(self):
        self.manager = Neo4jManager()

    def get_upstream(self, product_id: str, depth: int = 3) -> List[Dict]:
        """Find what sources feed into this product."""
        query = """
        MATCH path = (up:DataProduct)<-[:CONSUMES_FROM*1..{depth}]-(down:DataProduct {id: $id})
        RETURN nodes(path) as path_nodes
        """
        res = self.manager.execute_query(query, {"id": product_id, "depth": depth})
        return res

    def get_downstream(self, product_id: str, depth: int = 3) -> List[Dict]:
        """Find what products consume this product."""
        query = """
        MATCH path = (up:DataProduct {id: $id})-[:CONSUMES_FROM*1..{depth}]->(down:DataProduct)
        RETURN nodes(path) as path_nodes
        """
        res = self.manager.execute_query(query, {"id": product_id, "depth": depth})
        return res