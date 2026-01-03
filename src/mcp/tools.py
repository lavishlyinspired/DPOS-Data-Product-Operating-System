"""
MCP Tools for DPOS
Defines all tools available via MCP for Claude and other clients.
Includes all agents, knowledge extraction, and governance tools.
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

from src.graph.manager import Neo4jManager


# ============================================================================
# TOOL INPUT SCHEMAS
# ============================================================================

class SearchProductsInput(BaseModel):
    """Input for searching data products."""
    query: str = Field(description="Search query for finding data products")
    limit: int = Field(default=10, description="Maximum number of results")


class GetProductInput(BaseModel):
    """Input for getting a specific product."""
    product_id: str = Field(description="Product ID (e.g., DP001)")


class GetLineageInput(BaseModel):
    """Input for getting product lineage."""
    product_id: str = Field(description="Product ID to trace lineage for")
    direction: str = Field(default="both", description="Direction: upstream, downstream, or both")
    depth: int = Field(default=3, description="Maximum depth to traverse")


class HandleIncidentInput(BaseModel):
    """Input for handling an incident."""
    incident_id: str = Field(description="Incident ID to handle")
    severity: str = Field(default="medium", description="Incident severity: low, medium, high, critical")


class AnalyzeImpactInput(BaseModel):
    """Input for impact analysis."""
    product_id: str = Field(description="Product ID to analyze impact for")


class AskQuestionInput(BaseModel):
    """Input for asking a question."""
    question: str = Field(description="Natural language question about data products")


class ExecuteCypherInput(BaseModel):
    """Input for executing Cypher queries."""
    query: str = Field(description="Cypher query to execute (read-only)")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")


class ExtractKnowledgeInput(BaseModel):
    """Input for knowledge extraction."""
    text: str = Field(description="Text to extract knowledge from")
    source: str = Field(default="api", description="Source identifier")


class SLAMonitorInput(BaseModel):
    """Input for SLA monitoring."""
    product_ids: Optional[List[str]] = Field(default=None, description="Product IDs to monitor (None for all)")


class InsightsInput(BaseModel):
    """Input for insights generation."""
    time_range_days: int = Field(default=30, description="Time range in days for analysis")


class CrossDomainInput(BaseModel):
    """Input for cross-domain analysis."""
    event_type: str = Field(description="Type of event: incident, change, deprecation")
    product_id: str = Field(description="Product ID to analyze")
    severity: str = Field(default="medium", description="Severity level")
    description: str = Field(default="", description="Event description")


class NotificationInput(BaseModel):
    """Input for notification generation."""
    event_type: str = Field(description="Type of event")
    severity: str = Field(description="Severity level")
    product_id: str = Field(description="Affected product ID")
    description: str = Field(description="Event description")


class ContractEvolutionInput(BaseModel):
    """Input for contract evolution analysis."""
    contract_id: str = Field(description="Contract ID to analyze")


class PredictiveInput(BaseModel):
    """Input for predictive analysis."""
    product_ids: List[str] = Field(description="Product IDs to analyze")


class OrchestratorInput(BaseModel):
    """Input for orchestrator agent."""
    incident_ids: List[str] = Field(description="Incident IDs to orchestrate")


# ============================================================================
# HELPER FUNCTIONS - Lazy imports to avoid circular dependencies
# ============================================================================

def _get_agent_runner():
    """Lazily import agent runner."""
    from src.agents.agent_runner import (
        handle_incident,
        handle_incident_steward,
        analyze_impact,
        ask_question,
        discover_products
    )
    return {
        "handle_incident": handle_incident,
        "handle_incident_steward": handle_incident_steward,
        "analyze_impact": analyze_impact,
        "ask_question": ask_question,
        "discover_products": discover_products
    }


def _run_sla_agent(product_ids: Optional[List[str]] = None) -> Dict:
    """Run SLA monitoring agent."""
    try:
        from src.agents.sla_agent import run_sla_monitoring
        return run_sla_monitoring(product_ids)
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_insights_agent(time_range_days: int = 30) -> Dict:
    """Run insights agent."""
    try:
        from src.agents.insights_agent import run_insights_analysis
        return run_insights_analysis(time_range_days)
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_cross_domain_agent(event_type: str, product_id: str, severity: str, description: str) -> Dict:
    """Run cross-domain impact agent."""
    try:
        from src.agents.cross_domain_agent import build_cross_domain_agent
        agent = build_cross_domain_agent()
        result = agent.invoke({
            "event_type": event_type,
            "affected_product_id": product_id,
            "severity": severity,
            "description": description,
            "messages": []
        })
        return {
            "status": result.get("status"),
            "affected_domains": result.get("affected_domains"),
            "cross_domain_impacts": result.get("cross_domain_impacts"),
            "coordination_plan": result.get("coordination_plan"),
            "executive_summary": result.get("executive_summary")
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_notification_agent(event_type: str, severity: str, product_id: str, description: str) -> Dict:
    """Run notification agent."""
    try:
        from src.agents.notification_agent import build_notification_agent
        agent = build_notification_agent()
        result = agent.invoke({
            "event_type": event_type,
            "severity": severity,
            "affected_product_id": product_id,
            "summary": description,
            "details": description,
            "messages": []
        })
        return {
            "status": result.get("status"),
            "notifications": result.get("notifications", []),
            "escalations": result.get("escalation_actions", [])
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_contract_evolution_agent(contract_id: str) -> Dict:
    """Run contract evolution agent."""
    try:
        from src.agents.contract_evolution_agent import build_contract_evolution_agent
        agent = build_contract_evolution_agent()
        result = agent.invoke({
            "contract_id": contract_id,
            "messages": []
        })
        return {
            "status": result.get("status"),
            "violation_analysis": result.get("violation_analysis"),
            "threshold_recommendations": result.get("threshold_recommendations"),
            "new_rule_suggestions": result.get("new_rule_suggestions"),
            "evolution_plan": result.get("evolution_plan")
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_predictive_agent(product_ids: List[str]) -> Dict:
    """Run predictive agent."""
    try:
        from src.agents.predictive_agent import build_predictive_agent
        agent = build_predictive_agent()
        result = agent.invoke({
            "product_ids": product_ids,
            "messages": []
        })
        return {
            "status": result.get("status"),
            "predictions": result.get("predictions"),
            "risk_factors": result.get("risk_factors"),
            "preventive_actions": result.get("preventive_actions")
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def _run_orchestrator_agent(incident_ids: List[str]) -> Dict:
    """Run orchestrator agent."""
    try:
        from src.agents.orchestrator_agent import build_orchestrator_agent
        agent = build_orchestrator_agent()
        result = agent.invoke({
            "incident_ids": incident_ids,
            "messages": []
        })
        return {
            "status": result.get("status"),
            "incident_analysis": result.get("incident_analysis"),
            "prioritized_incidents": result.get("prioritized_incidents"),
            "batch_actions": result.get("batch_actions"),
            "orchestration_summary": result.get("orchestration_summary")
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


# ============================================================================
# CORE DATA PRODUCT TOOLS
# ============================================================================

@tool
def dpos_search_products(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for data products in the DPOS catalog.
    Returns matching products with their metadata.

    Args:
        query: Search term to find products
        limit: Maximum results to return

    Returns:
        List of matching data products
    """
    with Neo4jManager() as mgr:
        cypher = """
        MATCH (p:DataProduct)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        RETURN p.id as id, p.name as name, p.description as description,
               p.status as status, p.type as type, p.owner as owner,
               d.name as domain
        LIMIT $limit
        """
        results = mgr.execute_query(cypher, {"query": query, "limit": limit})
        return [dict(r) for r in results]


