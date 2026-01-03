from src.graph.manager import Neo4jManager
from datetime import datetime
import uuid


def persist_agent_execution(agent_name: str, incident_id: str, outcome: dict):
    mgr = Neo4jManager()
    exec_id = f"agent_exec_{uuid.uuid4().hex[:8]}"

    query = """
    MATCH (i:Incident {id:$iid})
    CREATE (a:AgentExecution {
        id:$id,
        agent:$agent,
        outcome:$outcome,
        created_at:datetime()
    })
    MERGE (i)-[:HANDLED_BY]->(a)
    """
    mgr.execute_query(query, {
        "iid": incident_id,
        "id": exec_id,
        "agent": agent_name,
        "outcome": str(outcome)
    })
