import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_policies():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "policies", "policies.json")

    if not os.path.exists(path):
        print(f"⚠️  File not found: {path}")
        return

    print(f"📥 Loading Policies from {path}...")

    with open(path, "r") as f:
        raw_data = json.load(f)

    # Handle wrapper format { "policies": [...] }
    policies_list = (
        raw_data.get("policies", raw_data)
        if isinstance(raw_data, dict)
        else raw_data
    )

    for p in policies_list:
        print(f"   [DEBUG] Processing item type: {type(p)}")

        if not isinstance(p, dict):
            print(f"   ⛔ Skipping invalid policy object: {p}")
            continue

        policy_id = p.get("id")
        if not policy_id:
            print("   ⚠️ Skipping policy with missing id")
            continue

        # ------------------------------------------------------------------
        # 1. CREATE POLICY NODE (REMOVE NESTED STRUCTURES)
        # ------------------------------------------------------------------
        policy_props = {
            k: v for k, v in p.items()
            if k not in ("rules",)   # Neo4j cannot store list-of-maps
        }

        q_policy = """
        MERGE (pol:Policy {id: $id})
        SET pol += $props
        """

        try:
            mgr.execute_query(q_policy, {
                "id": policy_id,
                "props": policy_props
            })
        except Exception as e:
            print(f"   ❌ Error creating Policy Node {policy_id}: {e}")
            continue

        # ------------------------------------------------------------------
        # 2. LINK POLICY TO DOMAIN (DOMAIN SCOPE ONLY)
        # ------------------------------------------------------------------
        if p.get("scope") == "DOMAIN":
            domain_id = p.get("domain_id")  # ✅ correct field

            if domain_id:
                q_domain_link = """
                MATCH (pol:Policy {id: $pid})
                MATCH (d:Domain {id: $did})
                MERGE (pol)-[:APPLIES_TO_DOMAIN]->(d)
                """

                mgr.execute_query(q_domain_link, {
                    "pid": policy_id,
                    "did": domain_id
                })
            else:
                print(f"   ⚠️ DOMAIN policy {policy_id} missing domain_id")

        # ------------------------------------------------------------------
        # 3. CREATE POLICY RULES + RELATIONSHIPS
        # ------------------------------------------------------------------
        rules = p.get("rules", [])
        for pr in rules:
            if not isinstance(pr, dict):
                continue

            rule_id = pr.get("id")
            if not rule_id:
                print(f"   ⚠️ Skipping PolicyRule with missing id in {policy_id}")
                continue

            q_rule = """
            MATCH (pol:Policy {id: $pid})
            MERGE (pr:PolicyRule {id: $rid})
            SET pr += $props
            MERGE (pol)-[:HAS_POLICY_RULE]->(pr)
            """

            try:
                mgr.execute_query(q_rule, {
                    "pid": policy_id,
                    "rid": rule_id,
                    "props": pr
                })
            except Exception as e:
                print(f"   ❌ Error creating PolicyRule {rule_id}: {e}")

    print("   ✅ Policies loaded successfully.")


if __name__ == "__main__":
    load_policies()
