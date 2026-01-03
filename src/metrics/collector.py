from src.graph.manager import Neo4jManager
from datetime import datetime, timedelta
from typing import Dict, List

import uuid
class MetricsCollector:
    def __init__(self):
        self.manager = Neo4jManager()
        self.buffer = {} # product_id -> {pass: 0, fail: 0}

    def record_metric(
        self,
        product_id: str,
        metric_type: str,
        value: float,
        incident_id: str | None = None
    ):
        metric_id = f"metric_{uuid.uuid4().hex[:8]}"

        query = """
        MATCH (p:DataProduct {id:$pid})
        MERGE (m:Metric {id:$id})
        SET m.type=$type,
            m.value=$value,
            m.product_id=$pid,
            m.created_at=datetime()
        MERGE (p)-[:HAS_METRIC]->(m)
        """

        params = {
            "pid": product_id,
            "id": metric_id,
            "type": metric_type,
            "value": value
        }

        self.manager.execute_query(query, params)

        # 🔗 Link to incident if provided
        if incident_id:
            link_q = """
            MATCH (i:Incident {id:$iid}), (m:Metric {id:$mid})
            MERGE (i)-[:CAUSED_BY]->(m)
            """
            self.manager.execute_query(link_q, {
                "iid": incident_id,
                "mid": metric_id
            })
    def record(self, metric_type: str, product_id: str, value: int, source: str):
        query = """
        CREATE (m:Metric {
            id: $id,
            type: $type,
            product_id: $product_id,
            value: $value,
            source: $source,
            created_at: datetime()
        })
        """
        self.manager.execute_query(query, {
            "id": f"metric_{uuid.uuid4().hex[:10]}",
            "type": metric_type,
            "product_id": product_id,
            "value": value,
            "source": source
        })

    def record_contract_violation(self, product_id: str, count: int):
        """Record a contract violation metric."""
        self.record(
            metric_type="contract_violation",
            product_id=product_id,
            value=count,
            source="enforcement"
        )

    def flush_metrics_to_graph(self):
        """
        Writes aggregated metrics to Neo4j as :Metric nodes.
        Also triggers Incident check.
        """
        timestamp = datetime.utcnow()
        
        for product_id, counts in self.buffer.items():
            total = counts["pass"] + counts["fail"]
            if total == 0: continue
            
            error_rate = counts["fail"] / total
            
            # Create Metric Node
            query = """
            MATCH (p:DataProduct {id: $id})
            CREATE (m:Metric {
                id: randomUUID(),
                timestamp: $ts,
                target_type: 'data_product',
                target_id: $id,
                metric_type: 'error_rate',
                value: $rate,
                total_records: $total,
                failed_records: $failed
            })
            CREATE (p)-[:HAS_METRIC]->(m)
            """
            self.manager.execute_query(query, {
                "id": product_id,
                "ts": timestamp,
                "rate": error_rate,
                "total": total,
                "failed": counts["fail"]
            })

            # Check SLA Breach
            self._check_sla(product_id, error_rate)

        self.buffer = {} # Clear buffer

    def _check_sla(self, product_id: str, current_error_rate: float):
        # Updated Query: Checks BOTH Contract path AND Direct path
        # coalesce returns the first non-null value found
        q = """
        MATCH (p:DataProduct {id: $id})
        
        // Check Governance Path: Product -> Contract -> SLA
        OPTIONAL MATCH (p)-[:HAS_CONTRACT]->(c)-[:HAS_SLA]->(s_contract:SLA)
        
        // Check Direct Path: Product -> SLA
        OPTIONAL MATCH (p)-[:HAS_SLA]->(s_direct:SLA)
        
        // Return whichever one exists (Direct takes precedence if both exist, or swap coalesce args)
        RETURN coalesce(s_contract.max_error_rate, s_direct.max_error_rate) as max
        """
        
        res = self.manager.execute_query(q, {"id": product_id})
        
        # Safety Check
        if res and res[0]["max"] is not None:
            threshold = res[0]["max"]
        else:
            print(f"⚠️  No SLA found for {product_id}. Skipping check.")
            return

        if current_error_rate > threshold:
            from src.metrics.incident_manager import IncidentManager
            mgr = IncidentManager()
            mgr.create_incident(product_id, "sla_breach", f"Error rate {current_error_rate:.2f} > {threshold}")
            print(f"🚨 SLA BREACH for {product_id}: {current_error_rate} > {threshold}")