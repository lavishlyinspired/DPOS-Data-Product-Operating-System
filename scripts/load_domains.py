import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_domains():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "domains", "domains.json")
    if not os.path.exists(path):
        print(f"⚠️  File not found: {path}")
        return

    print(f"📥 Loading Domains from {path}...")

    with open(path, "r") as f:
        raw = json.load(f)

    domains = raw.get("domains", raw) if isinstance(raw, dict) else raw
    if not isinstance(domains, list):
        print("⚠️ Invalid domains format.")
        return

    for d in domains:
        if not isinstance(d, dict):
            continue

        domain_id = d.get("id")
        if not domain_id:
            print(f"⚠️ Skipping domain with missing id: {d}")
            continue

        # Neo4j-safe domain properties
        domain_props = dict(d)

        query = """
        MERGE (d:Domain {id: $id})
        SET d += $props
        """

        mgr.execute_query(query, {
            "id": domain_id,
            "props": domain_props
        })

    print("   ✅ Domains loaded successfully.")


if __name__ == "__main__":
    load_domains()
