"""
Supervisor Agent (Global Orchestrator)

The Supervisor Agent acts as a conductor that orchestrates all other agents in DPOS.
It interprets user requests, determines which agents to invoke, coordinates their
execution, and synthesizes results into coherent responses.

Key Capabilities:
1. Natural Language Understanding - Interprets user intent from queries
2. Agent Selection - Determines optimal agent(s) for each task
3. Multi-Agent Coordination - Orchestrates parallel or sequential agent execution
4. Result Synthesis - Combines outputs from multiple agents
5. Conversation Memory - Maintains context across interactions
6. Adaptive Planning - Adjusts execution based on intermediate results

Entry Points:
- REST API: POST /api/agents/supervisor
- MCP Tool: dpos_supervisor_query
- Streaming: POST /api/agents/supervisor/stream

Example Workflows:
1. "What's wrong with my data and how do I fix it?"
   -> Insights Agent -> Incident Detection -> Healing Agent -> Summary

2. "Analyze the impact of Customer product failure and notify stakeholders"
   -> Impact Agent -> Cross-Domain Agent -> Notification Agent

3. "Generate a governance report for the executive team"
   -> Insights Agent -> SLA Agent -> Contract Evolution Agent -> Summary
"""

from typing import TypedDict, List, Optional, Annotated, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from operator import add
from datetime import datetime
import json

from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available
from src.graph.manager import Neo4jManager


# =============================================================================
# STATE DEFINITION
# =============================================================================

class SupervisorState(TypedDict):
    """
    State for the Supervisor Agent.

    The supervisor maintains comprehensive state to coordinate all agents:
    - User query and conversation history
    - Agent execution plan and results
    - Synthesized final response
    """
    # Input
    query: str                              # User's natural language query
    conversation_history: List[dict]        # Previous conversation context

    # Planning
    intent: Optional[str]                   # Classified user intent
    intent_confidence: Optional[float]      # Confidence in intent classification
    execution_plan: List[dict]              # Planned agent invocations
    current_step: int                       # Current execution step

    # Agent Results
    agent_results: Dict[str, Any]           # Results from each agent invocation
    intermediate_findings: List[str]        # Key findings during execution

    # Coordination
    requires_human_approval: bool           # Whether human approval is needed
    approval_reason: Optional[str]          # Why approval is needed
    approved: bool                          # Whether user approved

    # Output
    response: Optional[str]                 # Final synthesized response
    recommendations: List[str]              # Actionable recommendations
    follow_up_questions: List[str]          # Suggested follow-up questions

    # Metadata
    execution_log: List[dict]               # Detailed execution log
    total_agents_invoked: int               # Count of agents used
    status: str                             # Current status
    messages: Annotated[List[BaseMessage], add]


# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================

INTENT_CLASSIFICATION_PROMPT = """You are a data governance assistant. Classify the user's intent into one of these categories:

INTENTS:
1. DATA_DISCOVERY - Finding data products, searching catalog
2. INCIDENT_HANDLING - Reporting, investigating, or fixing data issues
3. IMPACT_ANALYSIS - Understanding downstream effects of changes/failures
4. SLA_MONITORING - Checking SLA compliance, breach detection
5. GOVERNANCE_INSIGHTS - Getting reports, trends, recommendations
6. CONTRACT_MANAGEMENT - Viewing, updating, or evolving data contracts
7. LINEAGE_TRACKING - Understanding data flow, upstream/downstream
8. NOTIFICATION - Alerting stakeholders about issues
9. MULTI_TASK - Complex query requiring multiple agents
10. GENERAL_QUERY - General question about data products

User Query: {query}

Respond with JSON:
{{
    "intent": "<INTENT_NAME>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>",
    "suggested_agents": ["<agent1>", "<agent2>"],
    "parameters": {{<extracted parameters>}}
}}
"""

