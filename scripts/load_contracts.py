import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_contracts():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "contracts", "contracts.json")
    if not os.path.exists(path):
        print(f"⚠️  File not found: {path}")
        return

    print(f"📥 Loading Contracts from {path}...")

    with open(path, "r") as f:
        raw = json.load(f)

    contracts = raw.get("contracts", raw) if isinstance(raw, dict) else raw
    if not isinstance(contracts, list):
        print("⚠️ Invalid contracts format.")
        return

    for c in contracts:
        contract_id = c.get("id")
        product_id = c.get("product_id")

        if not contract_id or not product_id:
            continue

        # -------------------------------
        # Contract node
        # -------------------------------
        contract_props = {
            k: v for k, v in c.items()
            if k not in ("rules", "product_id")
        }

        q_contract = """
        MATCH (p:DataProduct {id: $pid})
        MERGE (c:Contract {id: $cid})
        SET c += $props
        MERGE (p)-[:HAS_CONTRACT]->(c)
        """
        mgr.execute_query(q_contract, {
            "pid": product_id,
            "cid": contract_id,
            "props": contract_props
        })

        # -------------------------------
        # Rules
        # -------------------------------
        for r in c.get("rules", []):
            rule_id = r.get("id")
            if not rule_id:
                continue

            rule_props = dict(r)

            q_rule = """
            MATCH (c:Contract {id: $cid})
            MERGE (r:Rule {id: $rid})
            SET r += $props
            MERGE (c)-[:HAS_RULE]->(r)
            """
            mgr.execute_query(q_rule, {
                "cid": contract_id,
                "rid": rule_id,
                "props": rule_props
            })

            # -------------------------------
            # Rule → Field linkage
            # -------------------------------
            if r.get("field"):
                q_field_link = """
                MATCH (r:Rule {id: $rid})
                MATCH (f:Field {name: $field})
                MERGE (r)-[:TARGETS_FIELD]->(f)
                """
                mgr.execute_query(q_field_link, {
                    "rid": rule_id,
                    "field": r["field"]
                })

    print("   ✅ Contracts loaded successfully.")


if __name__ == "__main__":
    load_contracts()
