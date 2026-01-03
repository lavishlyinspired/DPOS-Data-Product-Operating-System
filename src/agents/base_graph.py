from src.graph.manager import Neo4jManager
from datetime import datetime, UTC
from langgraph.graph import StateGraph
import uuid


class AgentGraphBase:
    """Base class for recording agent executions to Neo4j."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.mgr = Neo4jManager()

    def record_execution(self, incident_id: str, state: dict):
        exec_id = f"AG_{uuid.uuid4().hex[:8]}"

        query = """
        MATCH (i:Incident {id:$iid})
        MERGE (a:AgentExecution {id:$aid})
        SET a.agent = $agent,
            a.outcome = $outcome,
            a.created_at = $ts
        MERGE (i)-[:HANDLED_BY]->(a)
        """

        self.mgr.execute_query(query, {
            "iid": incident_id,
            "aid": exec_id,
            "agent": self.agent_name,
            "outcome": str(state),
            "ts": datetime.now(UTC).isoformat()
        })

        print(f"[OK] AgentExecution {exec_id} persisted")


class BaseAgentGraph:
    """
    Base class for building LangGraph-based agents.
    Wraps StateGraph with common functionality.
    """
    
    def __init__(self, state_type):
        self.state_type = state_type
        self.graph = StateGraph(state_type)
    
    def compile(self):
        """Compile the graph and return the runnable."""
        return self.graph.compile()
