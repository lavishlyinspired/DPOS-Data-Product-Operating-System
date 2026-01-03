from src.graph.manager import Neo4jManager
from src.models.incident import Incident
from datetime import datetime
import uuid


from src.metrics.incident_manager import IncidentManager


class SLAAlertingEngine:
    def __init__(self):
        self.mgr = Neo4jManager()
        self.incidents = IncidentManager()

    def check_and_escalate(self):
        query = """
        MATCH (p:DataProduct)-[:HAS_SLA]->(s:SLA)<-[:BREACHES]-(m:Metric)
        RETURN p.id AS product_id, m.value AS value, s.threshold AS threshold
        """
        results = self.mgr.execute_query(query)

        for r in results:
            incident_id = self.incidents.create_incident(
                product_id=r["product_id"],
                incident_type="SLA_BREACH",
                severity="high",
                description=f"SLA breached: value={r['value']} threshold={r['threshold']}",
                source="sla_monitor"
            )

            # Lazy import to avoid circular dependency
            try:
                from src.agents.agent_runner import handle_incident
                handle_incident(incident_id, severity="high")
            except ImportError:
                pass

    def raise_incident(self, product_id: str, sla_type: str, value: float):
        incident_id = f"inc_{uuid.uuid4().hex[:8]}"

        incident = Incident(
            id=incident_id,
            type="SLA_BREACH",
            severity="high",
            description=f"{sla_type} SLA breached with value {value}",
            created_at=datetime.utcnow()
        )

        query = """
        MATCH (p:DataProduct {id: $pid})
        MERGE (i:Incident {id: $iid})
        SET i += $props
        MERGE (p)-[:HAS_INCIDENT]->(i)
        """

        self.manager.execute_query(query, {
            "pid": product_id,
            "iid": incident_id,
            "props": incident.dict()
        })

        return incident_id
