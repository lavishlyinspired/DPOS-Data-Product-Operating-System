"""
Insights Agent (LLM-Enhanced)
Generates automated governance insights, trends, and recommendations.
Uses LLM for intelligent pattern detection and executive summaries.
"""
from typing import TypedDict, List, Optional, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from operator import add
from datetime import datetime, timedelta

from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available
from src.graph.manager import Neo4jManager


class InsightsAgentState(TypedDict):
    """State for the insights agent."""
    time_range_days: int  # Analysis time range

    # Raw data
    products_data: List[dict]
    incidents_data: List[dict]
    contracts_data: List[dict]
    metrics_data: List[dict]

    # Analysis results
    health_summary: Optional[dict]
    incident_trends: Optional[dict]
    quality_patterns: Optional[List[dict]]
    compliance_insights: Optional[dict]

    # LLM-generated insights
    executive_summary: Optional[str]
    key_findings: Optional[List[str]]
    recommendations: Optional[List[str]]
    risk_areas: Optional[List[dict]]
    improvement_opportunities: Optional[List[str]]

    # Alerts and notifications
    alerts: List[dict]

    status: str
    messages: Annotated[List[BaseMessage], add]


def _fetch_products_data() -> List[dict]:
    """Fetch all products with their health metrics."""
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct)
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        OPTIONAL MATCH (p)-[:HAS_CONTRACT]->(c:Contract)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident)
        WITH p, d,
             count(DISTINCT c) as contract_count,
             count(DISTINCT i) as total_incidents,
             sum(CASE WHEN i.status = 'open' THEN 1 ELSE 0 END) as open_incidents
        RETURN p.id as id, p.name as name, p.type as type, p.status as status,
               d.name as domain, contract_count, total_incidents, open_incidents,
               p.created_at as created_at
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


def _fetch_incidents_data(days: int = 30) -> List[dict]:
    """Fetch incidents within time range."""
    with Neo4jManager() as mgr:
        query = """
        MATCH (i:Incident)
        OPTIONAL MATCH (i)<-[:HAS_INCIDENT]-(p:DataProduct)
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               i.created_at as created_at, i.resolved_at as resolved_at,
               p.id as product_id, p.name as product_name
        ORDER BY i.created_at DESC
        LIMIT 500
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


def _fetch_contracts_data() -> List[dict]:
    """Fetch contracts with validation stats."""
    with Neo4jManager() as mgr:
        query = """
        MATCH (c:Contract)
        OPTIONAL MATCH (c)<-[:HAS_CONTRACT]-(p:DataProduct)
        OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
        WITH c, p, count(r) as rule_count
        RETURN c.id as id, c.name as name, c.is_active as is_active,
               c.enforcement_mode as enforcement_mode,
               p.id as product_id, p.name as product_name,
               rule_count
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


def _fetch_metrics_data() -> List[dict]:
    """Fetch recent metrics snapshots."""
    with Neo4jManager() as mgr:
        query = """
        MATCH (v:ValidationReport)
        OPTIONAL MATCH (v)-[:VALIDATED]->(p:DataProduct)
        RETURN v.id as id, v.result as result, v.action as action,
               v.total_records as total_records, v.violations as violations,
               v.created_at as created_at,
               p.id as product_id, p.name as product_name
        ORDER BY v.created_at DESC
        LIMIT 200
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


def _generate_llm_insights(
    health_summary: dict,
    incident_trends: dict,
    quality_patterns: List[dict],
    compliance_insights: dict
) -> dict:
    """Generate insights using LLM."""
    llm = get_llm_if_available()

    if not llm:
        return {
            "executive_summary": f"Data governance health: {health_summary.get('overall_health', 'Unknown')}. "
                                f"{incident_trends.get('total', 0)} incidents tracked.",
            "key_findings": [
                f"Total products: {health_summary.get('total_products', 0)}",
                f"Active incidents: {incident_trends.get('open', 0)}",
                f"Compliance rate: {compliance_insights.get('compliance_rate', 0):.1f}%"
            ],
            "recommendations": [
                "Review products with multiple open incidents",
                "Update contracts with frequent violations",
                "Consider adding SLAs to unmonitored products"
            ]
        }

    prompt = f"""Analyze this data governance metrics and provide executive insights:

HEALTH SUMMARY:
- Total Products: {health_summary.get('total_products', 0)}
- Healthy Products: {health_summary.get('healthy', 0)}
- Degraded Products: {health_summary.get('degraded', 0)}
- Critical Products: {health_summary.get('critical', 0)}

