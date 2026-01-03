import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_users():
    mgr = Neo4jManager()
    cfg = Config()
    path = os.path.join(cfg.data_dir, "users")

    print(f"📥 Loading Users from {path}...")

    for file_path in glob.glob(os.path.join(path, "*.json")):
        with open(file_path, "r") as f:
            raw = json.load(f)

        # Handle wrapper: { "users": [...] }
        users = raw.get("users", raw) if isinstance(raw, dict) else raw

        if not isinstance(users, list):
            print(f"⚠️ Invalid users format in {file_path}")
            continue

        for u in users:
            if not isinstance(u, dict):
                continue

            user_id = u.get("id")
            if not user_id:
                print("⚠️ Skipping user with missing id")
                continue

            # ------------------------------------------------------
            # 1. CREATE USER NODE (Neo4j-safe properties)
            # ------------------------------------------------------
            user_props = {
                k: v for k, v in u.items()
                if k not in ("consumes", "owns", "stewards")
            }

            q_user = """
            MERGE (u:User {id: $id})
            SET u += $props
            """

            mgr.execute_query(q_user, {
                "id": user_id,
                "props": user_props
            })

            # ------------------------------------------------------
            # 2. CONSUMES RELATIONSHIPS
            # ------------------------------------------------------
            for dp_id in u.get("consumes", []):
                q_consume = """
                MATCH (u:User {id: $uid})
                MATCH (dp:DataProduct {id: $did})
                MERGE (u)-[:CONSUMES]->(dp)
                """
                mgr.execute_query(q_consume, {
                    "uid": user_id,
                    "did": dp_id
                })

            # ------------------------------------------------------
            # 3. OWNS RELATIONSHIPS
            # ------------------------------------------------------
            for dp_id in u.get("owns", []):
                q_owns = """
                MATCH (u:User {id: $uid})
                MATCH (dp:DataProduct {id: $did})
                MERGE (u)-[:OWNS]->(dp)
                """
                mgr.execute_query(q_owns, {
                    "uid": user_id,
                    "did": dp_id
                })

            # ------------------------------------------------------
            # 4. STEWARD RELATIONSHIPS
            # ------------------------------------------------------
            for dp_id in u.get("stewards", []):
                q_steward = """
                MATCH (u:User {id: $uid})
                MATCH (dp:DataProduct {id: $did})
                MERGE (u)-[:STEWARD_OF]->(dp)
                """
                mgr.execute_query(q_steward, {
                    "uid": user_id,
                    "did": dp_id
                })

    print("   ✅ Users loaded successfully.")


if __name__ == "__main__":
    load_users()