AGENT_CAPABILITIES = {
    "discovery": {
        "name": "Discovery Agent",
        "description": "Searches and discovers data products in the catalog",
        "intents": ["DATA_DISCOVERY", "GENERAL_QUERY"],
        "input_params": ["query"]
    },
    "qa": {
        "name": "Q&A Agent",
        "description": "Answers natural language questions about data products",
        "intents": ["GENERAL_QUERY", "DATA_DISCOVERY"],
        "input_params": ["question"]
    },
    "healing": {
        "name": "Healing Agent",
        "description": "Auto-remediates data quality issues with LLM analysis",
        "intents": ["INCIDENT_HANDLING"],
        "input_params": ["incident_id", "severity"]
    },
    "steward": {
        "name": "Steward Agent",
        "description": "Provides governance recommendations and quality assessments",
        "intents": ["GOVERNANCE_INSIGHTS", "INCIDENT_HANDLING"],
        "input_params": ["incident_id", "severity"]
    },
    "impact": {
        "name": "Impact Agent",
        "description": "Analyzes downstream impact of data product failures",
        "intents": ["IMPACT_ANALYSIS", "INCIDENT_HANDLING"],
        "input_params": ["product_id"]
    },
    "sla": {
        "name": "SLA Agent",
        "description": "Monitors SLA compliance and predicts breaches",
        "intents": ["SLA_MONITORING", "GOVERNANCE_INSIGHTS"],
        "input_params": ["product_ids"]
    },
    "insights": {
        "name": "Insights Agent",
        "description": "Generates governance insights and executive summaries",
        "intents": ["GOVERNANCE_INSIGHTS", "MULTI_TASK"],
        "input_params": ["time_range_days"]
    },
    "predictive": {
        "name": "Predictive Agent",
        "description": "Predicts future data quality issues",
        "intents": ["GOVERNANCE_INSIGHTS", "INCIDENT_HANDLING"],
        "input_params": ["product_ids"]
    },
    "orchestrator": {
        "name": "Orchestrator Agent",
        "description": "Coordinates multiple incident resolutions",
        "intents": ["INCIDENT_HANDLING", "MULTI_TASK"],
        "input_params": ["incident_ids"]
    },
    "cross_domain": {
        "name": "Cross-Domain Agent",
        "description": "Analyzes impact across organizational boundaries",
        "intents": ["IMPACT_ANALYSIS", "MULTI_TASK"],
        "input_params": ["event_type", "product_id", "severity"]
    },
    "notification": {
        "name": "Notification Agent",
        "description": "Generates stakeholder notifications",
        "intents": ["NOTIFICATION", "INCIDENT_HANDLING"],
        "input_params": ["event_type", "severity", "product_id", "summary"]
    },
    "contract_evolution": {
        "name": "Contract Evolution Agent",
        "description": "Suggests contract improvements based on patterns",
        "intents": ["CONTRACT_MANAGEMENT", "GOVERNANCE_INSIGHTS"],
        "input_params": ["contract_id"]
    }
}


# =============================================================================
# AGENT RUNNERS
# =============================================================================