INCIDENT TRENDS:
- Total Incidents: {incident_trends.get('total', 0)}
- Open: {incident_trends.get('open', 0)}
- By Severity: Critical={incident_trends.get('critical', 0)}, High={incident_trends.get('high', 0)}, Medium={incident_trends.get('medium', 0)}, Low={incident_trends.get('low', 0)}

QUALITY PATTERNS:
{quality_patterns[:5] if quality_patterns else 'No patterns detected'}

COMPLIANCE:
- Compliance Rate: {compliance_insights.get('compliance_rate', 0):.1f}%
- Products with Contracts: {compliance_insights.get('products_with_contracts', 0)}
- Products without Contracts: {compliance_insights.get('products_without_contracts', 0)}

Provide:
1. Executive Summary (2-3 sentences for C-level)
2. Key Findings (3-5 bullet points)
3. Top Recommendations (3-5 actionable items)
4. Risk Areas (identify 2-3 critical areas needing attention)
5. Improvement Opportunities (2-3 strategic suggestions)

Format as JSON with keys: executive_summary, key_findings (array), recommendations (array), risk_areas (array of objects with 'area' and 'reason'), improvement_opportunities (array)"""

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # Try to parse JSON
        import json
        if '{' in content:
            try:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                return json.loads(content[json_start:json_end])
            except:
                pass

        # Fallback parsing
        return {
            "executive_summary": content[:500],
            "key_findings": [
                f"Total products: {health_summary.get('total_products', 0)}",
                f"Active incidents: {incident_trends.get('open', 0)}",
                f"Compliance rate: {compliance_insights.get('compliance_rate', 0):.1f}%"
            ],
            "recommendations": [
                "Review products with multiple open incidents",
                "Update contracts with frequent violations"
            ],
            "risk_areas": [
                {"area": "Open Incidents", "reason": f"{incident_trends.get('open', 0)} incidents need resolution"}
            ],
            "improvement_opportunities": [
                "Consider automated healing for recurring issues"
            ]
        }
    except Exception as e:
        return {
            "executive_summary": f"Analysis completed with {health_summary.get('total_products', 0)} products monitored.",
            "key_findings": [f"Analysis error: {str(e)}"],
            "recommendations": ["Manual review recommended"],
            "risk_areas": [],
            "improvement_opportunities": []
        }


def build_insights_agent():
    """
    Build an insights agent that generates governance intelligence:
    - Analyzes data product health
    - Identifies incident trends
    - Detects quality patterns
    - Generates executive summaries
    - Provides actionable recommendations
    """
    log = get_agent_logger("InsightsAgent")

    def gather_data(state: InsightsAgentState) -> InsightsAgentState:
        """Gather all data for analysis."""
        log.info("Gathering data for insights analysis")

        products = _fetch_products_data()
        incidents = _fetch_incidents_data(state.get("time_range_days", 30))
        contracts = _fetch_contracts_data()
        metrics = _fetch_metrics_data()

        log.info(f"Gathered: {len(products)} products, {len(incidents)} incidents, {len(contracts)} contracts")

        return {
            **state,
            "products_data": products,
            "incidents_data": incidents,
            "contracts_data": contracts,
            "metrics_data": metrics,
            "status": "data_gathered"
        }

    def analyze_health(state: InsightsAgentState) -> InsightsAgentState:
        """Analyze overall data product health."""
        log.info("Analyzing data product health")

        products = state.get("products_data", [])

        total = len(products)
        healthy = 0
        degraded = 0
        critical = 0

        for p in products:
            open_incidents = p.get("open_incidents", 0)
            if open_incidents == 0:
                healthy += 1
            elif open_incidents <= 2:
                degraded += 1
            else:
                critical += 1

        # Calculate domain health
        domain_health = {}
        for p in products:
            domain = p.get("domain", "Unassigned")
            if domain not in domain_health:
                domain_health[domain] = {"total": 0, "healthy": 0}
            domain_health[domain]["total"] += 1
            if p.get("open_incidents", 0) == 0:
                domain_health[domain]["healthy"] += 1

        health_summary = {
            "total_products": total,
            "healthy": healthy,
            "degraded": degraded,
            "critical": critical,
            "overall_health": "good" if critical == 0 and degraded < total * 0.2 else (
                "degraded" if critical < total * 0.1 else "critical"
            ),
            "health_percentage": (healthy / total * 100) if total > 0 else 100,
            "domain_health": domain_health
        }

        return {
            **state,
            "health_summary": health_summary,
            "status": "health_analyzed"
        }

    def analyze_incidents(state: InsightsAgentState) -> InsightsAgentState:
        """Analyze incident trends."""
        log.info("Analyzing incident trends")

        incidents = state.get("incidents_data", [])

        # Count by status
        open_count = sum(1 for i in incidents if i.get("status") == "open")
        resolved_count = sum(1 for i in incidents if i.get("status") in ["resolved", "closed"])
        investigating_count = sum(1 for i in incidents if i.get("status") == "investigating")

        # Count by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for i in incidents:
            sev = i.get("severity", "medium").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1

        # Count by type
        type_counts = {}
        for i in incidents:
            itype = i.get("type", "unknown")
            type_counts[itype] = type_counts.get(itype, 0) + 1

        # Products with most incidents
        product_incidents = {}
        for i in incidents:
            pid = i.get("product_id", "unknown")
            product_incidents[pid] = product_incidents.get(pid, 0) + 1

        top_problem_products = sorted(
            product_incidents.items(), key=lambda x: x[1], reverse=True
        )[:5]

        incident_trends = {
            "total": len(incidents),
            "open": open_count,
            "resolved": resolved_count,
            "investigating": investigating_count,
            "critical": severity_counts["critical"],
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "by_type": type_counts,
            "top_problem_products": [
                {"product_id": p[0], "incident_count": p[1]}
                for p in top_problem_products
            ]
        }

        return {
            **state,
            "incident_trends": incident_trends,
            "status": "incidents_analyzed"
        }

    def analyze_quality(state: InsightsAgentState) -> InsightsAgentState:
        """Analyze quality patterns from validation metrics."""
        log.info("Analyzing quality patterns")

        metrics = state.get("metrics_data", [])

        # Aggregate by product
        product_quality = {}
        for m in metrics:
            pid = m.get("product_id", "unknown")
            if pid not in product_quality:
                product_quality[pid] = {
                    "total_validations": 0,
                    "passed": 0,
                    "failed": 0,
                    "total_records": 0,
                    "violations": 0
                }
            product_quality[pid]["total_validations"] += 1
            if m.get("result") == "passed":
                product_quality[pid]["passed"] += 1
            else:
                product_quality[pid]["failed"] += 1
            product_quality[pid]["total_records"] += m.get("total_records", 0)
            product_quality[pid]["violations"] += m.get("violations", 0)

        # Calculate quality scores
        quality_patterns = []
        for pid, stats in product_quality.items():
            total = stats["total_validations"]
            if total > 0:
                pass_rate = (stats["passed"] / total) * 100
                violation_rate = (
                    (stats["violations"] / stats["total_records"]) * 100
                    if stats["total_records"] > 0 else 0
                )
                quality_patterns.append({
                    "product_id": pid,
                    "total_validations": total,
                    "pass_rate": pass_rate,
                    "violation_rate": violation_rate,
                    "quality_score": max(0, 100 - violation_rate * 10)
                })

        # Sort by quality score (worst first)
        quality_patterns.sort(key=lambda x: x.get("quality_score", 100))

        return {
            **state,
            "quality_patterns": quality_patterns,
            "status": "quality_analyzed"
        }

    def analyze_compliance(state: InsightsAgentState) -> InsightsAgentState:
        """Analyze contract compliance."""
        log.info("Analyzing contract compliance")

        products = state.get("products_data", [])
        contracts = state.get("contracts_data", [])

        products_with_contracts = set(
            c.get("product_id") for c in contracts if c.get("product_id")
        )
        all_product_ids = set(p.get("id") for p in products)

        products_without_contracts = all_product_ids - products_with_contracts

        active_contracts = sum(1 for c in contracts if c.get("is_active", True))
        total_rules = sum(c.get("rule_count", 0) for c in contracts)

        compliance_insights = {
            "total_products": len(products),
            "products_with_contracts": len(products_with_contracts),
            "products_without_contracts": len(products_without_contracts),
            "compliance_rate": (
                len(products_with_contracts) / len(products) * 100
                if products else 100
            ),
            "total_contracts": len(contracts),
            "active_contracts": active_contracts,
            "total_rules": total_rules,
            "unprotected_products": list(products_without_contracts)[:10]
        }

        return {
            **state,
            "compliance_insights": compliance_insights,
            "status": "compliance_analyzed"
        }

    def generate_insights(state: InsightsAgentState) -> InsightsAgentState:
        """Generate LLM-powered insights."""
        log.info("Generating LLM-powered insights")

        llm_insights = _generate_llm_insights(
            state.get("health_summary", {}),
            state.get("incident_trends", {}),
            state.get("quality_patterns", []),
            state.get("compliance_insights", {})
        )

        # Generate alerts for critical issues
        alerts = []

        # Alert for critical incidents
        critical_count = state.get("incident_trends", {}).get("critical", 0)
        if critical_count > 0:
            alerts.append({
                "type": "critical_incidents",
                "severity": "critical",
                "message": f"{critical_count} critical incidents require immediate attention",
                "action": "Review and resolve critical incidents"
            })

        # Alert for low compliance
        compliance_rate = state.get("compliance_insights", {}).get("compliance_rate", 100)
        if compliance_rate < 80:
            alerts.append({
                "type": "low_compliance",
                "severity": "warning",
                "message": f"Contract compliance is at {compliance_rate:.1f}%",
                "action": "Add contracts to unprotected products"
            })

        # Alert for degraded health
        overall_health = state.get("health_summary", {}).get("overall_health", "good")
        if overall_health in ["degraded", "critical"]:
            alerts.append({
                "type": "degraded_health",
                "severity": "warning" if overall_health == "degraded" else "critical",
                "message": f"Overall data product health is {overall_health}",
                "action": "Investigate products with open incidents"
            })

        return {
            **state,
            "executive_summary": llm_insights.get("executive_summary"),
            "key_findings": llm_insights.get("key_findings", []),
            "recommendations": llm_insights.get("recommendations", []),
            "risk_areas": llm_insights.get("risk_areas", []),
            "improvement_opportunities": llm_insights.get("improvement_opportunities", []),
            "alerts": alerts,
            "status": "insights_generated"
        }

    def persist_insights(state: InsightsAgentState) -> InsightsAgentState:
        """Persist insights to the graph."""
        log.info("Persisting insights")

        with Neo4jManager() as mgr:
            mgr.execute_query("""
                CREATE (i:InsightsReport {
                    id: 'insights_' + toString(datetime()),
                    created_at: datetime(),
                    health_status: $health_status,
                    compliance_rate: $compliance_rate,
                    open_incidents: $open_incidents,
                    alert_count: $alert_count,
                    executive_summary: $summary
                })
            """, {
                "health_status": state.get("health_summary", {}).get("overall_health", "unknown"),
                "compliance_rate": state.get("compliance_insights", {}).get("compliance_rate", 0),
                "open_incidents": state.get("incident_trends", {}).get("open", 0),
                "alert_count": len(state.get("alerts", [])),
                "summary": (state.get("executive_summary") or "")[:500]
            })

        return {
            **state,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(InsightsAgentState)

    # Add nodes
    graph.add_node("gather_data", gather_data)
    graph.add_node("analyze_health", analyze_health)
    graph.add_node("analyze_incidents", analyze_incidents)
    graph.add_node("analyze_quality", analyze_quality)
    graph.add_node("analyze_compliance", analyze_compliance)
    graph.add_node("generate_insights", generate_insights)
    graph.add_node("persist", persist_insights)

    # Set entry point
    graph.set_entry_point("gather_data")

    # Add edges (sequential analysis flow)
    graph.add_edge("gather_data", "analyze_health")
    graph.add_edge("analyze_health", "analyze_incidents")
    graph.add_edge("analyze_incidents", "analyze_quality")
    graph.add_edge("analyze_quality", "analyze_compliance")
    graph.add_edge("analyze_compliance", "generate_insights")
    graph.add_edge("generate_insights", "persist")
    graph.add_edge("persist", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=get_checkpointer())


# Convenience function to run the agent
def run_insights_analysis(time_range_days: int = 30) -> dict:
    """Run insights analysis for the specified time range."""
    agent = build_insights_agent()

    initial_state: InsightsAgentState = {
        "time_range_days": time_range_days,
        "products_data": [],
        "incidents_data": [],
        "contracts_data": [],
        "metrics_data": [],
        "health_summary": None,
        "incident_trends": None,
        "quality_patterns": None,
        "compliance_insights": None,
        "executive_summary": None,
        "key_findings": None,
        "recommendations": None,
        "risk_areas": None,
        "improvement_opportunities": None,
        "alerts": [],
        "status": "initialized",
        "messages": []
    }

    result = agent.invoke(initial_state)

    return {
        "status": result.get("status"),
        "health_summary": result.get("health_summary"),
        "incident_trends": result.get("incident_trends"),
        "quality_patterns": result.get("quality_patterns", [])[:10],
        "compliance_insights": result.get("compliance_insights"),
        "executive_summary": result.get("executive_summary"),
        "key_findings": result.get("key_findings"),
        "recommendations": result.get("recommendations"),
        "risk_areas": result.get("risk_areas"),
        "improvement_opportunities": result.get("improvement_opportunities"),
        "alerts": result.get("alerts", [])
    }
