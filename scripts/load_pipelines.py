import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_pipelines():
    mgr = Neo4jManager()
    cfg = Config()
    path = os.path.join(cfg.data_dir, "pipelines")

    print(f"📥 Loading Pipelines from {path}...")

    for file_path in glob.glob(os.path.join(path, "*.json")):
        with open(file_path, "r") as f:
            raw = json.load(f)

        # Handle wrapper: { "pipelines": [...] }
        pipelines = raw.get("pipelines", raw) if isinstance(raw, dict) else raw

        if not isinstance(pipelines, list):
            print(f"⚠️ Invalid pipelines format in {file_path}")
            continue

        for p in pipelines:
            if not isinstance(p, dict):
                continue

            pipeline_id = p.get("id")
            if not pipeline_id:
                print("⚠️ Skipping pipeline with missing id")
                continue

            # ------------------------------------------------------
            # 1. CREATE PIPELINE NODE (Neo4j-safe properties only)
            # ------------------------------------------------------
            pipeline_props = {
                k: v for k, v in p.items()
                if k not in ("writes_to", "reads_from")
            }

            q_pipeline = """
            MERGE (pip:Pipeline {id: $id})
            SET pip += $props
            """

            mgr.execute_query(q_pipeline, {
                "id": pipeline_id,
                "props": pipeline_props
            })

            # ------------------------------------------------------
            # 2. LINK PIPELINE -> DATA PRODUCTS (WRITES_TO)
            # ------------------------------------------------------
            for dp_id in p.get("writes_to", []):
                q_link = """
                MATCH (pip:Pipeline {id: $pid})
                MATCH (dp:DataProduct {id: $did})
                MERGE (pip)-[:WRITES_TO]->(dp)
                """
                mgr.execute_query(q_link, {
                    "pid": pipeline_id,
                    "did": dp_id
                })

    print("   ✅ Pipelines loaded successfully.")


if __name__ == "__main__":
    load_pipelines()
