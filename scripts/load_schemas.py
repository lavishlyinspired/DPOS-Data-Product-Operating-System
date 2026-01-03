import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_schemas():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "schemas", "schemas.json")
    if not os.path.exists(path):
        print(f"⚠️  File not found: {path}")
        return

    print(f"📥 Loading Schemas from {path}...")

    with open(path, "r") as f:
        raw = json.load(f)

    schemas = raw.get("schemas", raw) if isinstance(raw, dict) else raw
    if not isinstance(schemas, list):
        print("⚠️ Invalid schema format.")
        return

    for s in schemas:
        if not isinstance(s, dict):
            continue

        schema_id = s.get("id")
        product_id = s.get("product_id")

        if not schema_id or not product_id:
            print(f"   ⚠️ Skipping invalid schema entry: {s}")
            continue

        fields = s.get("fields", [])
        if not isinstance(fields, list):
            fields = []

        # --------------------------------------------------
        # SCHEMA NODE
        # --------------------------------------------------
        schema_props = {
            k: v for k, v in s.items()
            if k not in ("fields", "product_id")
        }

        q_schema = """
        MATCH (p:DataProduct {id: $pid})
        MERGE (s:Schema {id: $sid})
        SET s += $props
        MERGE (p)-[:HAS_SCHEMA]->(s)
        """

        mgr.execute_query(q_schema, {
            "pid": product_id,
            "sid": schema_id,
            "props": schema_props
        })

        # --------------------------------------------------
        # FIELD NODES
        # --------------------------------------------------
        for fdef in fields:
            if not isinstance(fdef, dict):
                continue

            field_id = fdef.get("id")
            if not field_id:
                continue

            # Strip reference metadata from field props
            field_props = {
                k: v for k, v in fdef.items()
                if k not in ("reference_product", "reference_field")
            }

            q_field = """
            MATCH (s:Schema {id: $sid})
            MERGE (f:Field {id: $fid})
            SET f += $props
            MERGE (s)-[:HAS_FIELD]->(f)
            """

            mgr.execute_query(q_field, {
                "sid": schema_id,
                "fid": field_id,
                "props": field_props
            })

        # --------------------------------------------------
        # FIELD-LEVEL REFERENCES
        # --------------------------------------------------
        for fdef in fields:
            ref_prod = fdef.get("reference_product")
            ref_field = fdef.get("reference_field")

            if not ref_prod or not ref_field:
                continue

            q_ref = """
            MATCH (src:Field {id: $src_id})
            MATCH (dst_schema:Schema)<-[:HAS_SCHEMA]-(dp:DataProduct {id: $ref_dp})
            MATCH (dst_schema)-[:HAS_FIELD]->(dst:Field {name: $ref_field})
            MERGE (src)-[r:REFERENCES]->(dst)
            SET r.reference_product = $ref_dp,
                r.reference_field = $ref_field
            """

            mgr.execute_query(q_ref, {
                "src_id": fdef["id"],
                "ref_dp": ref_prod,
                "ref_field": ref_field
            })

    print("   ✅ Schemas loaded successfully.")


if __name__ == "__main__":
    load_schemas()
