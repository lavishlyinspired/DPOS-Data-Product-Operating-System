import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lineage.tracker import LineageTracker
from src.utils.config import Config


def load_lineage():
    tracker = LineageTracker()
    cfg = Config()
    path = os.path.join(cfg.data_dir, "lineage")

    print(f"🔗 Loading Lineage from {path}...")

    for file_path in glob.glob(os.path.join(path, "*.json")):
        with open(file_path, "r") as f:
            raw = json.load(f)

        # Handle wrapper: { "lineage": [...] }
        lineage_links = raw.get("lineage", raw) if isinstance(raw, dict) else raw

        if not isinstance(lineage_links, list):
            print(f"⚠️ Invalid lineage format in {file_path}")
            continue

        for l in lineage_links:
            if not isinstance(l, dict):
                continue

            src = l.get("source_product_id")
            dst = l.get("target_product_id")

            if not src or not dst:
                print(f"⚠️ Skipping lineage with missing endpoints: {l}")
                continue

            metadata = {
                "relationship_type": l.get("relationship_type"),
                "field": l.get("field"),
                "description": l.get("description"),
                "discovered_at": l.get("discovered_at"),
                "last_verified": l.get("last_verified"),
            }

            # ✅ CALL USING POSITIONAL ARGUMENTS
            tracker.record_lineage(src, dst, metadata)

            print(f"   ↘️  {src} -> {dst}")

    print("   ✅ Lineage loaded successfully.")


if __name__ == "__main__":
    load_lineage()
