"""
SLA Monitoring Agent (LLM-Enhanced)
Monitors SLA compliance and predicts/detects breaches.
Uses LLM for intelligent breach analysis and recommendation generation.
"""
from typing import TypedDict, List, Optional, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from operator import add
from datetime import datetime, timedelta
import uuid

from src.agents.checkpointer import get_checkpointer
from src.agents.checkpointer import get_thread_config
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available
from src.graph.manager import Neo4jManager


class SLAAgentState(TypedDict):
    """State for the SLA monitoring agent."""
    product_ids: Optional[List[str]]  # Products to monitor (None = all)

    # SLA data
    slas: List[dict]
    current_metrics: dict

    # Analysis results
    breached_slas: List[dict]
    at_risk_slas: List[dict]
    healthy_slas: List[dict]

    # LLM-enhanced analysis
    breach_analysis: Optional[str]
    risk_predictions: Optional[List[dict]]
    recommendations: Optional[List[str]]
    trend_analysis: Optional[str]

    # Notifications
    notifications: List[dict]
    escalations: List[dict]

    status: str
    messages: Annotated[List[BaseMessage], add]


def _get_slas_from_graph(product_ids: Optional[List[str]] = None) -> List[dict]:
    """Fetch SLAs from the knowledge graph."""
    with Neo4jManager() as mgr:
        if product_ids:
            query = """
            MATCH (p:DataProduct)-[:HAS_CONTRACT]->(c:Contract)-[:HAS_SLA]->(s:SLA)
            WHERE p.id IN $product_ids
            RETURN s.id as sla_id, s.name as sla_name,
                   s.target_value as target_value, s.metric_type as metric_type,
                   s.threshold as threshold, s.is_active as is_active,
                   c.id as contract_id, c.name as contract_name,
                   p.id as product_id, p.name as product_name
            """
            results = mgr.execute_query(query, {"product_ids": product_ids})
        else:
            query = """
            MATCH (s:SLA)
            OPTIONAL MATCH (c:Contract)-[:HAS_SLA]->(s)
            OPTIONAL MATCH (c)<-[:HAS_CONTRACT]-(p:DataProduct)
            WHERE s.is_active = true OR s.is_active IS NULL
            RETURN s.id as sla_id, s.name as sla_name,
                   s.target_value as target_value, s.metric_type as metric_type,
                   s.threshold as threshold, s.is_active as is_active,
                   c.id as contract_id, c.name as contract_name,
                   p.id as product_id, p.name as product_name
            """
            results = mgr.execute_query(query, {})

        return [dict(r) for r in results]


def _get_metrics_for_products(product_ids: List[str]) -> dict:
    """Fetch current metrics for products."""
    with Neo4jManager() as mgr:
        metrics = {}
        for pid in product_ids:
            query = """
            MATCH (p:DataProduct {id: $id})
            OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
            OPTIONAL MATCH (m:MetricSnapshot {product_id: $id})
            RETURN p.id as id, p.name as name,
                   count(i) as open_incidents,
                   m.freshness_seconds as freshness_seconds,
                   m.availability_percent as availability_percent,
                   m.latency_p99_ms as latency_p99_ms,
                   m.error_rate as error_rate,
                   m.null_rate as null_rate
            LIMIT 1
            """
            result = mgr.execute_query(query, {"id": pid})
            if result:
                # Mock metrics if not available
                r = dict(result[0])
                metrics[pid] = {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "open_incidents": r.get("open_incidents", 0),
                    "freshness_seconds": r.get("freshness_seconds", 300),
                    "availability_percent": r.get("availability_percent", 99.5),
                    "latency_p99_ms": r.get("latency_p99_ms", 50),
                    "error_rate": r.get("error_rate", 0.01),
                    "null_rate": r.get("null_rate", 0.02)
                }
        return metrics


