import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_slas():
    mgr = Neo4jManager()
    cfg = Config()

    # Prefer data/slas/slas.json, fallback to data/slas.json
    path = os.path.join(cfg.data_dir, "slas", "slas.json")
    if not os.path.exists(path):
        path = os.path.join(cfg.data_dir, "slas.json")

    if not os.path.exists(path):
        print("⚠️  SLA file not found.")
        return

    print(f"📥 Loading SLAs from {path}...")

    with open(path, "r") as f:
        raw = json.load(f)

    # Handle wrapper: { "slas": [...] }
    slas = raw.get("slas", raw) if isinstance(raw, dict) else raw

    if not isinstance(slas, list):
        print("⚠️ Invalid SLA format.")
        return

    for sla in slas:
        if not isinstance(sla, dict):
            continue

        sla_id = sla.get("id")
        product_id = sla.get("product_id")

        if not sla_id or not product_id:
            print(f"   ⚠️ Skipping invalid SLA entry: {sla}")
            continue

        # --------------------------------------------------
        # Neo4j-safe SLA properties (remove relationship data)
        # --------------------------------------------------
        sla_props = {
            k: v for k, v in sla.items()
            if k not in ("product_id",)
        }

        query = """
        MATCH (p:DataProduct {id: $pid})
        MERGE (s:SLA {id: $sid})
        SET s += $props
        MERGE (p)-[:HAS_SLA]->(s)
        """

        mgr.execute_query(query, {
            "pid": product_id,
            "sid": sla_id,
            "props": sla_props
        })

    print("   ✅ SLAs loaded successfully.")


if __name__ == "__main__":
    load_slas()
