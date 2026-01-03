"""
Impact Agent (LLM-Enhanced)
Analyzes downstream impact of data product failures.
Uses LLM for risk assessment narratives and business impact translation.
"""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import get_product_health, get_downstream_impact
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available


class ImpactAgentState(TypedDict):
    """State for the impact analysis agent with LLM enhancements."""
    product_id: str
    product_name: Optional[str]
    incident_id: Optional[str]

    # Impact data
    downstream_products: List[dict]
    affected_pipelines: List[dict]
    affected_users: int
    affected_domains: List[str]

    # LLM-enhanced analysis
    business_impact: str
    risk_score: float
    risk_assessment: Optional[str]
    impact_narrative: Optional[str]
    mitigation_suggestions: Optional[List[str]]

    status: str


# Impact narrative prompt
IMPACT_NARRATIVE_PROMPT = """You are a data platform expert analyzing the downstream impact of a data product failure.

Failed Product: {product_name}
Downstream Products Affected: {downstream_count}
Affected Pipelines: {pipeline_count}
Users Impacted: {affected_users}
Risk Score: {risk_score}/100

Downstream Dependencies:
{downstream_details}

Provide a clear impact analysis:
1. EXECUTIVE_SUMMARY: 2-3 sentences explaining the business impact
2. CASCADING_EFFECTS: What will break if this isn't fixed?
3. TIMELINE: How quickly will impact be felt? (immediate/hours/days)
4. PRIORITY_ACTIONS: Top 3 actions to mitigate impact

Keep responses concise and actionable.
"""

RISK_ASSESSMENT_PROMPT = """Assess the risk level of this data product failure.

Product: {product_name}
Downstream Products: {downstream_count}
Users Affected: {affected_users}
Current Risk Score: {risk_score}

Downstream Products:
{downstream_list}

Provide:
RISK_LEVEL: critical/high/medium/low
BUSINESS_AREAS: List affected business areas
FINANCIAL_IMPACT: Estimated impact (high/medium/low/minimal)
URGENCY: How quickly must this be addressed?
JUSTIFICATION: Brief explanation of your assessment
"""