def _analyze_sla_breach_with_llm(sla: dict, metrics: dict) -> dict:
    """Use LLM to analyze SLA breach and provide recommendations."""
    llm = get_llm_if_available()

    if llm:
        prompt = f"""Analyze this SLA breach and provide recommendations:

SLA Details:
- Name: {sla.get('sla_name')}
- Metric Type: {sla.get('metric_type')}
- Target Value: {sla.get('target_value')}
- Threshold: {sla.get('threshold')}
- Product: {sla.get('product_name')}

Current Metrics:
{metrics}

Provide:
1. Root cause analysis (2-3 sentences)
2. Immediate action to take
3. Long-term fix recommendation
4. Estimated time to resolution

Format as JSON with keys: root_cause, immediate_action, long_term_fix, estimated_resolution"""

        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse LLM response (simplified)
            import json
            try:
                # Try to extract JSON
                if '{' in content:
                    json_start = content.index('{')
                    json_end = content.rindex('}') + 1
                    return json.loads(content[json_start:json_end])
            except:
                pass

            return {
                "root_cause": content[:200],
                "immediate_action": "Investigate the metric deviation",
                "long_term_fix": "Review SLA thresholds and implement monitoring",
                "estimated_resolution": "1-2 hours",
                "llm_analysis": content
            }
        except Exception as e:
            return {
                "root_cause": "Unable to determine - LLM analysis failed",
                "immediate_action": "Manual investigation required",
                "long_term_fix": "Review SLA configuration",
                "estimated_resolution": "Unknown",
                "error": str(e)
            }

    # Non-LLM fallback
    return {
        "root_cause": f"SLA {sla.get('metric_type')} threshold exceeded",
        "immediate_action": "Check data pipeline health",
        "long_term_fix": "Implement alerting thresholds before SLA breach",
        "estimated_resolution": "30 minutes to 2 hours"
    }


def _predict_risks_with_llm(slas: List[dict], metrics: dict) -> List[dict]:
    """Use LLM to predict which SLAs are at risk of breach."""
    llm = get_llm_if_available()

    at_risk = []
    for sla in slas:
        product_id = sla.get("product_id")
        if not product_id or product_id not in metrics:
            continue

        product_metrics = metrics[product_id]
        metric_type = sla.get("metric_type", "").lower()
        target = sla.get("target_value") or sla.get("threshold")

        if target is None:
            continue

        # Check if approaching threshold
        current_value = None
        risk_percentage = 0

        if "freshness" in metric_type:
            current_value = product_metrics.get("freshness_seconds", 0)
            if target > 0:
                risk_percentage = (current_value / target) * 100
        elif "availability" in metric_type:
            current_value = product_metrics.get("availability_percent", 100)
            # For availability, lower is worse
            if target > 0:
                risk_percentage = ((100 - current_value) / (100 - target)) * 100 if target < 100 else 0
        elif "latency" in metric_type:
            current_value = product_metrics.get("latency_p99_ms", 0)
            if target > 0:
                risk_percentage = (current_value / target) * 100
        elif "error" in metric_type:
            current_value = product_metrics.get("error_rate", 0)
            if target > 0:
                risk_percentage = (current_value / target) * 100

        # Flag as at-risk if > 80% of threshold
        if risk_percentage > 80:
            at_risk.append({
                **sla,
                "current_value": current_value,
                "risk_percentage": min(risk_percentage, 100),
                "time_to_breach": "< 1 hour" if risk_percentage > 95 else "1-4 hours"
            })

    return at_risk