def _run_agent(agent_name: str, params: dict) -> dict:
    """Run a specific agent with given parameters."""
    log = get_agent_logger("Supervisor")

    try:
        if agent_name == "discovery":
            from src.agents.discovery_agent import build_discovery_agent
            agent = build_discovery_agent()
            result = agent.invoke({
                "query": params.get("query", ""),
                "sources_scanned": [],
                "discovered_products": [],
                "recommendations": [],
                "status": "initialized"
            })
            return {
                "success": True,
                "products": result.get("discovered_products", []),
                "recommendations": result.get("recommendations", [])
            }

        elif agent_name == "qa":
            from src.agents.qa_agent import build_qa_agent
            agent = build_qa_agent()
            result = agent.invoke({
                "question": params.get("question", params.get("query", "")),
                "answer": "",
                "context": [],
                "sources": [],
                "messages": []
            })
            return {
                "success": True,
                "answer": result.get("answer", ""),
                "sources": result.get("sources", [])
            }

        elif agent_name == "healing":
            from src.agents.healing_agent import build_healing_agent
            agent = build_healing_agent()
            result = agent.invoke({
                "incident_id": params.get("incident_id", ""),
                "severity": params.get("severity", "medium"),
                "recommendation": "",
                "action": "",
                "status": "",
                "messages": []
            })
            return {
                "success": True,
                "action": result.get("action"),
                "recommendation": result.get("recommendation"),
                "root_cause": result.get("root_cause"),
                "remediation_steps": result.get("remediation_steps", []),
                "requires_approval": result.get("requires_approval", False)
            }

        elif agent_name == "impact":
            from src.agents.impact_agent import build_impact_agent
            agent = build_impact_agent()
            result = agent.invoke({
                "product_id": params.get("product_id", ""),
                "product_name": None,
                "incident_id": None,
                "downstream_products": [],
                "affected_pipelines": [],
                "affected_users": 0,
                "affected_domains": [],
                "business_impact": "",
                "risk_score": 0.0,
                "risk_assessment": None,
                "impact_narrative": None,
                "mitigation_suggestions": None,
                "status": ""
            })
            return {
                "success": True,
                "risk_score": result.get("risk_score", 0),
                "business_impact": result.get("business_impact"),
                "downstream_count": len(result.get("downstream_products", [])),
                "impact_narrative": result.get("impact_narrative"),
                "mitigation_suggestions": result.get("mitigation_suggestions", [])
            }

        elif agent_name == "sla":
            from src.agents.sla_agent import run_sla_monitoring
            result = run_sla_monitoring(params.get("product_ids"))
            return {
                "success": True,
                "summary": result.get("summary", {}),
                "breached_slas": result.get("breached_slas", []),
                "at_risk_slas": result.get("at_risk_slas", []),
                "recommendations": result.get("recommendations", [])
            }

        elif agent_name == "insights":
            from src.agents.insights_agent import run_insights_analysis
            result = run_insights_analysis(params.get("time_range_days", 30))
            return {
                "success": True,
                "executive_summary": result.get("executive_summary"),
                "key_findings": result.get("key_findings", []),
                "recommendations": result.get("recommendations", []),
                "alerts": result.get("alerts", [])
            }

        elif agent_name == "steward":
            from src.agents.steward_agent import build_steward_agent
            agent = build_steward_agent()
            result = agent.invoke({
                "incident_id": params.get("incident_id", ""),
                "severity": params.get("severity", "medium"),
                "product_id": None,
                "product_name": None,
                "analysis": None,
                "quality_score": None,
                "root_cause": None,
                "root_cause_confidence": None,
                "remediation_steps": [],
                "preventive_measures": [],
                "governance_recommendations": [],
                "notifications_sent": [],
                "stakeholder_narrative": None,
                "status": ""
            })
            return {
                "success": True,
                "governance_recommendations": result.get("governance_recommendations", []),
                "preventive_measures": result.get("preventive_measures", []),
                "root_cause": result.get("root_cause")
            }

        elif agent_name == "notification":
            from src.agents.notification_agent import build_notification_agent
            agent = build_notification_agent()
            result = agent.invoke({
                "event_type": params.get("event_type", "incident"),
                "severity": params.get("severity", "medium"),
                "affected_product_id": params.get("product_id", ""),
                "summary": params.get("summary", ""),
                "details": params.get("details", ""),
                "messages": []
            })
            return {
                "success": True,
                "notifications": result.get("notifications", []),
                "delivery_status": result.get("delivery_status", [])
            }

        elif agent_name == "cross_domain":
            from src.agents.cross_domain_agent import build_cross_domain_agent
            agent = build_cross_domain_agent()
            result = agent.invoke({
                "event_type": params.get("event_type", "data_quality_issue"),
                "affected_product_id": params.get("product_id", ""),
                "severity": params.get("severity", "medium"),
                "description": params.get("description", ""),
                "messages": []
            })
            return {
                "success": True,
                "affected_domains": result.get("affected_domains", []),
                "cross_domain_impacts": result.get("cross_domain_impacts", []),
                "executive_summary": result.get("executive_summary")
            }

        elif agent_name == "contract_evolution":
            from src.agents.contract_evolution_agent import build_contract_evolution_agent
            agent = build_contract_evolution_agent()
            result = agent.invoke({
                "contract_id": params.get("contract_id", ""),
                "messages": []
            })
            return {
                "success": True,
                "threshold_recommendations": result.get("threshold_recommendations", []),
                "new_rule_suggestions": result.get("new_rule_suggestions", []),
                "evolution_plan": result.get("evolution_plan")
            }

        else:
            return {"success": False, "error": f"Unknown agent: {agent_name}"}

    except Exception as e:
        log.error(f"Agent {agent_name} failed: {e}")
        return {"success": False, "error": str(e)}


