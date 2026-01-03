"""
Predictive Prevention Agent
Forecasts and prevents incidents before they occur.
Uses LLM for anomaly analysis and prevention recommendations.
"""
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta, UTC

from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available
from src.graph.manager import Neo4jManager


class PredictiveAgentState(TypedDict):
    """State for the predictive prevention agent."""
    # Input
    product_id: Optional[str]
    domain_id: Optional[str]
    lookback_days: int

    # Analysis
    products_analyzed: List[Dict[str, Any]]
    historical_incidents: List[Dict[str, Any]]
    metrics_trends: Dict[str, Any]

    # Predictions
    risk_predictions: List[Dict[str, Any]]
    anomalies_detected: List[Dict[str, Any]]

    # Recommendations
    preventive_actions: List[Dict[str, Any]]
    monitoring_recommendations: List[str]

    status: str


PREDICTION_PROMPT = """Analyze this data product's health trends and predict potential issues.

Product: {product_name}
Domain: {domain}
Recent Incident Count: {incident_count}
Quality Score Trend: {quality_trend}

Historical Incidents (last {lookback_days} days):
{incident_history}

Based on this information:
1. What is the likelihood of an incident in the next 24 hours? (high/medium/low)
2. What type of incident is most likely?
3. What are the warning signs?
4. What preventive action would you recommend?

Format:
RISK_LEVEL: high/medium/low
INCIDENT_TYPE: <predicted type>
WARNING_SIGNS: <comma-separated list>
PREVENTION: <recommended action>
CONFIDENCE: <0-100>
"""

ANOMALY_PROMPT = """Analyze these metrics for anomalies:

Product: {product_name}
Metrics:
{metrics_text}

Recent Changes:
{changes_text}

Identify any anomalies that could indicate impending issues.
Format each as: ANOMALY: <description> | SEVERITY: high/medium/low | ACTION: <recommendation>
"""


