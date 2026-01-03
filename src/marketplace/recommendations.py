from src.graph.manager import Neo4jManager

class RecommendationEngine:
    def __init__(self):
        self.manager = Neo4jManager()

    def get_recommendations_for_user(self, user_id: str):
        # Logic: Recommend products in domains the user has affinity for
        q = """
        MATCH (u:User {id: $id})-[:CONSUMES]->(p:DataProduct)-[:IN_DOMAIN]->(d:Domain)
        WITH d
        MATCH (rec:DataProduct)-[:IN_DOMAIN]->(d)
        WHERE NOT (u)-[:CONSUMES]->(rec)
        RETURN DISTINCT rec.name as name
        LIMIT 5
        """
        return self.manager.execute_query(q, {"id": user_id})