def _get_context_from_graph() -> dict:
    """Get current system context for planning."""
    with Neo4jManager() as mgr:
        # Get summary stats
        stats_query = """
        MATCH (p:DataProduct)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        WITH count(DISTINCT p) as products, collect(DISTINCT i) as incidents
        RETURN products, size(incidents) as open_incidents,
               size([i IN incidents WHERE i.severity = 'critical']) as critical_incidents
        """
        stats = mgr.execute_query(stats_query, {})

        # Get recent incidents
        incidents_query = """
        MATCH (i:Incident {status: 'open'})
        OPTIONAL MATCH (i)<-[:HAS_INCIDENT]-(p:DataProduct)
        RETURN i.id as id, i.severity as severity, i.type as type,
               p.id as product_id, p.name as product_name
        ORDER BY i.created_at DESC
        LIMIT 5
        """
        incidents = mgr.execute_query(incidents_query, {})

        return {
            "total_products": stats[0]["products"] if stats else 0,
            "open_incidents": stats[0]["open_incidents"] if stats else 0,
            "critical_incidents": stats[0]["critical_incidents"] if stats else 0,
            "recent_incidents": [dict(i) for i in incidents]
        }


# =============================================================================
# SUPERVISOR AGENT BUILDER
# =============================================================================

def build_supervisor_agent():
    """
    Build the Supervisor Agent that orchestrates all other agents.

    The Supervisor follows this workflow:
    1. Understand - Parse and classify user intent
    2. Plan - Determine which agents to invoke and in what order
    3. Execute - Run agents according to plan
    4. Synthesize - Combine results into coherent response
    5. Recommend - Suggest next steps and follow-up questions
    """
    log = get_agent_logger("SupervisorAgent")

    def understand_intent(state: SupervisorState) -> SupervisorState:
        """Parse user query and classify intent using LLM."""
        log.info(f"Understanding intent for query: {state['query'][:100]}...")

        llm = get_llm_if_available()
        intent = "GENERAL_QUERY"
        confidence = 0.5
        suggested_agents = ["qa"]
        parameters = {}

        if llm:
            try:
                prompt = INTENT_CLASSIFICATION_PROMPT.format(query=state["query"])
                response = llm.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)

                # Parse JSON response
                if '{' in content:
                    json_start = content.index('{')
                    json_end = content.rindex('}') + 1
                    parsed = json.loads(content[json_start:json_end])

                    intent = parsed.get("intent", "GENERAL_QUERY")
                    confidence = parsed.get("confidence", 0.5)
                    suggested_agents = parsed.get("suggested_agents", ["qa"])
                    parameters = parsed.get("parameters", {})

            except Exception as e:
                log.warning(f"Intent classification failed: {e}")

        # Fallback: keyword-based classification
        query_lower = state["query"].lower()
        if any(kw in query_lower for kw in ["incident", "issue", "problem", "fix", "heal"]):
            intent = "INCIDENT_HANDLING"
            suggested_agents = ["insights", "healing"]
        elif any(kw in query_lower for kw in ["impact", "downstream", "affect"]):
            intent = "IMPACT_ANALYSIS"
            suggested_agents = ["impact", "cross_domain"]
        elif any(kw in query_lower for kw in ["sla", "compliance", "breach"]):
            intent = "SLA_MONITORING"
            suggested_agents = ["sla"]
        elif any(kw in query_lower for kw in ["report", "insight", "governance", "overview", "health"]):
            intent = "GOVERNANCE_INSIGHTS"
            suggested_agents = ["insights"]
        elif any(kw in query_lower for kw in ["find", "search", "discover", "catalog"]):
            intent = "DATA_DISCOVERY"
            suggested_agents = ["discovery"]
        elif any(kw in query_lower for kw in ["lineage", "upstream", "source", "flow"]):
            intent = "LINEAGE_TRACKING"
            suggested_agents = ["impact"]
        elif any(kw in query_lower for kw in ["notify", "alert", "stakeholder"]):
            intent = "NOTIFICATION"
            suggested_agents = ["notification"]
        elif any(kw in query_lower for kw in ["contract", "rule", "evolve"]):
            intent = "CONTRACT_MANAGEMENT"
            suggested_agents = ["contract_evolution"]

        log.info(f"Classified intent: {intent} (confidence: {confidence})")

        return {
            **state,
            "intent": intent,
            "intent_confidence": confidence,
            "agent_results": {"_parameters": parameters, "_suggested": suggested_agents},
            "execution_log": [{
                "step": "understand_intent",
                "intent": intent,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }],
            "status": "intent_classified"
        }

    def create_execution_plan(state: SupervisorState) -> SupervisorState:
        """Create an execution plan based on intent and context."""
        log.info("Creating execution plan")

        intent = state.get("intent", "GENERAL_QUERY")
        params = state.get("agent_results", {}).get("_parameters", {})
        suggested = state.get("agent_results", {}).get("_suggested", [])

        # Get system context
        context = _get_context_from_graph()

        # Build execution plan
        plan = []

        if intent == "GOVERNANCE_INSIGHTS":
            plan = [
                {"agent": "insights", "params": {"time_range_days": 30}, "purpose": "Get overall governance health"},
                {"agent": "sla", "params": {"product_ids": None}, "purpose": "Check SLA compliance"}
            ]

        elif intent == "INCIDENT_HANDLING":
            # Check if there are open incidents
            if context.get("open_incidents", 0) > 0:
                incident = context.get("recent_incidents", [{}])[0]
                plan = [
                    {"agent": "insights", "params": {}, "purpose": "Get governance overview"},
                    {"agent": "healing", "params": {
                        "incident_id": params.get("incident_id", incident.get("id", "")),
                        "severity": params.get("severity", incident.get("severity", "medium"))
                    }, "purpose": "Analyze and remediate incident"}
                ]
                if incident.get("product_id"):
                    plan.append({
                        "agent": "impact",
                        "params": {"product_id": incident.get("product_id")},
                        "purpose": "Assess downstream impact"
                    })
            else:
                plan = [
                    {"agent": "insights", "params": {}, "purpose": "Check for any issues"}
                ]

        elif intent == "IMPACT_ANALYSIS":
            product_id = params.get("product_id", "")
            if not product_id and context.get("recent_incidents"):
                product_id = context["recent_incidents"][0].get("product_id", "")

            plan = [
                {"agent": "impact", "params": {"product_id": product_id}, "purpose": "Analyze downstream impact"},
                {"agent": "cross_domain", "params": {
                    "event_type": "data_quality_issue",
                    "product_id": product_id,
                    "severity": "medium"
                }, "purpose": "Check cross-domain effects"}
            ]

        elif intent == "SLA_MONITORING":
            plan = [
                {"agent": "sla", "params": {"product_ids": params.get("product_ids")}, "purpose": "Monitor SLA compliance"}
            ]

        elif intent == "DATA_DISCOVERY":
            plan = [
                {"agent": "discovery", "params": {"query": state["query"]}, "purpose": "Search data catalog"}
            ]

        elif intent == "NOTIFICATION":
            plan = [
                {"agent": "insights", "params": {}, "purpose": "Get current status"},
                {"agent": "notification", "params": {
                    "event_type": params.get("event_type", "status_update"),
                    "severity": params.get("severity", "medium"),
                    "product_id": params.get("product_id", ""),
                    "summary": state["query"]
                }, "purpose": "Generate notifications"}
            ]

        elif intent == "CONTRACT_MANAGEMENT":
            plan = [
                {"agent": "contract_evolution", "params": {
                    "contract_id": params.get("contract_id", "")
                }, "purpose": "Analyze contract evolution opportunities"}
            ]

        else:  # GENERAL_QUERY or fallback
            plan = [
                {"agent": "qa", "params": {"question": state["query"]}, "purpose": "Answer question"}
            ]

        log.info(f"Created plan with {len(plan)} steps")

        return {
            **state,
            "execution_plan": plan,
            "current_step": 0,
            "execution_log": state.get("execution_log", []) + [{
                "step": "create_plan",
                "plan_size": len(plan),
                "agents": [p["agent"] for p in plan],
                "timestamp": datetime.now().isoformat()
            }],
            "status": "plan_created"
        }

    def execute_plan(state: SupervisorState) -> SupervisorState:
        """Execute the planned agent invocations."""
        log.info("Executing plan")

        plan = state.get("execution_plan", [])
        results = state.get("agent_results", {})
        findings = state.get("intermediate_findings", [])
        execution_log = state.get("execution_log", [])
        requires_approval = False
        approval_reason = None

        for i, step in enumerate(plan):
            agent_name = step["agent"]
            params = step["params"]
            purpose = step.get("purpose", "")

            log.info(f"Step {i+1}/{len(plan)}: Running {agent_name} - {purpose}")

            # Run agent
            result = _run_agent(agent_name, params)
            results[agent_name] = result

            # Log execution
            execution_log.append({
                "step": f"execute_{agent_name}",
                "success": result.get("success", False),
                "purpose": purpose,
                "timestamp": datetime.now().isoformat()
            })

            # Extract key findings
            if result.get("success"):
                if agent_name == "insights":
                    if result.get("executive_summary"):
                        findings.append(f"Governance Status: {result['executive_summary'][:200]}")
                    for finding in result.get("key_findings", [])[:3]:
                        findings.append(finding)

                elif agent_name == "healing":
                    if result.get("root_cause"):
                        findings.append(f"Root Cause: {result['root_cause']}")
                    if result.get("requires_approval"):
                        requires_approval = True
                        approval_reason = "Healing action requires human approval"

                elif agent_name == "impact":
                    findings.append(f"Risk Score: {result.get('risk_score', 0)}/100")
                    findings.append(f"Business Impact: {result.get('business_impact', 'Unknown')}")

                elif agent_name == "sla":
                    summary = result.get("summary", {})
                    findings.append(
                        f"SLA Status: {summary.get('healthy', 0)} healthy, "
                        f"{summary.get('breached', 0)} breached, "
                        f"{summary.get('at_risk', 0)} at risk"
                    )

                elif agent_name == "discovery":
                    products = result.get("products", [])
                    findings.append(f"Found {len(products)} matching data products")

        return {
            **state,
            "agent_results": results,
            "intermediate_findings": findings,
            "total_agents_invoked": len(plan),
            "requires_human_approval": requires_approval,
            "approval_reason": approval_reason,
            "execution_log": execution_log,
            "status": "execution_complete"
        }

    def check_approval_needed(state: SupervisorState) -> Literal["wait_approval", "synthesize"]:
        """Check if human approval is needed before proceeding."""
        if state.get("requires_human_approval") and not state.get("approved"):
            return "wait_approval"
        return "synthesize"

    def wait_for_approval(state: SupervisorState) -> SupervisorState:
        """Wait for human approval (in real implementation, this would pause)."""
        log.info(f"Waiting for approval: {state.get('approval_reason')}")

        return {
            **state,
            "status": "awaiting_approval",
            "execution_log": state.get("execution_log", []) + [{
                "step": "await_approval",
                "reason": state.get("approval_reason"),
                "timestamp": datetime.now().isoformat()
            }]
        }

    def synthesize_response(state: SupervisorState) -> SupervisorState:
        """Synthesize all agent results into a coherent response."""
        log.info("Synthesizing response")

        llm = get_llm_if_available()
        results = state.get("agent_results", {})
        findings = state.get("intermediate_findings", [])
        intent = state.get("intent", "GENERAL_QUERY")

        # Build context for synthesis
        context_parts = []
        for agent_name, result in results.items():
            if agent_name.startswith("_"):
                continue
            if result.get("success"):
                context_parts.append(f"**{agent_name.title()} Agent Results:**\n{json.dumps(result, indent=2, default=str)[:1000]}")

        response = ""
        recommendations = []
        follow_ups = []

        if llm:
            try:
                synthesis_prompt = f"""You are a data governance assistant. Synthesize these agent results into a clear, actionable response.

User Query: {state['query']}
Intent: {intent}

Agent Results:
{chr(10).join(context_parts)}

Key Findings:
{chr(10).join(f'- {f}' for f in findings)}

Provide:
1. A clear summary response (2-3 paragraphs)
2. 3-5 specific recommendations
3. 2-3 follow-up questions the user might want to ask

Format as JSON:
{{
    "response": "<summary>",
    "recommendations": ["<rec1>", "<rec2>", ...],
    "follow_up_questions": ["<q1>", "<q2>", ...]
}}"""

                llm_response = llm.invoke(synthesis_prompt)
                content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

                if '{' in content:
                    json_start = content.index('{')
                    json_end = content.rindex('}') + 1
                    parsed = json.loads(content[json_start:json_end])

                    response = parsed.get("response", "")
                    recommendations = parsed.get("recommendations", [])
                    follow_ups = parsed.get("follow_up_questions", [])
                else:
                    response = content

            except Exception as e:
                log.warning(f"LLM synthesis failed: {e}")

        # Fallback synthesis
        if not response:
            response = f"Based on my analysis of your query about '{intent.lower().replace('_', ' ')}':\n\n"
            response += "**Key Findings:**\n"
            for finding in findings[:5]:
                response += f"- {finding}\n"

            # Add agent-specific summaries
            if "insights" in results and results["insights"].get("success"):
                response += f"\n**Governance Overview:**\n{results['insights'].get('executive_summary', 'No summary available')}\n"

            if "healing" in results and results["healing"].get("success"):
                response += f"\n**Incident Analysis:**\n"
                response += f"- Action: {results['healing'].get('action', 'N/A')}\n"
                response += f"- Root Cause: {results['healing'].get('root_cause', 'Unknown')}\n"

            if "sla" in results and results["sla"].get("success"):
                summary = results["sla"].get("summary", {})
                response += f"\n**SLA Status:**\n"
                response += f"- Total: {summary.get('total_slas', 0)} SLAs monitored\n"
                response += f"- Breached: {summary.get('breached', 0)}\n"

            # Default recommendations
            recommendations = [
                "Review the detailed agent results for more information",
                "Set up automated monitoring for ongoing issues",
                "Consider scheduling a governance review meeting"
            ]

            follow_ups = [
                "What specific actions should I take first?",
                "Can you show me the data lineage for affected products?",
                "What's the trend over the past month?"
            ]

        return {
            **state,
            "response": response,
            "recommendations": recommendations,
            "follow_up_questions": follow_ups,
            "execution_log": state.get("execution_log", []) + [{
                "step": "synthesize",
                "response_length": len(response),
                "timestamp": datetime.now().isoformat()
            }],
            "status": "completed"
        }

    def persist_execution(state: SupervisorState) -> SupervisorState:
        """Persist execution record to the graph."""
        log.info("Persisting supervisor execution")

        try:
            with Neo4jManager() as mgr:
                mgr.execute_query("""
                    CREATE (e:SupervisorExecution {
                        id: 'sup_' + toString(datetime()),
                        query: $query,
                        intent: $intent,
                        agents_invoked: $agents_invoked,
                        status: $status,
                        created_at: datetime()
                    })
                """, {
                    "query": state.get("query", "")[:500],
                    "intent": state.get("intent", ""),
                    "agents_invoked": state.get("total_agents_invoked", 0),
                    "status": state.get("status", "")
                })
        except Exception as e:
            log.warning(f"Failed to persist execution: {e}")

        return state

    # Build the graph
    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("understand", understand_intent)
    graph.add_node("plan", create_execution_plan)
    graph.add_node("execute", execute_plan)
    graph.add_node("wait_approval", wait_for_approval)
    graph.add_node("synthesize", synthesize_response)
    graph.add_node("persist", persist_execution)

    # Set entry point
    graph.set_entry_point("understand")

    # Add edges
    graph.add_edge("understand", "plan")
    graph.add_edge("plan", "execute")

    # Conditional edge for approval
    graph.add_conditional_edges(
        "execute",
        check_approval_needed,
        {
            "wait_approval": "wait_approval",
            "synthesize": "synthesize"
        }
    )

    graph.add_edge("wait_approval", "synthesize")  # After approval granted
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=get_checkpointer())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_supervisor(
    query: str,
    conversation_history: List[dict] = None,
    approved: bool = True
) -> dict:
    """
    Run the Supervisor Agent with a natural language query.

    Args:
        query: User's natural language query
        conversation_history: Previous conversation context
        approved: Pre-approve any actions requiring approval

    Returns:
        Complete supervisor response with results and recommendations

    Example:
        >>> result = run_supervisor("What's wrong with my data and how do I fix it?")
        >>> print(result["response"])
    """
    agent = build_supervisor_agent()

    initial_state: SupervisorState = {
        "query": query,
        "conversation_history": conversation_history or [],
        "intent": None,
        "intent_confidence": None,
        "execution_plan": [],
        "current_step": 0,
        "agent_results": {},
        "intermediate_findings": [],
        "requires_human_approval": False,
        "approval_reason": None,
        "approved": approved,
        "response": None,
        "recommendations": [],
        "follow_up_questions": [],
        "execution_log": [],
        "total_agents_invoked": 0,
        "status": "initialized",
        "messages": []
    }

    result = agent.invoke(initial_state)

    return {
        "query": query,
        "intent": result.get("intent"),
        "intent_confidence": result.get("intent_confidence"),
        "response": result.get("response"),
        "recommendations": result.get("recommendations", []),
        "follow_up_questions": result.get("follow_up_questions", []),
        "agent_results": {
            k: v for k, v in result.get("agent_results", {}).items()
            if not k.startswith("_")
        },
        "findings": result.get("intermediate_findings", []),
        "agents_invoked": result.get("total_agents_invoked", 0),
        "execution_log": result.get("execution_log", []),
        "status": result.get("status")
    }


def get_supervisor_capabilities() -> dict:
    """
    Get information about supervisor capabilities and available agents.

    Returns:
        Dictionary describing all capabilities
    """
    return {
        "name": "DPOS Supervisor Agent",
        "description": "Global orchestrator that coordinates all DPOS agents",
        "intents": [
            "DATA_DISCOVERY", "INCIDENT_HANDLING", "IMPACT_ANALYSIS",
            "SLA_MONITORING", "GOVERNANCE_INSIGHTS", "CONTRACT_MANAGEMENT",
            "LINEAGE_TRACKING", "NOTIFICATION", "MULTI_TASK", "GENERAL_QUERY"
        ],
        "agents": AGENT_CAPABILITIES,
        "example_queries": [
            "What's the current health of my data governance?",
            "Find all customer-related data products",
            "There's a problem with the Order data - investigate and fix it",
            "What's the downstream impact if Customer data fails?",
            "Are any SLAs at risk of breach?",
            "Generate a governance report for executives",
            "Notify stakeholders about the current incident status"
        ]
    }
