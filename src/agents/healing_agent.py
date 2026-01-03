"""
Healing Agent (LLM-Enhanced)
Self-healing agent that automatically remediates data quality issues.
Uses LLM for intelligent diagnosis, severity assessment, and remediation planning.
"""
from typing import TypedDict, List, Optional, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from operator import add

from src.agents.tools.common_tools import (
    get_incident_details,
    get_downstream_impact,
    check_pipeline_fallback,
    activate_fallback,
    record_agent_execution,
    update_incident_status
)
from src.agents.tools.llm_tools import (
    analyze_root_cause,
    reassess_severity,
    create_remediation_plan,
    generate_incident_narrative
)
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available


class HealingAgentState(TypedDict):
    """State for the self-healing agent with LLM enhancements."""
    incident_id: str
    severity: str
    product_id: Optional[str]
    product_name: Optional[str]

    # LLM-enhanced analysis
    diagnosis: Optional[str]
    root_cause: Optional[str]
    root_cause_factors: Optional[List[str]]
    root_cause_confidence: Optional[str]

    # Severity reassessment
    assessed_severity: Optional[str]
    severity_changed: bool
    urgency: Optional[str]

    # Remediation
    recommendation: str
    remediation_steps: Optional[List[str]]
    action: str
    fallback_available: bool

    # Human-in-the-loop
    requires_approval: bool
    approved: bool
    escalation_needed: bool

    # Narrative for stakeholders
    incident_narrative: Optional[str]

    status: str
    messages: Annotated[List[BaseMessage], add]


