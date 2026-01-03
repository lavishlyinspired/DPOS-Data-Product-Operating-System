"""
Multi-Incident Orchestrator Agent
Correlates and batch-handles related incidents for efficient resolution.
Uses LLM for incident correlation and priority determination.
"""
from typing import TypedDict, List, Optional, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from datetime import datetime, UTC

from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available
from src.graph.manager import Neo4jManager


class OrchestratorAgentState(TypedDict):
    """State for the multi-incident orchestrator agent."""
    # Input
    incident_ids: List[str]
    timeframe_hours: int

    # Correlation analysis
    incidents: List[Dict[str, Any]]
    correlation_groups: List[Dict[str, Any]]
    root_cause_hypothesis: Optional[str]

    # Prioritization
    priority_queue: List[Dict[str, Any]]
    handling_strategy: Optional[str]

    # Execution
    delegated_actions: List[Dict[str, Any]]
    batch_remediation_plan: Optional[str]

    status: str


CORRELATION_PROMPT = """Analyze these incidents to identify if they are related:

Incidents:
{incidents_text}

Determine:
1. Are these incidents likely caused by the same root issue? (yes/no)
2. What is the likely common root cause?
3. What is the correlation strength? (strong/moderate/weak/none)
4. Should these be handled as a batch? (yes/no)

Format:
CORRELATED: yes/no
ROOT_CAUSE: <hypothesis>
STRENGTH: strong/moderate/weak/none
BATCH_HANDLE: yes/no
REASONING: <brief explanation>
"""

PRIORITIZATION_PROMPT = """Prioritize these correlated incidents for handling:

Incidents:
{incidents_text}

Consider:
- Severity levels
- Business impact
- Dependencies between incidents
- Resource efficiency

Return a prioritized list with handling recommendations.
Format each as: PRIORITY N: incident_id - reason
"""


