import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure we don't pollute stdout with logs when debugging
os.environ.setdefault("DPOS_LOG_STREAM", "stderr")

from src.graph.manager import Neo4jManager


def pick_incident_id() -> str:
    cypher = (
        "MATCH (i:Incident) "
        "RETURN i.id AS id, i.severity AS severity, i.status AS status "
        "ORDER BY i.created_at DESC, i.id DESC LIMIT 1"
    )
    with Neo4jManager() as mgr:
        rows = mgr.execute_query(cypher, {})
    if not rows:
        raise SystemExit("No Incident nodes found in Neo4j")
    row = rows[0]
    print(f"Using incident: {row}")
    return row["id"]


def main() -> int:
    incident_id = sys.argv[1] if len(sys.argv) > 1 else pick_incident_id()
    severity = sys.argv[2] if len(sys.argv) > 2 else "high"

    from src.agents.agent_runner import handle_incident

    try:
        result = handle_incident(incident_id, severity=severity)
        print("RESULT_KEYS", sorted(list(result.keys())) if isinstance(result, dict) else type(result))
        print("RESULT", result)
        return 0
    except Exception as e:
        import traceback

        print("ERROR", type(e).__name__, str(e), file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
