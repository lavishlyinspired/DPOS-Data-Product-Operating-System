from typing import List, Dict, Any
from src.incidents.incident_manager import IncidentManager

from src.agents.agent_runner import handle_incident
from src.metrics.collector import MetricsCollector

incident_mgr = IncidentManager()
metrics = MetricsCollector()

class EnforcementEngine:
    """
    Executes enforcement actions based on contract validation results.
    Stateless by design.
    """

    def enforce(self, product_id: str, report: Dict[str, Any]):
        """
        Entry point used by loaders, demos, and pipelines.
        """
        action = report.get("action")
        valid_data = report.get("valid_data", [])
        invalid_data = report.get("invalid_data", [])
        output_port_config = report.get("output_port", {})

        self._execute(
            product_id=product_id,
            action=action,
            valid_data=valid_data,
            invalid_data=invalid_data,
            output_port_config=output_port_config
        )

    # ------------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------------

    def _execute(
        self,
        action: str,
        product_id: str,
        valid_data: List[Dict],
        invalid_data: List[Dict],
        output_port_config: Dict,
    ):
        print(f"[ENFORCEMENT] Action: {action.upper()}")

        if action in ("passed", "warned"):
            print(
                f"   [OK] Writing {len(valid_data)} records to Output Topic: "
                f"{output_port_config.get('topic')}"
            )

        elif action == "blocked":
            # Step 1: Create incident
            incident_id = incident_mgr.create_incident(
                product_id=product_id,
                incident_type="CONTRACT_VIOLATION",
                severity="high",
                description=f"Contract violated for product {product_id}",
                source="enforcement",
            )

            # Step 2: Record metric
            metrics.record_contract_violation(product_id, len(invalid_data))

            print(
                f"   [BLOCKED] Contract violated. "
                f"Incident {incident_id} created and metric recorded. "
                f"Zero records written to output."
            )

            # Step 3: Trigger agent
            handle_incident(incident_id, severity="high")

        elif action == "quarantined":
            print(
                f"   [QUARANTINE] Writing {len(valid_data)} good records "
                f"and {len(invalid_data)} bad records to DLQ."
            )
