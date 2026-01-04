import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DPOS_LOG_STREAM", "stderr")

from src.graph.manager import Neo4jManager


def main() -> int:
    with Neo4jManager() as mgr:
        label_counts = mgr.execute_query(
            "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS count ORDER BY count DESC",
            {},
        )
        print("LABEL_COUNTS")
        for row in label_counts[:30]:
            print(f"- {row['label']}: {row['count']}")

        sample_products = mgr.execute_query(
            "MATCH (p:DataProduct) RETURN p.id AS id, p.name AS name, p.status AS status ORDER BY p.id LIMIT 10",
            {},
        )
        print("\nSAMPLE_PRODUCTS")
        for row in sample_products:
            print(f"- {row}")

        sample_incidents = mgr.execute_query(
            "MATCH (i:Incident) RETURN i.id AS id, i.severity AS severity, i.status AS status, i.description AS description ORDER BY i.id LIMIT 5",
            {},
        )
        print("\nSAMPLE_INCIDENTS")
        for row in sample_incidents:
            print(f"- {row}")

        vr_keys = mgr.execute_query(
            "MATCH (vr:ValidationReport) RETURN keys(vr) AS keys LIMIT 1",
            {},
        )
        print("\nVALIDATION_REPORT_KEYS")
        print(vr_keys[0]["keys"] if vr_keys else [])

        sample_vr = mgr.execute_query(
            "MATCH (vr:ValidationReport) RETURN vr ORDER BY coalesce(vr.created_at, vr.timestamp, vr.id) DESC LIMIT 3",
            {},
        )
        print("\nSAMPLE_VALIDATION_REPORTS")
        for row in sample_vr:
            # row['vr'] is a Node; convert via dict() doesn't work reliably
            vr = row.get('vr')
            props = dict(vr) if vr is not None else {}
            print(f"- {props}")

        # Try to detect 'good/bad CSV' related labels
        hints = [
            "GoodRecord",
            "BadRecord",
            "Good",
            "Bad",
            "DataQualityIssue",
            "Violation",
            "ContractViolation",
        ]
        present_hints = [h for h in hints if any(r["label"] == h for r in label_counts)]
        print("\nQUALITY_LABEL_HINTS", present_hints)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
