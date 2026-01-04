#!/usr/bin/env python3
"""DPOS Core Concepts Demo (Batch + Agents + Kafka + SLA)

This script is meant for *explaining* DPOS, end-to-end, with both good and bad data.

It demonstrates:
- Data Products + Contracts (rules loaded from Neo4j)
- Contract validation on GOOD vs BAD data
- Enforcement actions (passed/blocked/quarantined)
- Incident creation + AI agent handling (Healing + Steward)
- Impact analysis
- SLA monitoring (best-effort)
- Kafka streaming concepts (MOCK by default; real if KAFKA_ENABLED=true)

Prereqs (recommended):
- Neo4j running + sample data loaded: scripts/init_graph.py + scripts/load_all.py
- Optional Kafka via docker-compose and KAFKA_ENABLED=true

Run:
  python scripts/demo_core_concepts.py
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = _project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _read_csv(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            rows.append(dict(row))
            if limit is not None and idx + 1 >= limit:
                break
    return rows


def _get_output_topic_for(product_id: str) -> str:
    from src.graph.manager import Neo4jManager

    with Neo4jManager() as mgr:
        res = mgr.execute_query(
            """
            MATCH (p:DataProduct {id: $id})-[:HAS_OUTPUT_PORT]->(op:OutputPort)
            WHERE coalesce(op.status, 'active') = 'active'
            RETURN op.topic AS topic
            ORDER BY coalesce(op.requires_approval, false) DESC
            LIMIT 1
            """,
            {"id": product_id},
        )
        if res and res[0].get("topic"):
            return str(res[0]["topic"])
    return f"dpos.valid.{product_id}"


def main() -> int:
    sys.path.insert(0, str(_project_root()))
    _load_env()

    print("=" * 78)
    print("DPOS Core Concepts Demo")
    print("=" * 78)

    # ----------------------------
    # 0) Connectivity
    # ----------------------------
    from src.graph.manager import Neo4jManager

    mgr = Neo4jManager()
    if not mgr.verify_connectivity():
        raise SystemExit(
            "Neo4j connectivity failed. Start infra and set NEO4J_* in dpos-ecommerce/.env"
        )
    print("[OK] Neo4j connectivity verified")

    # ----------------------------
    # 1) Contracts + validation (GOOD vs BAD)
    # ----------------------------
    product_id = "DP001"

    # Use-case dataset selection (kept generic; choose via env var)
    usecase = os.getenv("DPOS_USECASE", "ecommerce")
    usecase_root = _project_root() / "data" / "usecase" / usecase

    # Prefer new layout: data/usecase/<usecase>/good|bad
    good_path = usecase_root / "good" / "customers.csv"
    bad_path = usecase_root / "bad" / "customers_bad.csv"

    # Alternative COVID file names
    if not good_path.exists():
        good_path = usecase_root / "good" / "outreach_list.csv"
    if not bad_path.exists():
        bad_path = usecase_root / "bad" / "outreach_list_bad.csv"

    # Backward compatible fallbacks
    if not good_path.exists():
        good_path = _project_root() / "data" / "good" / "customers.csv"
    if not bad_path.exists():
        bad_path = _project_root() / "data" / "bad" / "customers_bad.csv"

    if not good_path.exists() or not bad_path.exists():
        raise SystemExit(f"Missing demo data: {good_path} or {bad_path}")

    good_rows = _read_csv(good_path, limit=50)
    bad_rows = _read_csv(bad_path, limit=50)

    from src.contracts.validator import ContractValidator

    validator = ContractValidator(product_id)

    print("\n--- 1A) Validate GOOD data (should pass/warn) ---")
    report_good = validator.validate_batch(good_rows)
    print({k: report_good.get(k) for k in ["product_id", "result", "action", "report_id"]})

    print("\n--- 1B) Validate BAD data (should fail -> strict=blocked for DP001) ---")
    report_bad = validator.validate_batch(bad_rows)
    print({k: report_bad.get(k) for k in ["product_id", "result", "action", "report_id"]})
    print(f"Valid records: {len(report_bad.get('valid_data', []))}")
    print(f"Invalid records: {len(report_bad.get('invalid_data', []))}")

    # ----------------------------
    # 2) Enforcement (creates incident on blocked)
    # ----------------------------
    from src.enforcement.engine import EnforcementEngine

    engine = EnforcementEngine()

    print("\n--- 2A) Enforce GOOD report (publish valid) ---")
    engine.enforce(product_id, report_good)

    print("\n--- 2B) Enforce BAD report (blocked -> create incident + trigger agent) ---")
    engine.enforce(product_id, report_bad)

    # Fetch newest incident for DP001
    incident_id = None
    res = mgr.execute_query(
        """
        MATCH (p:DataProduct {id:$pid})-[:HAS_INCIDENT]->(i:Incident)
        RETURN i.id AS id, i.severity AS severity, i.status AS status, i.timestamp AS ts
        ORDER BY i.timestamp DESC
        LIMIT 1
        """.strip(),
        {"pid": product_id},
    )
    if res:
        incident_id = res[0]["id"]
        print(f"[OK] Latest incident for {product_id}: {incident_id} (severity={res[0].get('severity')})")
    else:
        print("[WARN] No incident found (check enforcement_mode and data)")

    # ----------------------------
    # 3) Steward + Impact agents (explicit)
    # ----------------------------
    from src.agents.agent_runner import handle_incident_steward, analyze_impact

    if incident_id:
        print("\n--- 3A) Steward Agent review (governance recommendations) ---")
        handle_incident_steward(incident_id, severity="high")

    print("\n--- 3B) Impact Agent (downstream impact for product failure) ---")
    analyze_impact(product_id, incident_id=incident_id)

    # ----------------------------
    # 4) SLA Monitoring (best-effort)
    # ----------------------------
    print("\n--- 4) SLA monitoring (best-effort) ---")
    try:
        from src.agents.sla_agent import run_sla_monitoring

        sla_report = run_sla_monitoring([product_id])
        print({
            "breached_slas": len(sla_report.get("breached_slas", [])),
            "at_risk_slas": len(sla_report.get("at_risk_slas", [])),
            "status": sla_report.get("status"),
        })
    except Exception as e:
        print(f"[WARN] SLA monitoring not available: {e}")

    # ----------------------------
    # 5) Kafka concepts (works even in MOCK mode)
    # ----------------------------
    print("\n--- 5) Kafka routing (streaming enforcement concept) ---")
    from src.utils.config import app_config
    from src.enforcement.streaming_enforcer import StreamingEnforcer

    print(f"KAFKA_ENABLED={getattr(app_config, 'kafka_enabled', False)}")
    print(f"Raw prefix={app_config.topic_prefix_raw}  Valid prefix={app_config.topic_prefix_valid}  DLQ={app_config.topic_dlq}")

    enforcer = StreamingEnforcer()

    # Simulate one good and one bad streaming message for DP001
    raw_topic = f"{app_config.topic_prefix_raw}{product_id}"
    good_msg = ("{" + "\"customer_id\":\"123\",\"email\":\"test@test.com\",\"name\":\"Alice\",\"segment\":\"premium\"}" ).encode("utf-8")
    bad_msg = ("{" + "\"customer_id\":\"123\",\"email\":null,\"name\":\"\",\"segment\":\"bogus\"}" ).encode("utf-8")

    print(f"Simulating streaming message on topic: {raw_topic}")
    res_good = enforcer.process_message(raw_topic, good_msg)
    res_bad = enforcer.process_message(raw_topic, bad_msg)
    print("Streaming result (good):", res_good)
    print("Streaming result (bad):", res_bad)

    print("\n--- 6) Supervisor Agent (multi-agent orchestration) ---")
    try:
        from src.agents.supervisor_agent import build_supervisor_agent
        from src.agents.checkpointer import get_thread_config
        import uuid

        supervisor = build_supervisor_agent()
        q = (
            f"We had a contract violation for {product_id}. "
            f"Summarize governance health, analyze impact, and suggest next actions." 
        )
        result = supervisor.invoke(
            {
                "query": q,
                "conversation_history": [],
                "intent": None,
                "intent_confidence": None,
                "execution_plan": [],
                "current_step": 0,
                "agent_results": {},
                "intermediate_findings": [],
                "requires_human_approval": False,
                "approval_reason": None,
                "approved": False,
                "response": None,
                "recommendations": [],
                "follow_up_questions": [],
                "execution_log": [],
                "total_agents_invoked": 0,
                "status": "new",
                "messages": [],
            },
            config=get_thread_config(f"demo_supervisor_{uuid.uuid4().hex[:8]}"),
        )
        print("Supervisor intent:", result.get("intent"), "conf=", result.get("intent_confidence"))
        print("Agents invoked:", result.get("total_agents_invoked"))
        print("Response:\n", result.get("response"))
        if result.get("recommendations"):
            print("Recommendations:")
            for r in result["recommendations"][:5]:
                print(" -", r)
    except Exception as e:
        print(f"[WARN] Supervisor demo failed: {e}")

    print("\n[OK] Demo complete")
    print("Output topic example for DP001:", _get_output_topic_for(product_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