def build_healing_agent():
    """
    Build an enhanced self-healing agent with LLM capabilities:
    - LLM-powered root cause analysis
    - Dynamic severity reassessment
    - Intelligent remediation planning
    - Stakeholder narrative generation
    """
    log = get_agent_logger("HealingAgent")

    def load_incident(state: HealingAgentState) -> HealingAgentState:
        """Load incident details."""
        log.info(f"Loading incident {state['incident_id']}")
        details = get_incident_details.invoke(state["incident_id"])

        return {
            **state,
            "product_id": details.get("product_id"),
            "product_name": details.get("product_name", details.get("product_id")),
            "diagnosis": details.get("description"),
            "status": "incident_loaded"
        }

    def analyze_impact(state: HealingAgentState) -> HealingAgentState:
        """Analyze the impact of the incident with LLM enhancement."""
        log.info(f"Analyzing impact for product {state.get('product_id')}")

        if not state.get("product_id"):
            return {
                **state,
                "recommendation": "manual_investigation",
                "root_cause": "unknown",
                "status": "no_product"
            }

        # Get impact data
        impact = get_downstream_impact.invoke(state["product_id"])
        fallback_info = check_pipeline_fallback.invoke(state["product_id"])

        downstream_count = len(impact.get("downstream_consumers", []))
        affected_users = impact.get("affected_users", 0)
        has_fallback = fallback_info.get("has_fallback", False)

        # LLM-powered root cause analysis
        root_cause_result = analyze_root_cause.invoke(
            incident_id=state["incident_id"],
            incident_type="data_quality_issue",
            description=state.get("diagnosis", "Unknown issue"),
            affected_product=state.get("product_name", state.get("product_id", "unknown")),
            severity=state.get("severity", "medium"),
            violation_details="",
            historical_incidents=[]
        )

        log.info(
            f"Root cause analysis complete",
            extra={
                "root_cause": root_cause_result.get("root_cause"),
                "confidence": root_cause_result.get("confidence"),
                "method": root_cause_result.get("method")
            }
        )

        return {
            **state,
            "root_cause": root_cause_result.get("root_cause", "unknown"),
            "root_cause_factors": root_cause_result.get("factors", []),
            "root_cause_confidence": root_cause_result.get("confidence", "low"),
            "fallback_available": has_fallback,
            "status": "impact_analyzed"
        }

    def reassess_incident_severity(state: HealingAgentState) -> HealingAgentState:
        """Reassess severity using LLM analysis."""
        log.info("Reassessing incident severity with LLM")

        if not state.get("product_id"):
            return {
                **state,
                "assessed_severity": state.get("severity", "medium"),
                "severity_changed": False,
                "status": "severity_assessed"
            }

        # Get impact metrics
        impact = get_downstream_impact.invoke(state["product_id"])
        downstream_count = len(impact.get("downstream_consumers", []))
        affected_users = impact.get("affected_users", 0)

        # LLM severity reassessment
        severity_result = reassess_severity.invoke(
            incident_id=state["incident_id"],
            current_severity=state.get("severity", "medium"),
            downstream_count=downstream_count,
            affected_users=affected_users,
            has_fallback=state.get("fallback_available", False),
            business_context=""
        )

        assessed = severity_result.get("assessed_severity", state.get("severity", "medium"))
        changed = severity_result.get("changed", False)

        if changed:
            log.warning(
                f"Severity changed from {state.get('severity')} to {assessed}",
                extra={"reason": severity_result.get("reasoning")}
            )

        return {
            **state,
            "assessed_severity": assessed,
            "severity_changed": changed,
            "urgency": severity_result.get("urgency", "day"),
            "escalation_needed": severity_result.get("escalation_needed", False),
            "status": "severity_assessed"
        }

    def route_by_severity(state: HealingAgentState) -> Literal["escalate", "auto_heal", "notify"]:
        """Route based on assessed severity and fallback availability."""
        # Use reassessed severity if available
        severity = state.get("assessed_severity") or state.get("severity", "medium")
        has_fallback = state.get("fallback_available", False)
        escalation_needed = state.get("escalation_needed", False)

        log.info(f"Routing decision: severity={severity}, fallback={has_fallback}, escalation={escalation_needed}")

        if severity == "critical" or escalation_needed:
            return "escalate"
        elif severity == "high" and has_fallback:
            return "auto_heal"
        elif severity == "high":
            return "escalate"
        else:
            return "notify"

    def escalate_to_human(state: HealingAgentState) -> HealingAgentState:
        """Escalate to human with LLM-generated remediation plan."""
        log.info("Escalating to human for approval")

        # Generate remediation plan using LLM
        remediation = create_remediation_plan.invoke(
            incident_type="data_quality_issue",
            root_cause=state.get("root_cause", "Unknown"),
            severity=state.get("assessed_severity") or state.get("severity", "critical"),
            affected_systems=[state.get("product_name", state.get("product_id", "unknown"))],
            available_resources=None
        )

        # Generate stakeholder narrative
        narrative_result = generate_incident_narrative.invoke(
            incident={
                "id": state["incident_id"],
                "type": "data_quality_issue",
                "severity": state.get("assessed_severity") or state.get("severity"),
                "product_name": state.get("product_name"),
                "description": state.get("diagnosis"),
                "status": "escalated"
            },
            impact_analysis={
                "downstream_count": len(state.get("root_cause_factors", [])),
                "affected_users": 0,
                "risk_score": "high" if state.get("assessed_severity") == "critical" else "medium"
            },
            actions_taken=["Incident detected", "Root cause analyzed", "Escalated to human review"]
        )

        return {
            **state,
            "action": "escalate_to_human",
            "remediation_steps": remediation.get("immediate_actions", []) + remediation.get("short_term_fixes", []),
            "recommendation": f"Critical incident requires human review. Root cause: {state.get('root_cause', 'Unknown')}",
            "incident_narrative": narrative_result.get("narrative"),
            "requires_approval": True,
            "approved": False,
            "status": "awaiting_approval"
        }

    def auto_heal(state: HealingAgentState) -> HealingAgentState:
        """Automatically heal by activating fallback with LLM guidance."""
        log.info("Auto-healing: activating fallback")

        fallback_activated = False
        if state.get("product_id"):
            fallback_info = check_pipeline_fallback.invoke(state["product_id"])
            if fallback_info.get("fallbacks"):
                pipeline_id = fallback_info["fallbacks"][0]["pipeline_id"]
                activate_fallback.invoke(pipeline_id)
                fallback_activated = True

        # Generate remediation steps for documentation
        remediation = create_remediation_plan.invoke(
            incident_type="data_quality_issue",
            root_cause=state.get("root_cause", "Unknown"),
            severity=state.get("assessed_severity") or state.get("severity", "high"),
            affected_systems=[state.get("product_name", state.get("product_id", "unknown"))],
            available_resources=["fallback_pipeline"]
        )

        recommendation = "Fallback source activated automatically. "
        recommendation += f"Root cause: {state.get('root_cause', 'Unknown')}. "
        recommendation += f"Confidence: {state.get('root_cause_confidence', 'low')}."

        return {
            **state,
            "action": "activate_fallback",
            "remediation_steps": remediation.get("preventive_measures", []),
            "recommendation": recommendation,
            "requires_approval": False,
            "status": "healed"
        }

    def notify_steward(state: HealingAgentState) -> HealingAgentState:
        """Notify data steward for low severity issues with context."""
        log.info("Notifying data steward")

        recommendation = f"Low severity issue detected. Root cause: {state.get('root_cause', 'Unknown')}. "
        recommendation += "Data steward notified for review."

        return {
            **state,
            "action": "notify_steward",
            "recommendation": recommendation,
            "requires_approval": False,
            "status": "notified"
        }

    def persist_execution(state: HealingAgentState) -> HealingAgentState:
        """Persist the agent execution to Neo4j with full context."""
        log.info(f"Persisting execution for incident {state['incident_id']}")

        if state.get("incident_id"):
            # Build detailed outcome
            outcome = {
                "action": state.get("action"),
                "root_cause": state.get("root_cause"),
                "root_cause_confidence": state.get("root_cause_confidence"),
                "assessed_severity": state.get("assessed_severity"),
                "severity_changed": state.get("severity_changed"),
                "recommendation": state.get("recommendation", "")[:500]
            }

            record_agent_execution.invoke(
                state["incident_id"],
                "HealingAgent",
                str(outcome)
            )

            # Update incident status
            new_status = "mitigating" if state.get("action") != "escalate_to_human" else "escalated"
            update_incident_status.invoke(state["incident_id"], new_status)

        return {
            **state,
            "status": "completed"
        }

    # Build the graph with LLM-enhanced nodes
    graph = StateGraph(HealingAgentState)

    # Add nodes
    graph.add_node("load_incident", load_incident)
    graph.add_node("analyze_impact", analyze_impact)
    graph.add_node("reassess_severity", reassess_incident_severity)
    graph.add_node("escalate", escalate_to_human)
    graph.add_node("auto_heal", auto_heal)
    graph.add_node("notify", notify_steward)
    graph.add_node("persist", persist_execution)

    # Set entry point
    graph.set_entry_point("load_incident")

    # Add edges - now with severity reassessment step
    graph.add_edge("load_incident", "analyze_impact")
    graph.add_edge("analyze_impact", "reassess_severity")

    # Conditional routing based on assessed severity
    graph.add_conditional_edges(
        "reassess_severity",
        route_by_severity,
        {
            "escalate": "escalate",
            "auto_heal": "auto_heal",
            "notify": "notify"
        }
    )

    # All paths lead to persist
    graph.add_edge("escalate", "persist")
    graph.add_edge("auto_heal", "persist")
    graph.add_edge("notify", "persist")
    graph.add_edge("persist", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=get_checkpointer())
