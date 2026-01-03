import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_products():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "products", "products.json")
    if not os.path.exists(path):
        print(f"⚠️  File not found: {path}")
        return

    print(f"📥 Loading Products from {path}...")

    with open(path, "r") as f:
        raw = json.load(f)

    products = raw.get("products", raw) if isinstance(raw, dict) else raw
    if not isinstance(products, list):
        print("⚠️ Invalid products format.")
        return

    for p in products:
        if not isinstance(p, dict):
            continue

        product_id = p.get("id")
        domain_id = p.get("domain_id")

        if not product_id or not domain_id:
            print(f"   ⚠️ Skipping invalid product entry: {p}")
            continue

        # --------------------------------------------------
        # Product node (strip relationship fields)
        # --------------------------------------------------
        product_props = {
            k: v for k, v in p.items()
            if k not in ("domain_id", "tags", "consumes_from")
        }

        q_product = """
        MATCH (d:Domain {id: $did})
        MERGE (p:DataProduct {id: $pid})
        SET p += $props
        MERGE (p)-[:IN_DOMAIN]->(d)
        """

        mgr.execute_query(q_product, {
            "pid": product_id,
            "did": domain_id,
            "props": product_props
        })

        # --------------------------------------------------
        # Tags
        # --------------------------------------------------
        tags = p.get("tags", [])
        if isinstance(tags, list) and tags:
            q_tags = """
            MATCH (p:DataProduct {id: $pid})
            UNWIND $tags AS tname
            MERGE (t:Tag {name: tname})
            MERGE (p)-[:HAS_TAG]->(t)
            """
            mgr.execute_query(q_tags, {
                "pid": product_id,
                "tags": tags
            })

    print("   ✅ Products loaded successfully.")


if __name__ == "__main__":
    load_products()
