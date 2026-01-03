import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.utils.config import Config


def load_ports():
    mgr = Neo4jManager()
    cfg = Config()

    path = os.path.join(cfg.data_dir, "ports")

    print(f"📥 Loading Ports from {path}...")

    files = glob.glob(os.path.join(path, "*.json"))
    if not files:
        print(f"⚠️  No JSON files found in {path}")
        return

    for file_path in files:
        with open(file_path, "r") as f:
            raw = json.load(f)

        ports = []

        # Handle wrappers
        if isinstance(raw, dict):
            if "input_ports" in raw:
                ports = raw["input_ports"]
            elif "output_ports" in raw:
                ports = raw["output_ports"]
            else:
                print(f"   ⚠️ Skipping {os.path.basename(file_path)}: unknown structure")
                continue
        elif isinstance(raw, list):
            ports = raw
        else:
            continue

        for p in ports:
            if not isinstance(p, dict):
                continue

            port_id = p.get("id")
            product_id = p.get("product_id")

            if not port_id or not product_id:
                print(f"   ⚠️ Skipping invalid port entry: {p}")
                continue

            # --------------------------------------------------
            # Determine Port Type (robust)
            # --------------------------------------------------
            if port_id.startswith("inport_"):
                label = "InputPort"
                rel_type = "HAS_INPUT_PORT"
            elif port_id.startswith("outport_"):
                label = "OutputPort"
                rel_type = "HAS_OUTPUT_PORT"
            else:
                print(f"   ⚠️ Unknown port type for {port_id}")
                continue

            # --------------------------------------------------
            # Neo4j-safe port properties (strip relationship data)
            # --------------------------------------------------
            port_props = {
                k: v for k, v in p.items()
                if k not in ("product_id",)
            }

            query = f"""
            MATCH (prod:DataProduct {{id: $pid}})
            MERGE (port:{label} {{id: $id}})
            SET port += $props
            MERGE (prod)-[:{rel_type}]->(port)
            """

            mgr.execute_query(query, {
                "pid": product_id,
                "id": port_id,
                "props": port_props
            })

    print("   ✅ Ports loaded successfully.")


if __name__ == "__main__":
    load_ports()