@tool
def dpos_get_product(product_id: str) -> Dict:
    """
    Get detailed information about a specific data product.

    Args:
        product_id: The product ID (e.g., DP001)

    Returns:
        Product details including health, contracts, and incidents
    """
    with Neo4jManager() as mgr:
        cypher = """
        MATCH (p:DataProduct {id: $id})
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        OPTIONAL MATCH (p)-[:HAS_CONTRACT]->(c:Contract)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        RETURN p.id as id, p.name as name, p.description as description,
               p.status as status, p.type as type, p.owner as owner,
               d.name as domain,
               count(DISTINCT c) as contract_count,
               count(DISTINCT i) as open_incidents
        """
        results = mgr.execute_query(cypher, {"id": product_id})
        if results:
            result = dict(results[0])
            result["health"] = "healthy" if result.get("open_incidents", 0) == 0 else "degraded"
            return result
        return {"error": f"Product {product_id} not found"}


@tool
def dpos_get_lineage(product_id: str, direction: str = "both", depth: int = 3) -> Dict:
    """
    Get data lineage for a product - upstream sources and downstream consumers.

    Args:
        product_id: Product ID to trace lineage for
        direction: "upstream", "downstream", or "both"
        depth: Maximum traversal depth

    Returns:
        Lineage information with upstream and downstream products
    """
    with Neo4jManager() as mgr:
        result = {"product_id": product_id, "upstream": [], "downstream": []}

        if direction in ["upstream", "both"]:
            cypher = f"""
            MATCH path = (p:DataProduct {{id: $id}})-[:CONSUMES_FROM*1..{depth}]->(source)
            RETURN DISTINCT source.id as id, source.name as name, length(path) as distance
            ORDER BY distance
            """
            upstream = mgr.execute_query(cypher, {"id": product_id})
            result["upstream"] = [dict(r) for r in upstream]

        if direction in ["downstream", "both"]:
            cypher = f"""
            MATCH path = (consumer)-[:CONSUMES_FROM*1..{depth}]->(p:DataProduct {{id: $id}})
            RETURN DISTINCT consumer.id as id, consumer.name as name, length(path) as distance
            ORDER BY distance
            """
            downstream = mgr.execute_query(cypher, {"id": product_id})
            result["downstream"] = [dict(r) for r in downstream]

        return result


