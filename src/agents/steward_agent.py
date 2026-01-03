"""
Steward Agent (LLM-Enhanced)
AI Data Steward for governance and quality management.
Uses LLM for intelligent recommendations and remediation planning.
"""
from typing import TypedDict, List, Optional, Literal
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import (
    get_incident_details,
    get_product_health,
    record_agent_execution
)
from src.agents.tools.llm_tools import (
    analyze_root_cause,
    create_remediation_plan,
    generate_incident_narrative
)
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available


class StewardAgentState(TypedDict):
    """State for the AI data steward agent with LLM enhancements."""
    incident_id: str
    severity: str
    product_id: Optional[str]
    product_name: Optional[str]

    # Analysis
    analysis: Optional[str]
    quality_score: Optional[float]
    root_cause: Optional[str]
    root_cause_confidence: Optional[str]

    # LLM-generated recommendations
    remediation_steps: List[str]
    preventive_measures: List[str]
    governance_recommendations: List[str]

    # Notifications
    notifications_sent: List[str]
    stakeholder_narrative: Optional[str]

    status: str


# Governance recommendation prompts
GOVERNANCE_PROMPT = """You are a data governance expert reviewing an incident. Based on the analysis, provide governance recommendations.

Incident Analysis:
- Type: {incident_type}
- Severity: {severity}
- Product: {product_name}
- Quality Score: {quality_score}
- Root Cause: {root_cause}

Provide specific governance recommendations for:
1. Contract/Rule improvements
2. Monitoring enhancements
3. Documentation updates
4. Process improvements
5. Training needs

Format as bullet points, each starting with the category in brackets.
"""