def build_orchestrator_agent():
    """Build the multi-incident orchestrator agent."""
    log = get_agent_logger("OrchestratorAgent")

    def load_incidents(state: OrchestratorAgentState) -> OrchestratorAgentState:
        """Load incident details for all provided IDs."""
        log.info(f"Loading {len(state['incident_ids'])} incidents for orchestration")

        incidents = []
        try:
            with Neo4jManager() as mgr:
                for incident_id in state["incident_ids"]:
                    result = mgr.execute_query("""
                        MATCH (i:Incident {id: $id})
                        OPTIONAL MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i)
                        RETURN i {.*, product_id: p.id, product_name: p.name} as incident
                    """, {"id": incident_id})

                    if result:
                        incidents.append(result[0]["incident"])

        except Exception as e:
            log.error(f"Failed to load incidents: {e}")

        return {
            **state,
            "incidents": incidents,
            "status": "incidents_loaded"
        }

    def correlate_incidents(state: OrchestratorAgentState) -> OrchestratorAgentState:
        """Analyze incidents for correlation using LLM."""
        log.info("Analyzing incident correlations with LLM")

        incidents = state.get("incidents", [])
        if len(incidents) < 2:
            return {
                **state,
                "correlation_groups": [{"incidents": incidents, "correlated": False}],
                "status": "correlation_analyzed"
            }

        llm = get_llm_if_available()
        correlation_groups = []
        root_cause_hypothesis = None

        if llm:
            try:
                incidents_text = "\n".join(
                    f"- ID: {inc.get('id')}, Severity: {inc.get('severity')}, "
                    f"Product: {inc.get('product_name', 'Unknown')}, "
                    f"Type: {inc.get('type')}, Description: {inc.get('description', 'N/A')[:100]}"
                    for inc in incidents
                )

                prompt = CORRELATION_PROMPT.format(incidents_text=incidents_text)
                response = llm.invoke(prompt)

                # Parse response
                content = response.content
                is_correlated = "CORRELATED: yes" in content.lower()
                root_cause = _extract_field(content, "ROOT_CAUSE:")
                strength = _extract_field(content, "STRENGTH:")
                batch_handle = "BATCH_HANDLE: yes" in content.lower()

                if is_correlated:
                    correlation_groups.append({
                        "incidents": incidents,
                        "correlated": True,
                        "root_cause": root_cause,
                        "strength": strength,
                        "batch_handle": batch_handle
                    })
                    root_cause_hypothesis = root_cause
                else:
                    # Treat as individual incidents
                    for inc in incidents:
                        correlation_groups.append({
                            "incidents": [inc],
                            "correlated": False
                        })

            except Exception as e:
                log.warning(f"LLM correlation failed: {e}")
                correlation_groups = [{"incidents": incidents, "correlated": False}]
        else:
            # Fallback: Group by product or severity
            correlation_groups = _fallback_correlation(incidents)

        log.info(
            f"Correlation analysis complete",
            extra={
                "groups": len(correlation_groups),
                "correlated": any(g.get("correlated") for g in correlation_groups)
            }
        )

        return {
            **state,
            "correlation_groups": correlation_groups,
            "root_cause_hypothesis": root_cause_hypothesis,
            "status": "correlation_analyzed"
        }

    def prioritize_incidents(state: OrchestratorAgentState) -> OrchestratorAgentState:
        """Prioritize incidents for handling."""
        log.info("Prioritizing incidents")

        incidents = state.get("incidents", [])
        correlation_groups = state.get("correlation_groups", [])

        # Build priority queue
        priority_queue = []

        llm = get_llm_if_available()
        if llm and len(incidents) > 1:
            try:
                incidents_text = "\n".join(
                    f"- {inc.get('id')}: severity={inc.get('severity')}, "
                    f"product={inc.get('product_name', 'Unknown')}"
                    for inc in incidents
                )

                prompt = PRIORITIZATION_PROMPT.format(incidents_text=incidents_text)
                response = llm.invoke(prompt)

                # Parse priorities from response
                for line in response.content.split("\n"):
                    if "PRIORITY" in line.upper():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            incident_ref = parts[1].strip().split("-")[0].strip()
                            for inc in incidents:
                                if inc.get("id") == incident_ref or incident_ref in str(inc.get("id")):
                                    priority_queue.append({
                                        "incident": inc,
                                        "priority": len(priority_queue) + 1
                                    })
                                    break

            except Exception as e:
                log.warning(f"LLM prioritization failed: {e}")

        # Fallback prioritization
        if not priority_queue:
            priority_queue = _fallback_prioritization(incidents)

        # Determine handling strategy
        strategy = "individual"
        if any(g.get("batch_handle") for g in correlation_groups):
            strategy = "batch"
        elif any(g.get("correlated") for g in correlation_groups):
            strategy = "coordinated"

        return {
            **state,
            "priority_queue": priority_queue,
            "handling_strategy": strategy,
            "status": "prioritized"
        }

    def plan_batch_remediation(state: OrchestratorAgentState) -> OrchestratorAgentState:
        """Plan batch remediation for correlated incidents."""
        log.info(f"Planning remediation with strategy: {state.get('handling_strategy')}")

        strategy = state.get("handling_strategy", "individual")
        priority_queue = state.get("priority_queue", [])
        root_cause = state.get("root_cause_hypothesis")

        delegated_actions = []
        batch_plan = None

        if strategy == "batch" and root_cause:
            # Single fix for correlated incidents
            batch_plan = f"""
**Batch Remediation Plan**
Root Cause: {root_cause}

Actions:
1. Address root cause affecting all {len(priority_queue)} incidents
2. Verify fix resolves primary incident
3. Validate all correlated incidents are resolved
4. Update incident statuses in batch
"""
            for item in priority_queue:
                delegated_actions.append({
                    "incident_id": item["incident"].get("id"),
                    "action": "await_batch_fix",
                    "agent": "OrchestratorAgent"
                })

        elif strategy == "coordinated":
            # Sequential handling with coordination
            for item in priority_queue:
                inc = item["incident"]
                severity = inc.get("severity", "medium")

                if severity in ["critical", "high"]:
                    delegated_actions.append({
                        "incident_id": inc.get("id"),
                        "action": "delegate_to_healing_agent",
                        "agent": "HealingAgent",
                        "priority": item["priority"]
                    })
                else:
                    delegated_actions.append({
                        "incident_id": inc.get("id"),
                        "action": "delegate_to_steward_agent",
                        "agent": "StewardAgent",
                        "priority": item["priority"]
                    })

        else:
            # Individual handling
            for item in priority_queue:
                inc = item["incident"]
                delegated_actions.append({
                    "incident_id": inc.get("id"),
                    "action": "handle_individually",
                    "agent": "HealingAgent" if inc.get("severity") in ["critical", "high"] else "StewardAgent",
                    "priority": item["priority"]
                })

        return {
            **state,
            "delegated_actions": delegated_actions,
            "batch_remediation_plan": batch_plan,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(OrchestratorAgentState)

    graph.add_node("load", load_incidents)
    graph.add_node("correlate", correlate_incidents)
    graph.add_node("prioritize", prioritize_incidents)
    graph.add_node("plan", plan_batch_remediation)

    graph.set_entry_point("load")
    graph.add_edge("load", "correlate")
    graph.add_edge("correlate", "prioritize")
    graph.add_edge("prioritize", "plan")
    graph.add_edge("plan", END)

    return graph.compile(checkpointer=get_checkpointer())


def _extract_field(content: str, field: str) -> str:
    """Extract a field value from LLM response."""
    for line in content.split("\n"):
        if field.upper() in line.upper():
            return line.split(":", 1)[-1].strip()
    return ""


def _fallback_correlation(incidents: List[Dict]) -> List[Dict]:
    """Fallback correlation by product."""
    by_product = {}
    for inc in incidents:
        product = inc.get("product_id", "unknown")
        if product not in by_product:
            by_product[product] = []
        by_product[product].append(inc)

    groups = []
    for product, incs in by_product.items():
        groups.append({
            "incidents": incs,
            "correlated": len(incs) > 1,
            "root_cause": f"Multiple incidents on {product}" if len(incs) > 1 else None
        })

    return groups


def _fallback_prioritization(incidents: List[Dict]) -> List[Dict]:
    """Fallback prioritization by severity."""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    sorted_incidents = sorted(
        incidents,
        key=lambda x: severity_order.get(x.get("severity", "medium"), 2)
    )

    return [
        {"incident": inc, "priority": i + 1}
        for i, inc in enumerate(sorted_incidents)
    ]