@tool
def dpos_list_incidents(status: str = "open", severity: str = None) -> List[Dict]:
    """
    List incidents in the DPOS system.

    Args:
        status: Filter by status (open, investigating, resolved, all)
        severity: Filter by severity (low, medium, high, critical)

    Returns:
        List of incidents matching the criteria
    """
    with Neo4jManager() as mgr:
        conditions = []
        params = {}

        if status != "all":
            conditions.append("i.status = $status")
            params["status"] = status

        if severity:
            conditions.append("i.severity = $severity")
            params["severity"] = severity

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        cypher = f"""
        MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
        {where_clause}
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               p.name as product_name, p.id as product_id
        ORDER BY
          CASE i.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
          i.created_at DESC
        LIMIT 50
        """
        results = mgr.execute_query(cypher, params)
        return [dict(r) for r in results]


@tool
def dpos_get_dashboard_stats() -> Dict:
    """
    Get dashboard statistics for DPOS overview.

    Returns:
        Summary statistics including products, incidents, and health
    """
    with Neo4jManager() as mgr:
        stats = {}

        # Product count
        result = mgr.execute_query("MATCH (p:DataProduct) RETURN count(p) as count")
        stats["total_products"] = result[0]["count"] if result else 0

        # Active contracts
        result = mgr.execute_query(
            "MATCH (c:Contract {is_active: true}) RETURN count(c) as count"
        )
        stats["active_contracts"] = result[0]["count"] if result else 0

        # Open incidents
        result = mgr.execute_query(
            "MATCH (i:Incident {status: 'open'}) RETURN count(i) as count"
        )
        stats["open_incidents"] = result[0]["count"] if result else 0

        # Health by domain
        result = mgr.execute_query("""
            MATCH (d:Domain)<-[:IN_DOMAIN]-(p:DataProduct)
            OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
            WITH d, count(DISTINCT p) as products, count(i) as incidents
            RETURN d.name as domain, products, incidents
            ORDER BY incidents DESC
        """)
        stats["domains"] = [dict(r) for r in result]

        return stats


@tool
def dpos_execute_cypher(query: str, parameters: Dict = None) -> Dict:
    """
    Execute a read-only Cypher query against the DPOS knowledge graph.
    Only SELECT/MATCH queries are allowed - no mutations.

    Args:
        query: Cypher query (read-only)
        parameters: Optional query parameters

    Returns:
        Query results
    """
    # Safety check
    query_upper = query.upper()
    forbidden = ['DELETE', 'REMOVE', 'SET ', 'CREATE', 'MERGE', 'DROP']
    for word in forbidden:
        if word in query_upper:
            return {"error": f"Mutation operations ({word}) are not allowed"}

    with Neo4jManager() as mgr:
        try:
            results = mgr.execute_query(query, parameters or {})
            return {
                "results": [dict(r) for r in results[:100]],
                "count": len(results)
            }
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# AI AGENT TOOLS
# ============================================================================

@tool
def dpos_handle_incident(incident_id: str, severity: str = "medium") -> Dict:
    """
    Handle an incident using the AI Healing Agent.
    The agent will analyze the incident and take appropriate action.

    Args:
        incident_id: Incident ID to handle
        severity: Incident severity level

    Returns:
        Agent execution result with action taken
    """
    runner = _get_agent_runner()
    result = runner["handle_incident"](incident_id, severity)
    return {
        "incident_id": incident_id,
        "action": result.get("action", "unknown"),
        "recommendation": result.get("recommendation", ""),
        "root_cause": result.get("root_cause", ""),
        "status": result.get("status", ""),
        "requires_approval": result.get("requires_approval", False)
    }