def build_steward_agent():
    """Build an enhanced AI data steward agent with LLM capabilities."""
    log = get_agent_logger("StewardAgent")

    def analyze_incident(state: StewardAgentState) -> StewardAgentState:
        """Analyze the incident and determine quality issues with LLM."""
        log.info(f"Analyzing incident {state['incident_id']}")

        details = get_incident_details.invoke(state["incident_id"])
        product_id = details.get("product_id")
        product_name = details.get("product_name", product_id)

        analysis = f"Incident Type: {details.get('type', 'unknown')}\n"
        analysis += f"Description: {details.get('description', 'N/A')}\n"

        quality_score = 85.0
        if product_id:
            health = get_product_health.invoke(product_id)
            analysis += f"Product Health: {health.get('health', 'unknown')}\n"
            quality_score = health.get("quality_score", 85.0)
            analysis += f"Quality Score: {quality_score}\n"

        # LLM root cause analysis
        root_cause_result = analyze_root_cause.invoke(
            incident_id=state["incident_id"],
            incident_type=details.get("type", "data_quality_issue"),
            description=details.get("description", "Unknown issue"),
            affected_product=product_name or "unknown",
            severity=state.get("severity", "medium"),
            violation_details="",
            historical_incidents=[]
        )

        log.info(
            f"Root cause analysis complete for steward review",
            extra={
                "root_cause": root_cause_result.get("root_cause"),
                "confidence": root_cause_result.get("confidence")
            }
        )

        return {
            **state,
            "product_id": product_id,
            "product_name": product_name,
            "analysis": analysis,
            "quality_score": quality_score,
            "root_cause": root_cause_result.get("root_cause", "unknown"),
            "root_cause_confidence": root_cause_result.get("confidence", "low"),
            "status": "analyzed"
        }

    def route_by_quality(state: StewardAgentState) -> Literal["critical_remediation", "standard_remediation"]:
        """Route based on quality score and severity."""
        quality_score = state.get("quality_score", 100)
        severity = state.get("severity", "medium")
        confidence = state.get("root_cause_confidence", "low")

        # Consider root cause confidence in routing
        if severity == "critical" or quality_score < 50:
            return "critical_remediation"
        elif confidence == "high" and quality_score < 70:
            # High confidence root cause with poor quality -> critical
            return "critical_remediation"
        return "standard_remediation"

    def critical_remediation(state: StewardAgentState) -> StewardAgentState:
        """Handle critical remediation with LLM-generated steps."""
        log.info("Generating critical remediation plan with LLM")

        # Use LLM for remediation planning
        remediation = create_remediation_plan.invoke(
            incident_type="data_quality_critical",
            root_cause=state.get("root_cause", "Unknown"),
            severity="critical",
            affected_systems=[state.get("product_name", state.get("product_id", "unknown"))],
            available_resources=["on-call team", "rollback capability"]
        )

        immediate_actions = remediation.get("immediate_actions", [])
        if not immediate_actions:
            immediate_actions = [
                "URGENT: Immediately pause data ingestion",
                "Notify all downstream consumers via emergency channel",
                "Investigate root cause with on-call team",
                "Prepare rollback plan",
                "Schedule post-mortem review"
            ]

        # Generate governance recommendations
        governance_recs = _generate_governance_recommendations(state)

        return {
            **state,
            "remediation_steps": immediate_actions + remediation.get("short_term_fixes", []),
            "preventive_measures": remediation.get("preventive_measures", []),
            "governance_recommendations": governance_recs,
            "status": "critical_remediation_planned"
        }

    def standard_remediation(state: StewardAgentState) -> StewardAgentState:
        """Handle standard remediation with LLM guidance."""
        log.info("Generating standard remediation plan with LLM")

        severity = state.get("severity", "medium")

        # Use LLM for remediation planning
        remediation = create_remediation_plan.invoke(
            incident_type="data_quality_standard",
            root_cause=state.get("root_cause", "Unknown"),
            severity=severity,
            affected_systems=[state.get("product_name", state.get("product_id", "unknown"))],
            available_resources=None
        )

        if severity == "high":
            default_steps = [
                "Review recent data changes",
                "Check contract violations",
                "Notify data owners",
                "Schedule review meeting"
            ]
        else:
            default_steps = [
                "Log incident for tracking",
                "Monitor for recurrence",
                "Update documentation if needed"
            ]

        remediation_steps = remediation.get("immediate_actions", []) or default_steps

        # Generate governance recommendations
        governance_recs = _generate_governance_recommendations(state)

        return {
            **state,
            "remediation_steps": remediation_steps,
            "preventive_measures": remediation.get("preventive_measures", []),
            "governance_recommendations": governance_recs,
            "status": "remediation_planned"
        }

    def notify_stakeholders(state: StewardAgentState) -> StewardAgentState:
        """Send notifications with LLM-generated narrative."""
        log.info("Notifying stakeholders with LLM-generated narrative")

        notifications = []
        severity = state.get("severity", "medium")

        # Generate stakeholder narrative
        narrative_result = generate_incident_narrative.invoke(
            incident={
                "id": state["incident_id"],
                "type": "data_quality_issue",
                "severity": severity,
                "product_name": state.get("product_name"),
                "description": state.get("analysis"),
                "status": state.get("status")
            },
            impact_analysis={
                "quality_score": state.get("quality_score", 0),
                "root_cause": state.get("root_cause"),
                "confidence": state.get("root_cause_confidence")
            },
            actions_taken=state.get("remediation_steps", [])[:3]
        )

        if severity == "critical":
            notifications.append("PAGER: On-call team alerted")
            notifications.append("Email sent to data owners (URGENT)")
            notifications.append("Slack notification to #data-quality-critical")
        elif severity == "high":
            notifications.append("Email sent to data owners")
            notifications.append("Slack notification to #data-quality")

        notifications.append("Incident logged in tracking system")

        # Record execution with LLM insights
        if state.get("incident_id"):
            outcome = {
                "analysis": state.get("analysis", "")[:200],
                "root_cause": state.get("root_cause"),
                "confidence": state.get("root_cause_confidence"),
                "remediation_count": len(state.get("remediation_steps", [])),
                "governance_recommendations": len(state.get("governance_recommendations", []))
            }
            record_agent_execution.invoke(
                state["incident_id"],
                "StewardAgent",
                str(outcome)
            )

        return {
            **state,
            "notifications_sent": notifications,
            "stakeholder_narrative": narrative_result.get("narrative"),
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(StewardAgentState)

    graph.add_node("analyze", analyze_incident)
    graph.add_node("critical_remediation", critical_remediation)
    graph.add_node("standard_remediation", standard_remediation)
    graph.add_node("notify", notify_stakeholders)

    graph.set_entry_point("analyze")

    # Conditional routing based on quality
    graph.add_conditional_edges(
        "analyze",
        route_by_quality,
        {
            "critical_remediation": "critical_remediation",
            "standard_remediation": "standard_remediation"
        }
    )

    graph.add_edge("critical_remediation", "notify")
    graph.add_edge("standard_remediation", "notify")
    graph.add_edge("notify", END)

    return graph.compile(checkpointer=get_checkpointer())


def _generate_governance_recommendations(state: StewardAgentState) -> List[str]:
    """Generate governance recommendations using LLM or fallback."""
    from src.core.llm import get_llm_if_available

    llm = get_llm_if_available()
    if not llm:
        # Fallback recommendations
        return [
            "[Contract] Review and tighten data quality rules",
            "[Monitoring] Add alerts for similar patterns",
            "[Documentation] Update data product documentation",
            "[Process] Review data ingestion procedures"
        ]

    try:
        prompt = GOVERNANCE_PROMPT.format(
            incident_type="data_quality_issue",
            severity=state.get("severity", "medium"),
            product_name=state.get("product_name", "unknown"),
            quality_score=state.get("quality_score", 0),
            root_cause=state.get("root_cause", "Unknown")
        )

        response = llm.invoke(prompt)
        recommendations = []

        for line in response.content.strip().split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("•") or line.startswith("["):
                recommendations.append(line.lstrip("-•").strip())

        return recommendations[:6] if recommendations else [
            "[Contract] Review and tighten data quality rules",
            "[Monitoring] Add alerts for similar patterns"
        ]

    except Exception as e:
        log = get_agent_logger("StewardAgent")
        log.warning(f"LLM governance recommendations failed: {e}")
        return [
            "[Contract] Review and tighten data quality rules",
            "[Monitoring] Add alerts for similar patterns",
            "[Documentation] Update data product documentation"
        ]
