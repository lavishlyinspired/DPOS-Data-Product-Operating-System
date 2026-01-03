import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_tags():
    mgr = Neo4jManager()
    cfg = Config()
    path = os.path.join(cfg.data_dir, "tags")

    print(f"📥 Loading Tags from {path}...")

    for file_path in glob.glob(os.path.join(path, "*.json")):
        with open(file_path, "r") as f:
            raw = json.load(f)

        # Handle wrapper: { "tags": [...] }
        tags = raw.get("tags", raw) if isinstance(raw, dict) else raw

        if not isinstance(tags, list):
            print(f"⚠️ Invalid tags format in {file_path}")
            continue

        for t in tags:
            if not isinstance(t, dict):
                continue

            tag_name = t.get("name")
            if not tag_name:
                print("⚠️ Skipping tag with missing name")
                continue

            # ------------------------------------------------------
            # CREATE TAG NODE (Neo4j-safe properties only)
            # ------------------------------------------------------
            tag_props = dict(t)  # all fields are primitive-safe today

            q_tag = """
            MERGE (tag:Tag {name: $name})
            SET tag += $props
            """

            mgr.execute_query(q_tag, {
                "name": tag_name,
                "props": tag_props
            })

    print("   ✅ Tags loaded successfully.")


if __name__ == "__main__":
    load_tags()