@tool
def dpos_steward_review(incident_id: str, severity: str = "medium") -> Dict:
    """
    Run steward review for an incident using the Data Steward Agent.
    Provides governance recommendations and preventive measures.

    Args:
        incident_id: Incident ID to review
        severity: Incident severity level

    Returns:
        Steward recommendations and governance insights
    """
    runner = _get_agent_runner()
    result = runner["handle_incident_steward"](incident_id, severity)
    return {
        "incident_id": incident_id,
        "governance_recommendations": result.get("governance_recommendations", []),
        "preventive_measures": result.get("preventive_measures", []),
        "policy_updates": result.get("policy_updates", []),
        "status": result.get("status", "")
    }


@tool
def dpos_analyze_impact(product_id: str) -> Dict:
    """
    Analyze the downstream impact of a data product failure.
    Uses the Impact Agent to trace dependencies.

    Args:
        product_id: Product ID to analyze

    Returns:
        Impact analysis with risk score and affected systems
    """
    runner = _get_agent_runner()
    result = runner["analyze_impact"](product_id)
    return {
        "product_id": product_id,
        "risk_score": result.get("risk_score", 0),
        "business_impact": result.get("business_impact", "unknown"),
        "downstream_products": len(result.get("downstream_products", [])),
        "affected_pipelines": len(result.get("affected_pipelines", [])),
        "affected_users": result.get("affected_users", 0),
        "mitigation_suggestions": result.get("mitigation_suggestions", [])
    }


@tool
def dpos_ask_question(question: str) -> Dict:
    """
    Ask a natural language question about data products.
    Uses the QA Agent to search and answer.

    Args:
        question: Natural language question

    Returns:
        Answer with sources
    """
    runner = _get_agent_runner()
    result = runner["ask_question"](question)
    return {
        "question": question,
        "answer": result.get("answer", "No answer found"),
        "sources": result.get("sources", [])
    }


@tool
def dpos_discover_products(query: str) -> Dict:
    """
    Discover data products matching a query.
    Uses the Discovery Agent with recommendations.

    Args:
        query: Discovery query

    Returns:
        Discovered products and recommendations
    """
    runner = _get_agent_runner()
    result = runner["discover_products"](query)
    return {
        "query": query,
        "products_found": len(result.get("discovered_products", [])),
        "products": result.get("discovered_products", []),
        "recommendations": result.get("recommendations", [])
    }


@tool
def dpos_monitor_slas(product_ids: List[str] = None) -> Dict:
    """
    Monitor SLA compliance and detect breaches.
    Uses the SLA Agent to check all configured SLAs.

    Args:
        product_ids: Optional list of product IDs to monitor (None for all)

    Returns:
        SLA compliance report with breaches and at-risk SLAs
    """
    return _run_sla_agent(product_ids)


@tool
def dpos_generate_insights(time_range_days: int = 30) -> Dict:
    """
    Generate governance insights and recommendations.
    Uses the Insights Agent for automated analysis.

    Args:
        time_range_days: Time range in days for analysis

    Returns:
        Executive summary, key findings, and recommendations
    """
    return _run_insights_agent(time_range_days)


@tool
def dpos_cross_domain_impact(
    event_type: str,
    product_id: str,
    severity: str = "medium",
    description: str = ""
) -> Dict:
    """
    Analyze cross-domain impact of an event.
    Traces impacts across organizational boundaries.

    Args:
        event_type: Type of event (incident, change, deprecation)
        product_id: Affected product ID
        severity: Severity level
        description: Event description

    Returns:
        Cross-domain impact analysis and coordination plan
    """
    return _run_cross_domain_agent(event_type, product_id, severity, description)


@tool
def dpos_generate_notifications(
    event_type: str,
    severity: str,
    product_id: str,
    description: str
) -> Dict:
    """
    Generate stakeholder notifications for an event.
    Creates tailored messages for different audiences.

    Args:
        event_type: Type of event
        severity: Severity level
        product_id: Affected product ID
        description: Event description

    Returns:
        Generated notifications and escalation actions
    """
    return _run_notification_agent(event_type, severity, product_id, description)


@tool
def dpos_analyze_contract_evolution(contract_id: str) -> Dict:
    """
    Analyze contract evolution opportunities.
    Reviews violations and suggests improvements.

    Args:
        contract_id: Contract ID to analyze

    Returns:
        Threshold recommendations and new rule suggestions
    """
    return _run_contract_evolution_agent(contract_id)


@tool
def dpos_predict_issues(product_ids: List[str]) -> Dict:
    """
    Predict potential issues for products.
    Uses historical patterns for proactive detection.

    Args:
        product_ids: Product IDs to analyze

    Returns:
        Predictions and preventive actions
    """
    return _run_predictive_agent(product_ids)


