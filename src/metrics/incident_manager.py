from src.graph.manager import Neo4jManager
from src.models.incident import Incident
from datetime import datetime, UTC
import uuid


class IncidentManager:
    def __init__(self):
        self.mgr = Neo4jManager()

    def create_incident(
        self,
        product_id: str,
        incident_type: str,
        severity: str,
        description: str,
        source: str
    ) -> str:
        incident_id = f"INC_{uuid.uuid4().hex[:8]}"

        incident = Incident(
            id=incident_id,
            target_id=product_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            status="open",
            source=source,
            timestamp=datetime.now(UTC)
        )

        query = """
        MATCH (p:DataProduct {id:$pid})
        MERGE (i:Incident {id:$id})
        SET i += $props
        MERGE (p)-[:HAS_INCIDENT]->(i)
        """

        self.mgr.execute_query(query, {
            "pid": product_id,
            "id": incident_id,
            "props": incident.model_dump()
        })

        # Lazy import to avoid circular dependency
        try:
            from src.agents.agent_runner import handle_incident
            handle_incident(incident_id, severity=severity)
        except ImportError:
            pass  # Agent runner not available

        return incident_id
