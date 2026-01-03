from src.graph.manager import Neo4jManager
import json


class AgentReplayService:
    def __init__(self):
        self.mgr = Neo4jManager()

    def get_execution(self, incident_id: str):
        query = """
        MATCH (i:Incident {id:$id})-[:HANDLED_BY]->(a:AgentExecution)
        RETURN a.agent AS agent,
               a.outcome AS outcome,
               a.created_at AS created_at
        ORDER BY a.created_at
        """
        res = self.mgr.execute_query(query, {"id": incident_id})
        return res

    def explain(self, incident_id: str):
        executions = self.get_execution(incident_id)
        explanation = []

        for e in executions:
            explanation.append({
                "agent": e["agent"],
                "decision": e["outcome"],
                "timestamp": e["created_at"]
            })

        return explanation