def build_sla_agent():
    """
    Build an SLA monitoring agent with LLM capabilities:
    - Monitors SLA compliance across products
    - Predicts potential breaches
    - Provides intelligent recommendations
    - Generates stakeholder notifications
    """
    log = get_agent_logger("SLAAgent")

    def load_slas(state: SLAAgentState) -> SLAAgentState:
        """Load SLAs and current metrics."""
        log.info("Loading SLAs and metrics")

        product_ids = state.get("product_ids")
        slas = _get_slas_from_graph(product_ids)

        # Get unique product IDs
        all_product_ids = list(set(
            s["product_id"] for s in slas if s.get("product_id")
        ))

        metrics = _get_metrics_for_products(all_product_ids) if all_product_ids else {}

        log.info(f"Loaded {len(slas)} SLAs for {len(all_product_ids)} products")

        return {
            **state,
            "slas": slas,
            "current_metrics": metrics,
            "status": "slas_loaded"
        }

    def check_compliance(state: SLAAgentState) -> SLAAgentState:
        """Check current SLA compliance status."""
        log.info("Checking SLA compliance")

        breached = []
        healthy = []

        for sla in state.get("slas", []):
            product_id = sla.get("product_id")
            if not product_id:
                continue

            metrics = state.get("current_metrics", {}).get(product_id, {})
            metric_type = sla.get("metric_type", "").lower()
            target = sla.get("target_value") or sla.get("threshold")

            if target is None:
                healthy.append(sla)
                continue

            is_breached = False
            current_value = None

            if "freshness" in metric_type:
                current_value = metrics.get("freshness_seconds", 0)
                is_breached = current_value > target
            elif "availability" in metric_type:
                current_value = metrics.get("availability_percent", 100)
                is_breached = current_value < target
            elif "latency" in metric_type:
                current_value = metrics.get("latency_p99_ms", 0)
                is_breached = current_value > target
            elif "error" in metric_type:
                current_value = metrics.get("error_rate", 0)
                is_breached = current_value > target

            sla_with_status = {
                **sla,
                "current_value": current_value,
                "is_compliant": not is_breached
            }

            if is_breached:
                breached.append(sla_with_status)
            else:
                healthy.append(sla_with_status)

        log.info(f"Compliance check: {len(breached)} breached, {len(healthy)} healthy")

        return {
            **state,
            "breached_slas": breached,
            "healthy_slas": healthy,
            "status": "compliance_checked"
        }

    def predict_risks(state: SLAAgentState) -> SLAAgentState:
        """Predict which SLAs are at risk of breach."""
        log.info("Predicting SLA breach risks")

        # Filter to only check healthy SLAs for risk
        healthy_slas = state.get("healthy_slas", [])
        metrics = state.get("current_metrics", {})

        at_risk = _predict_risks_with_llm(healthy_slas, metrics)

        log.info(f"Identified {len(at_risk)} SLAs at risk")

        return {
            **state,
            "at_risk_slas": at_risk,
            "risk_predictions": [
                {
                    "sla_id": r["sla_id"],
                    "sla_name": r["sla_name"],
                    "risk_level": "high" if r["risk_percentage"] > 95 else "medium",
                    "time_to_breach": r["time_to_breach"]
                }
                for r in at_risk
            ],
            "status": "risks_predicted"
        }

    def route_by_status(state: SLAAgentState) -> Literal["analyze_breaches", "generate_report"]:
        """Route based on whether there are breaches."""
        if state.get("breached_slas"):
            return "analyze_breaches"
        return "generate_report"

    def analyze_breaches(state: SLAAgentState) -> SLAAgentState:
        """Analyze breached SLAs with LLM."""
        log.info("Analyzing SLA breaches with LLM")

        breached = state.get("breached_slas", [])
        metrics = state.get("current_metrics", {})

        analyses = []
        recommendations = []
        escalations = []

        for sla in breached:
            product_id = sla.get("product_id")
            product_metrics = metrics.get(product_id, {})

            analysis = _analyze_sla_breach_with_llm(sla, product_metrics)
            analyses.append({
                "sla_id": sla.get("sla_id"),
                "sla_name": sla.get("sla_name"),
                **analysis
            })

            recommendations.append(
                f"{sla.get('sla_name')}: {analysis.get('immediate_action', 'Investigate immediately')}"
            )

            # Escalate critical breaches
            if sla.get("metric_type", "").lower() in ["availability", "critical"]:
                escalations.append({
                    "type": "sla_breach",
                    "sla_id": sla.get("sla_id"),
                    "sla_name": sla.get("sla_name"),
                    "product": sla.get("product_name"),
                    "severity": "critical",
                    "message": analysis.get("root_cause", "SLA breach detected")
                })

        # Generate overall breach analysis
        llm = get_llm_if_available()
        breach_summary = None

        if llm and len(breached) > 0:
            try:
                prompt = f"""Summarize these SLA breaches in 2-3 sentences for executive stakeholders:

Breached SLAs: {len(breached)}
Products affected: {', '.join(set(s.get('product_name', 'Unknown') for s in breached))}
Breach types: {', '.join(set(s.get('metric_type', 'Unknown') for s in breached))}

Individual analyses:
{analyses[:3]}  # Limit for context

Provide a concise executive summary."""

                response = llm.invoke(prompt)
                breach_summary = response.content if hasattr(response, 'content') else str(response)
            except:
                breach_summary = f"{len(breached)} SLA breaches detected requiring immediate attention."
        else:
            breach_summary = f"{len(breached)} SLA breaches detected requiring immediate attention."

        return {
            **state,
            "breach_analysis": breach_summary,
            "recommendations": recommendations,
            "escalations": escalations,
            "status": "breaches_analyzed"
        }

    def generate_report(state: SLAAgentState) -> SLAAgentState:
        """Generate SLA compliance report."""
        log.info("Generating SLA compliance report")

        breached = state.get("breached_slas", [])
        at_risk = state.get("at_risk_slas", [])
        healthy = state.get("healthy_slas", [])

        total = len(breached) + len(at_risk) + len(healthy)
        compliance_rate = (len(healthy) / total * 100) if total > 0 else 100

        notifications = []

        # Notify about at-risk SLAs
        for sla in at_risk:
            notifications.append({
                "type": "sla_at_risk",
                "sla_id": sla.get("sla_id"),
                "sla_name": sla.get("sla_name"),
                "product": sla.get("product_name"),
                "severity": "warning",
                "message": f"SLA at {sla.get('risk_percentage', 0):.0f}% of threshold. {sla.get('time_to_breach', '')} until breach.",
                "recommended_action": "Monitor closely and prepare mitigation"
            })

        # Generate trend analysis
        llm = get_llm_if_available()
        trend_analysis = None

        if llm:
            try:
                prompt = f"""Based on these SLA metrics, provide a brief trend analysis:

Total SLAs: {total}
Compliant: {len(healthy)} ({compliance_rate:.1f}%)
At Risk: {len(at_risk)}
Breached: {len(breached)}

Provide 2-3 sentences about the overall SLA health trend and any patterns observed."""

                response = llm.invoke(prompt)
                trend_analysis = response.content if hasattr(response, 'content') else str(response)
            except:
                trend_analysis = f"SLA compliance is at {compliance_rate:.1f}%. {len(at_risk)} SLAs need attention."
        else:
            trend_analysis = f"SLA compliance is at {compliance_rate:.1f}%. {len(at_risk)} SLAs need attention."

        return {
            **state,
            "notifications": state.get("notifications", []) + notifications,
            "trend_analysis": trend_analysis,
            "status": "report_generated"
        }

    def persist_results(state: SLAAgentState) -> SLAAgentState:
        """Persist SLA monitoring results."""
        log.info("Persisting SLA monitoring results")

        # Store execution record
        with Neo4jManager() as mgr:
            mgr.execute_query("""
                CREATE (e:AgentExecution {
                    id: 'sla_' + toString(datetime()),
                    agent: 'SLAAgent',
                    outcome: $outcome,
                    created_at: datetime()
                })
            """, {
                "outcome": str({
                    "breached_count": len(state.get("breached_slas", [])),
                    "at_risk_count": len(state.get("at_risk_slas", [])),
                    "healthy_count": len(state.get("healthy_slas", [])),
                    "escalations": len(state.get("escalations", []))
                })
            })

        return {
            **state,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(SLAAgentState)

    # Add nodes
    graph.add_node("load_slas", load_slas)
    graph.add_node("check_compliance", check_compliance)
    graph.add_node("predict_risks", predict_risks)
    graph.add_node("analyze_breaches", analyze_breaches)
    graph.add_node("generate_report", generate_report)
    graph.add_node("persist", persist_results)

    # Set entry point
    graph.set_entry_point("load_slas")

    # Add edges
    graph.add_edge("load_slas", "check_compliance")
    graph.add_edge("check_compliance", "predict_risks")

    # Conditional routing based on breaches
    graph.add_conditional_edges(
        "predict_risks",
        route_by_status,
        {
            "analyze_breaches": "analyze_breaches",
            "generate_report": "generate_report"
        }
    )

    graph.add_edge("analyze_breaches", "generate_report")
    graph.add_edge("generate_report", "persist")
    graph.add_edge("persist", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=get_checkpointer())


# Convenience function to run the agent
def run_sla_monitoring(product_ids: Optional[List[str]] = None, thread_id: Optional[str] = None) -> dict:
    """Run SLA monitoring for specified products or all products."""
    agent = build_sla_agent()

    if thread_id is None:
        thread_id = f"sla_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state: SLAAgentState = {
        "product_ids": product_ids,
        "slas": [],
        "current_metrics": {},
        "breached_slas": [],
        "at_risk_slas": [],
        "healthy_slas": [],
        "breach_analysis": None,
        "risk_predictions": None,
        "recommendations": None,
        "trend_analysis": None,
        "notifications": [],
        "escalations": [],
        "status": "initialized",
        "messages": []
    }

    result = agent.invoke(initial_state, config)

    return {
        "status": result.get("status"),
        "summary": {
            "total_slas": len(result.get("slas", [])),
            "breached": len(result.get("breached_slas", [])),
            "at_risk": len(result.get("at_risk_slas", [])),
            "healthy": len(result.get("healthy_slas", []))
        },
        "breached_slas": result.get("breached_slas", []),
        "at_risk_slas": result.get("at_risk_slas", []),
        "breach_analysis": result.get("breach_analysis"),
        "risk_predictions": result.get("risk_predictions"),
        "recommendations": result.get("recommendations"),
        "trend_analysis": result.get("trend_analysis"),
        "notifications": result.get("notifications", []),
        "escalations": result.get("escalations", [])
    }
