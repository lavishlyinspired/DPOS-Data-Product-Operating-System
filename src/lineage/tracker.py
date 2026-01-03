from src.graph.manager import Neo4jManager


class LineageTracker:
    def __init__(self):
        self.manager = Neo4jManager()

    def record_lineage(self, source_id: str, dest_id: str, metadata: dict = None):
        """
        Records lineage between two DataProducts with optional metadata.
        """
        metadata = metadata or {}

        query = """
        MATCH (src:DataProduct {id: $src})
        MATCH (dst:DataProduct {id: $dst})
        MERGE (dst)-[r:DEPENDS_ON]->(src)
        SET r += $props
        """

        self.manager.execute_query(query, {
            "src": source_id,
            "dst": dest_id,
            "props": metadata
        })
