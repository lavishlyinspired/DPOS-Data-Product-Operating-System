from src.graph.manager import Neo4jManager
from src.models import ValidationReport
from src.contracts.rules import get_rule_engine
from typing import List, Dict, Any
import uuid
from datetime import datetime, UTC
from src.governance.policy_resolver import PolicyResolver
import json


class ContractValidator:
    def __init__(self, product_id: str):
        self.product_id = product_id
        self.manager = Neo4jManager()
        self.rules = self._load_rules()

    # ---------------------------------------------------------
    # LOAD RULES (contract + policy)
    # ---------------------------------------------------------

    def _load_rules(self):
        query = """
        MATCH (p:DataProduct {id: $id})-[:HAS_CONTRACT]->(c:Contract)
        WHERE c.is_active = true
        MATCH (c)-[:HAS_RULE]->(r:Rule)
        WHERE r.enabled = true
        RETURN r
        """
        results = self.manager.execute_query(query, {"id": self.product_id})
        base_rules = [dict(r["r"]) for r in results]

        resolver = PolicyResolver()
        return resolver.resolve_policies(self.product_id, base_rules)

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def validate_batch(self, data_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        report_id = f"vr_{uuid.uuid4().hex[:10]}"
        violations = []
        invalid_rows = set()

        engines = []
        batch_engines = []

        for r in self.rules:
            try:
                engine = get_rule_engine(r["type"], r)
                if hasattr(engine, "validate_batch"):
                    batch_engines.append(engine)
                engines.append(engine)
            except ValueError:
                continue

        # -----------------------------
        # Batch-level rules
        # -----------------------------
        for engine in batch_engines:
            if not engine.validate_batch(data_batch):
                violations.append({
                    "rule_id": engine.config["id"],
                    "field": engine.field,
                    "severity": engine.severity,
                    "message": engine.get_error_message()
                })

        # -----------------------------
        # Row-level rules
        # -----------------------------
        for idx, row in enumerate(data_batch):
            for engine in engines:
                try:
                    if not engine.validate(row):
                        invalid_rows.add(idx)
                        violations.append({
                            "rule_id": engine.config["id"],
                            "field": engine.field,
                            "severity": engine.severity,
                            "message": engine.get_error_message(),
                            "row": idx
                        })
                except Exception:
                    continue

        valid_data = [row for i, row in enumerate(data_batch) if i not in invalid_rows]
        invalid_data = [row for i, row in enumerate(data_batch) if i in invalid_rows]

        result = "failed" if violations else "passed"
        action = self._determine_enforcement(result)

        now = datetime.now(UTC)
        report = ValidationReport(
        id=report_id,
        product_id=self.product_id,
        timestamp=now,
        created_at=now,
        trigger="batch",
        batch_id=f"batch_{now.timestamp()}",
        result=result,
        action=action,
        total_records=len(data_batch),
        passed_records=len(valid_data),
        failed_records=len(invalid_data),
        violations=json.dumps(violations),
        triggered_by="validator_system"
        )


        self._save_report(report)

        # Attach output port info (if present) so enforcement/demos can route outputs.
        output_port = {}
        try:
            port_res = self.manager.execute_query(
                """
                MATCH (p:DataProduct {id: $id})-[:HAS_OUTPUT_PORT]->(op:OutputPort)
                WHERE coalesce(op.status, 'active') = 'active'
                RETURN op
                ORDER BY coalesce(op.requires_approval, false) DESC
                LIMIT 1
                """,
                {"id": self.product_id},
            )
            if port_res:
                output_port = dict(port_res[0].get("op", {}))
        except Exception:
            output_port = {}

        return {
            "report_id": report_id,
            "product_id": self.product_id,
            "result": result,
            "action": action,
            "valid_data": valid_data,
            "invalid_data": invalid_data,
            "output_port": output_port
        }

    # ---------------------------------------------------------
    # ENFORCEMENT DECISION
    # ---------------------------------------------------------

    def _determine_enforcement(self, result: str) -> str:
        query = """
        MATCH (p:DataProduct {id: $id})-[:HAS_CONTRACT]->(c:Contract)
        WHERE c.is_active = true
        RETURN c.enforcement_mode AS mode
        """
        res = self.manager.execute_query(query, {"id": self.product_id})
        mode = res[0]["mode"] if res else "warn"

        if result == "passed":
            return "passed"

        return {
            "strict": "blocked",
            "quarantine": "quarantined"
        }.get(mode, "warned")

    # ---------------------------------------------------------
    # PERSIST VALIDATION REPORT
    # ---------------------------------------------------------

    def _save_report(self, report: ValidationReport):
        query = """
        MATCH (p:DataProduct {id: $pid})
        CREATE (v:ValidationReport $props)
        MERGE (p)-[:HAS_VALIDATION]->(v)
        """
        self.manager.execute_query(query, {
            "pid": self.product_id,
            "props": report.model_dump()
        })