@tool
def dpos_orchestrate_incidents(incident_ids: List[str]) -> Dict:
    """
    Orchestrate multiple incidents together.
    Correlates and prioritizes for efficient resolution.

    Args:
        incident_ids: Incident IDs to orchestrate

    Returns:
        Prioritized incidents and batch actions
    """
    return _run_orchestrator_agent(incident_ids)


# ============================================================================
# KNOWLEDGE EXTRACTION TOOLS
# ============================================================================

@tool
def dpos_extract_knowledge(text: str, source: str = "api") -> Dict:
    """
    Extract knowledge entities from unstructured text.
    Identifies data products, rules, and relationships.

    Args:
        text: Text to extract knowledge from
        source: Source identifier

    Returns:
        Extracted entities and relationships
    """
    try:
        from src.knowledge.ontology_extractor import OntologyExtractor
        extractor = OntologyExtractor()
        result = extractor.extract(text, source)
        return {
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "confidence": result.get("confidence", 0)
        }
    except Exception as e:
        return {"error": str(e), "entities": [], "relationships": []}


@tool
def dpos_list_slas() -> List[Dict]:
    """
    List all SLAs in the system.

    Returns:
        List of SLAs with their targets and compliance status
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (s:SLA)
        OPTIONAL MATCH (c:Contract)-[:HAS_SLA]->(s)
        OPTIONAL MATCH (c)<-[:HAS_CONTRACT]-(p:DataProduct)
        RETURN s.id as id, s.name as name, s.description as description,
               s.target_value as target_value, s.metric_type as metric_type,
               s.threshold as threshold, s.is_active as is_active,
               c.id as contract_id, p.id as product_id, p.name as product_name
        ORDER BY s.name
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@tool
def dpos_list_contracts() -> List[Dict]:
    """
    List all data contracts in the system.

    Returns:
        List of contracts with their rules and products
    """
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
        ORDER BY c.name
        """
        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@tool
def dpos_get_contract_rules(contract_id: str) -> Dict:
    """
    Get all rules for a specific contract.

    Args:
        contract_id: Contract ID

    Returns:
        Contract details with all rules
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (c:Contract {id: $id})
        OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
        RETURN c.id as id, c.name as name, c.is_active as is_active,
               collect({
                   id: r.id, type: r.type, field: r.field,
                   threshold: r.threshold, severity: r.severity,
                   enabled: r.enabled
               }) as rules
        """
        results = mgr.execute_query(query, {"id": contract_id})
        if results:
            return dict(results[0])
        return {"error": f"Contract {contract_id} not found"}


# ============================================================================
# TOOL REGISTRY
# ============================================================================

def get_all_tools() -> List:
    """Get all DPOS tools for MCP registration."""
    return [
        # Core data product tools
        dpos_search_products,
        dpos_get_product,
        dpos_get_lineage,
        dpos_list_incidents,
        dpos_get_dashboard_stats,
        dpos_execute_cypher,
        # AI agent tools
        dpos_handle_incident,
        dpos_steward_review,
        dpos_analyze_impact,
        dpos_ask_question,
        dpos_discover_products,
        dpos_monitor_slas,
        dpos_generate_insights,
        dpos_cross_domain_impact,
        dpos_generate_notifications,
        dpos_analyze_contract_evolution,
        dpos_predict_issues,
        dpos_orchestrate_incidents,
        # Knowledge and governance tools
        dpos_extract_knowledge,
        dpos_list_slas,
        dpos_list_contracts,
        dpos_get_contract_rules
    ]


def get_tool_descriptions() -> List[Dict]:
    """Get tool descriptions for documentation."""
    tools = get_all_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "args": str(t.args) if hasattr(t, 'args') else ""
        }
        for t in tools
    ]


def get_tools_by_category() -> Dict[str, List]:
    """Get tools organized by category."""
    return {
        "data_products": [
            dpos_search_products,
            dpos_get_product,
            dpos_get_lineage,
            dpos_list_incidents,
            dpos_get_dashboard_stats
        ],
        "agents": [
            dpos_handle_incident,
            dpos_steward_review,
            dpos_analyze_impact,
            dpos_ask_question,
            dpos_discover_products,
            dpos_monitor_slas,
            dpos_generate_insights,
            dpos_cross_domain_impact,
            dpos_generate_notifications,
            dpos_analyze_contract_evolution,
            dpos_predict_issues,
            dpos_orchestrate_incidents
        ],
        "governance": [
            dpos_list_slas,
            dpos_list_contracts,
            dpos_get_contract_rules,
            dpos_extract_knowledge
        ],
        "advanced": [
            dpos_execute_cypher
        ]
    }