def build_predictive_agent():
    """Build the predictive prevention agent."""
    log = get_agent_logger("PredictiveAgent")

    def gather_data(state: PredictiveAgentState) -> PredictiveAgentState:
        """Gather historical data for analysis."""
        log.info("Gathering data for predictive analysis")

        lookback_days = state.get("lookback_days", 7)
        products_analyzed = []
        historical_incidents = []
        metrics_trends = {}

        try:
            with Neo4jManager() as mgr:
                # Build query based on scope
                if state.get("product_id"):
                    products_query = """
                        MATCH (p:DataProduct {id: $id})
                        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
                        RETURN p {.*, domain: d.name} as product
                    """
                    params = {"id": state["product_id"]}
                elif state.get("domain_id"):
                    products_query = """
                        MATCH (p:DataProduct)-[:IN_DOMAIN]->(d:Domain {id: $id})
                        RETURN p {.*, domain: d.name} as product
                    """
                    params = {"id": state["domain_id"]}
                else:
                    products_query = """
                        MATCH (p:DataProduct)
                        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
                        RETURN p {.*, domain: d.name} as product
                        LIMIT 50
                    """
                    params = {}

                result = mgr.execute_query(products_query, params)
                products_analyzed = [r["product"] for r in result]

                # Get historical incidents
                product_ids = [p.get("id") for p in products_analyzed if p.get("id")]
                if product_ids:
                    incidents_result = mgr.execute_query("""
                        MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
                        WHERE p.id IN $ids
                        RETURN i {.*, product_id: p.id, product_name: p.name} as incident
                        ORDER BY i.created_at DESC
                        LIMIT 100
                    """, {"ids": product_ids})
                    historical_incidents = [r["incident"] for r in incidents_result]

                # Get metrics (simplified)
                metrics_trends = {
                    "products_count": len(products_analyzed),
                    "incidents_last_week": len(historical_incidents),
                    "avg_incidents_per_product": (
                        len(historical_incidents) / len(products_analyzed)
                        if products_analyzed else 0
                    )
                }

        except Exception as e:
            log.error(f"Failed to gather data: {e}")

        return {
            **state,
            "products_analyzed": products_analyzed,
            "historical_incidents": historical_incidents,
            "metrics_trends": metrics_trends,
            "status": "data_gathered"
        }

    def analyze_trends(state: PredictiveAgentState) -> PredictiveAgentState:
        """Analyze trends and detect anomalies."""
        log.info("Analyzing trends and detecting anomalies")

        products = state.get("products_analyzed", [])
        incidents = state.get("historical_incidents", [])
        anomalies = []

        # Group incidents by product
        incidents_by_product = {}
        for inc in incidents:
            pid = inc.get("product_id")
            if pid:
                if pid not in incidents_by_product:
                    incidents_by_product[pid] = []
                incidents_by_product[pid].append(inc)

        # Detect anomalies
        for product in products:
            pid = product.get("id")
            product_incidents = incidents_by_product.get(pid, [])

            # Anomaly: High incident frequency
            if len(product_incidents) >= 3:
                anomalies.append({
                    "product_id": pid,
                    "product_name": product.get("name", pid),
                    "type": "high_incident_frequency",
                    "severity": "high" if len(product_incidents) >= 5 else "medium",
                    "details": f"{len(product_incidents)} incidents in analysis period"
                })

            # Anomaly: Critical incidents
            critical_count = sum(
                1 for i in product_incidents
                if i.get("severity") == "critical"
            )
            if critical_count >= 1:
                anomalies.append({
                    "product_id": pid,
                    "product_name": product.get("name", pid),
                    "type": "critical_incidents",
                    "severity": "high",
                    "details": f"{critical_count} critical incidents"
                })

        log.info(f"Detected {len(anomalies)} anomalies")

        return {
            **state,
            "anomalies_detected": anomalies,
            "status": "trends_analyzed"
        }

    def predict_risks(state: PredictiveAgentState) -> PredictiveAgentState:
        """Generate risk predictions using LLM."""
        log.info("Generating risk predictions with LLM")

        products = state.get("products_analyzed", [])
        incidents = state.get("historical_incidents", [])
        predictions = []

        llm = get_llm_if_available()

        # Group incidents by product for analysis
        incidents_by_product = {}
        for inc in incidents:
            pid = inc.get("product_id")
            if pid:
                if pid not in incidents_by_product:
                    incidents_by_product[pid] = []
                incidents_by_product[pid].append(inc)

        for product in products[:10]:  # Limit to 10 products for performance
            pid = product.get("id")
            product_incidents = incidents_by_product.get(pid, [])

            if llm:
                try:
                    incident_history = "\n".join(
                        f"- {inc.get('type', 'Unknown')}: {inc.get('severity')} - {inc.get('description', 'N/A')[:50]}"
                        for inc in product_incidents[:5]
                    ) or "No recent incidents"

                    prompt = PREDICTION_PROMPT.format(
                        product_name=product.get("name", pid),
                        domain=product.get("domain", "Unknown"),
                        incident_count=len(product_incidents),
                        quality_trend="declining" if len(product_incidents) > 2 else "stable",
                        lookback_days=state.get("lookback_days", 7),
                        incident_history=incident_history
                    )

                    response = llm.invoke(prompt)
                    prediction = _parse_prediction(response.content, product)
                    predictions.append(prediction)

                except Exception as e:
                    log.warning(f"LLM prediction failed for {pid}: {e}")
                    predictions.append(_fallback_prediction(product, product_incidents))
            else:
                predictions.append(_fallback_prediction(product, product_incidents))

        # Sort by risk level
        risk_order = {"high": 0, "medium": 1, "low": 2}
        predictions.sort(key=lambda x: risk_order.get(x.get("risk_level", "low"), 2))

        return {
            **state,
            "risk_predictions": predictions,
            "status": "risks_predicted"
        }

    def generate_recommendations(state: PredictiveAgentState) -> PredictiveAgentState:
        """Generate preventive action recommendations."""
        log.info("Generating preventive action recommendations")

        predictions = state.get("risk_predictions", [])
        anomalies = state.get("anomalies_detected", [])

        preventive_actions = []
        monitoring_recommendations = []

        # High-risk products need immediate attention
        high_risk = [p for p in predictions if p.get("risk_level") == "high"]
        for pred in high_risk:
            preventive_actions.append({
                "product_id": pred.get("product_id"),
                "product_name": pred.get("product_name"),
                "urgency": "immediate",
                "action": pred.get("prevention", "Review and strengthen monitoring"),
                "predicted_issue": pred.get("incident_type", "Unknown")
            })

        # Medium-risk products need monitoring
        medium_risk = [p for p in predictions if p.get("risk_level") == "medium"]
        for pred in medium_risk:
            preventive_actions.append({
                "product_id": pred.get("product_id"),
                "product_name": pred.get("product_name"),
                "urgency": "soon",
                "action": pred.get("prevention", "Increase monitoring frequency"),
                "predicted_issue": pred.get("incident_type", "Unknown")
            })

        # General monitoring recommendations
        if high_risk:
            monitoring_recommendations.append(
                f"Set up alerting for {len(high_risk)} high-risk products"
            )

        if anomalies:
            monitoring_recommendations.append(
                f"Investigate {len(anomalies)} detected anomalies"
            )

        monitoring_recommendations.extend([
            "Review contract rules for products with recurring incidents",
            "Consider implementing automated quality checks",
            "Schedule preventive maintenance for aging data pipelines"
        ])

        return {
            **state,
            "preventive_actions": preventive_actions,
            "monitoring_recommendations": monitoring_recommendations,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(PredictiveAgentState)

    graph.add_node("gather", gather_data)
    graph.add_node("analyze", analyze_trends)
    graph.add_node("predict", predict_risks)
    graph.add_node("recommend", generate_recommendations)

    graph.set_entry_point("gather")
    graph.add_edge("gather", "analyze")
    graph.add_edge("analyze", "predict")
    graph.add_edge("predict", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile(checkpointer=get_checkpointer())


def _parse_prediction(content: str, product: Dict) -> Dict[str, Any]:
    """Parse LLM prediction response."""
    prediction = {
        "product_id": product.get("id"),
        "product_name": product.get("name", product.get("id")),
        "risk_level": "low",
        "incident_type": "unknown",
        "warning_signs": [],
        "prevention": "Monitor regularly",
        "confidence": 50
    }

    for line in content.split("\n"):
        line_upper = line.upper()
        if "RISK_LEVEL:" in line_upper:
            level = line.split(":")[-1].strip().lower()
            if level in ["high", "medium", "low"]:
                prediction["risk_level"] = level
        elif "INCIDENT_TYPE:" in line_upper:
            prediction["incident_type"] = line.split(":")[-1].strip()
        elif "WARNING_SIGNS:" in line_upper:
            signs = line.split(":")[-1].strip()
            prediction["warning_signs"] = [s.strip() for s in signs.split(",")]
        elif "PREVENTION:" in line_upper:
            prediction["prevention"] = line.split(":")[-1].strip()
        elif "CONFIDENCE:" in line_upper:
            try:
                prediction["confidence"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    return prediction


def _fallback_prediction(product: Dict, incidents: List[Dict]) -> Dict[str, Any]:
    """Fallback prediction based on incident history."""
    incident_count = len(incidents)

    if incident_count >= 5:
        risk_level = "high"
        prevention = "Immediate review of data quality rules and upstream sources"
    elif incident_count >= 2:
        risk_level = "medium"
        prevention = "Increase monitoring and review recent changes"
    else:
        risk_level = "low"
        prevention = "Continue regular monitoring"

    return {
        "product_id": product.get("id"),
        "product_name": product.get("name", product.get("id")),
        "risk_level": risk_level,
        "incident_type": "data_quality_issue",
        "warning_signs": [f"{incident_count} recent incidents"],
        "prevention": prevention,
        "confidence": 60
    }
