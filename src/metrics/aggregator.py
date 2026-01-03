from src.graph.manager import Neo4jManager
from datetime import datetime, timedelta

class MetricsAggregator:
    def __init__(self):
        self.manager = Neo4jManager()

    def get_hourly_avg(self, product_id: str, metric_type: str):
        # Logic to aggregate last hour's metrics
        q = """
        MATCH (p:DataProduct {id: $id})-[:HAS_METRIC]->(m:Metric)
        WHERE m.type = $type AND m.timestamp > datetime() - duration('PT1H')
        RETURN avg(m.value) as avg_val
        """
        res = self.manager.execute_query(q, {"id": product_id, "type": metric_type})
        return res[0]['avg_val'] if res else 0.0