def build_impact_agent():
    """Build an enhanced impact analysis agent with LLM capabilities."""
    log = get_agent_logger("ImpactAgent")

    def load_product(state: ImpactAgentState) -> ImpactAgentState:
        """Load product details."""
        log.info(f"Loading product {state['product_id']}")

        health = get_product_health.invoke(state["product_id"])
        product_name = health.get("name", state["product_id"])

        return {
            **state,
            "product_name": product_name,
            "status": "product_loaded"
        }

    def analyze_downstream(state: ImpactAgentState) -> ImpactAgentState:
        """Analyze downstream impact."""
        log.info("Analyzing downstream dependencies")

        impact = get_downstream_impact.invoke(state["product_id"])

        downstream_products = impact.get("downstream_consumers", [])
        affected_pipelines = impact.get("affected_pipelines", [])
        affected_users = impact.get("affected_users", 0)

        # Extract affected domains
        affected_domains = list(set(
            p.get("domain", "Unknown")
            for p in downstream_products
            if p.get("domain")
        ))

        return {
            **state,
            "downstream_products": downstream_products,
            "affected_pipelines": affected_pipelines,
            "affected_users": affected_users,
            "affected_domains": affected_domains,
            "status": "downstream_analyzed"
        }

    def calculate_risk(state: ImpactAgentState) -> ImpactAgentState:
        """Calculate overall risk score with LLM enhancement."""
        log.info("Calculating risk score with LLM assessment")

        num_products = len(state.get("downstream_products", []))
        num_pipelines = len(state.get("affected_pipelines", []))
        num_users = state.get("affected_users", 0)
        num_domains = len(state.get("affected_domains", []))

        # Enhanced risk calculation
        base_risk = (num_products * 10) + (num_pipelines * 5) + (num_users * 2)
        domain_multiplier = 1 + (num_domains * 0.1)  # Cross-domain impact increases risk
        risk_score = min(100.0, float(base_risk * domain_multiplier))

        # Determine business impact level
        if risk_score >= 70:
            business_impact = "critical"
        elif risk_score >= 40:
            business_impact = "high"
        elif risk_score >= 20:
            business_impact = "medium"
        else:
            business_impact = "low"

        # LLM risk assessment
        risk_assessment = _generate_risk_assessment(state, risk_score)

        log.info(
            f"Risk calculation complete",
            extra={
                "risk_score": risk_score,
                "business_impact": business_impact,
                "downstream_count": num_products,
                "domains_affected": num_domains
            }
        )

        return {
            **state,
            "risk_score": risk_score,
            "business_impact": business_impact,
            "risk_assessment": risk_assessment,
            "status": "risk_calculated"
        }

    def generate_narrative(state: ImpactAgentState) -> ImpactAgentState:
        """Generate impact narrative and mitigation suggestions using LLM."""
        log.info("Generating impact narrative with LLM")

        narrative = _generate_impact_narrative(state)
        mitigations = _generate_mitigation_suggestions(state)

        return {
            **state,
            "impact_narrative": narrative,
            "mitigation_suggestions": mitigations,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(ImpactAgentState)

    graph.add_node("load", load_product)
    graph.add_node("analyze", analyze_downstream)
    graph.add_node("calculate", calculate_risk)
    graph.add_node("narrative", generate_narrative)

    graph.set_entry_point("load")
    graph.add_edge("load", "analyze")
    graph.add_edge("analyze", "calculate")
    graph.add_edge("calculate", "narrative")
    graph.add_edge("narrative", END)

    return graph.compile(checkpointer=get_checkpointer())


def _generate_risk_assessment(state: ImpactAgentState, risk_score: float) -> Optional[str]:
    """Generate risk assessment using LLM."""
    llm = get_llm_if_available()
    if not llm:
        return None

    try:
        downstream_list = "\n".join(
            f"- {p.get('name', p.get('id', 'Unknown'))}: {p.get('domain', 'Unknown')} domain"
            for p in state.get("downstream_products", [])[:10]
        )

        prompt = RISK_ASSESSMENT_PROMPT.format(
            product_name=state.get("product_name", state.get("product_id", "Unknown")),
            downstream_count=len(state.get("downstream_products", [])),
            affected_users=state.get("affected_users", 0),
            risk_score=risk_score,
            downstream_list=downstream_list or "No downstream products"
        )

        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        log = get_agent_logger("ImpactAgent")
        log.warning(f"LLM risk assessment failed: {e}")
        return None


def _generate_impact_narrative(state: ImpactAgentState) -> Optional[str]:
    """Generate impact narrative using LLM."""
    llm = get_llm_if_available()

    downstream_details = "\n".join(
        f"- {p.get('name', p.get('id', 'Unknown'))} ({p.get('domain', 'Unknown')} domain)"
        for p in state.get("downstream_products", [])[:10]
    )

    if llm:
        try:
            prompt = IMPACT_NARRATIVE_PROMPT.format(
                product_name=state.get("product_name", state.get("product_id", "Unknown")),
                downstream_count=len(state.get("downstream_products", [])),
                pipeline_count=len(state.get("affected_pipelines", [])),
                affected_users=state.get("affected_users", 0),
                risk_score=state.get("risk_score", 0),
                downstream_details=downstream_details or "None identified"
            )

            response = llm.invoke(prompt)
            return response.content

        except Exception as e:
            log = get_agent_logger("ImpactAgent")
            log.warning(f"LLM narrative generation failed: {e}")

    # Fallback template narrative
    impact_level = state.get("business_impact", "medium")
    downstream_count = len(state.get("downstream_products", []))
    affected_users = state.get("affected_users", 0)
    affected_domains = state.get("affected_domains", [])

    narrative = f"""
**Impact Assessment for {state.get('product_name', state.get('product_id', 'Unknown'))}**

**Executive Summary:**
This {impact_level} severity incident affects {downstream_count} downstream data products and potentially impacts {affected_users} users.

**Cascading Effects:**
- {downstream_count} data products depend on this source
- {len(state.get('affected_pipelines', []))} pipelines will be affected
- Domains impacted: {', '.join(affected_domains) if affected_domains else 'Unknown'}

**Timeline:**
Impact will be felt {'immediately' if impact_level == 'critical' else 'within hours' if impact_level == 'high' else 'within 24 hours'}.

**Risk Score:** {state.get('risk_score', 0):.1f}/100 ({impact_level.upper()})
"""
    return narrative.strip()


def _generate_mitigation_suggestions(state: ImpactAgentState) -> List[str]:
    """Generate mitigation suggestions using LLM or fallback."""
    impact_level = state.get("business_impact", "medium")

    llm = get_llm_if_available()
    if llm:
        try:
            prompt = f"""Given a {impact_level} severity data product failure affecting {len(state.get('downstream_products', []))} downstream products, suggest 4-5 specific mitigation actions.

Product: {state.get('product_name', 'Unknown')}
Risk Score: {state.get('risk_score', 0)}/100

Format as a numbered list of actionable steps."""

            response = llm.invoke(prompt)
            suggestions = []
            for line in response.content.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    suggestions.append(line.lstrip("0123456789.-) ").strip())

            if suggestions:
                return suggestions[:5]

        except Exception as e:
            log = get_agent_logger("ImpactAgent")
            log.warning(f"LLM mitigation suggestions failed: {e}")

    # Fallback suggestions based on severity
    if impact_level == "critical":
        return [
            "Immediately notify all downstream product owners",
            "Activate fallback data sources if available",
            "Pause dependent pipeline executions",
            "Escalate to incident management team",
            "Begin root cause investigation"
        ]
    elif impact_level == "high":
        return [
            "Notify affected team leads",
            "Check for available fallback sources",
            "Monitor downstream product health",
            "Prepare communication for stakeholders"
        ]
    else:
        return [
            "Log incident for tracking",
            "Monitor for impact escalation",
            "Schedule review with product owners"
        ]
