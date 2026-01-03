from src.graph.manager import Neo4jManager
from typing import List, Dict

class ImpactAnalyzer:
    def __init__(self):
        self.manager = Neo4jManager()

    def analyze_product_failure(self, failed_product_id: str) -> Dict:
        """Alias for analyze_failure_impact for backwards compatibility."""
        return self.analyze_failure_impact(failed_product_id)

    def analyze_failure(self, failed_product_id: str) -> Dict:
        """Alias for analyze_failure_impact for API compatibility."""
        return self.analyze_failure_impact(failed_product_id)

    def analyze_failure_impact(self, failed_product_id: str) -> Dict:
        """
        Analyzes the impact of a product failure.
        Returns: Downstream consumers, affected pipelines, and business criticality.
        """
        
        # 1. Find Downstream Consumers
        consumers_query = """
        MATCH (p:DataProduct {id: $id})<-[:CONSUMES_FROM]-(consumer:DataProduct)
        OPTIONAL MATCH (consumer)-[:HAS_TAG]->(t:Tag {name: 'Critical'})
        RETURN consumer.id as consumer_id, consumer.name as consumer_name, 
               CASE WHEN t IS NOT NULL THEN true ELSE false END as is_critical
        """
        consumers = self.manager.execute_query(consumers_query, {"id": failed_product_id})
        
        # 2. Find Affected Pipelines
        pipelines_query = """
        MATCH (p:DataProduct {id: $id})<-[:READS_FROM]-(pipe:Pipeline)
        RETURN pipe.id, pipe.name, pipe.status
        UNION
        MATCH (p:DataProduct {id: $id})<-[:CONSUMES_FROM]-(down:DataProduct)<-[:WRITES_TO]-(pipe:Pipeline)
        RETURN pipe.id, pipe.name, pipe.status
        """
        pipelines = self.manager.execute_query(pipelines_query, {"id": failed_product_id})
        
        # 3. Count Users
        users_query = """
        MATCH (p:DataProduct {id: $id})<-[:CONSUMES]-(u:User)
        RETURN count(u) as affected_users
        """
        users = self.manager.execute_query(users_query, {"id": failed_product_id})
        user_count = users[0]["affected_users"] if users else 0

        return {
            "failed_product": failed_product_id,
            "downstream_consumers": [dict(c) for c in consumers],
            "affected_pipelines": [dict(p) for p in pipelines],
            "affected_users_count": user_count
        }