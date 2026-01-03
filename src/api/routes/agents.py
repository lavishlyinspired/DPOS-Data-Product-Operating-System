"""
Agents API Routes
Endpoints for invoking all AI agents in the DPOS platform.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import json
import asyncio

# Core agents
from src.agents.discovery_agent import build_discovery_agent
from src.agents.impact_agent import build_impact_agent
from src.agents.healing_agent import build_healing_agent
from src.agents.steward_agent import build_steward_agent
from src.agents.qa_agent import build_qa_agent


# ============================================================================
# REQUEST MODELS
# ============================================================================

class AgentRequest(BaseModel):
    query: str


class IncidentRequest(BaseModel):
    incident_id: str
    severity: Optional[str] = "medium"


class ImpactRequest(BaseModel):
    product_id: str


class PredictiveRequest(BaseModel):
    product_ids: List[str]


class OrchestratorRequest(BaseModel):
    incident_ids: List[str]


class ContractEvolutionRequest(BaseModel):
    contract_id: str


class CrossDomainRequest(BaseModel):
    event_type: str
    product_id: str
    severity: Optional[str] = "medium"
    description: Optional[str] = ""


class NotificationRequest(BaseModel):
    event_type: str
    severity: str
    product_id: str
    summary: str
    details: Optional[str] = ""


class SLAMonitorRequest(BaseModel):
    product_ids: Optional[List[str]] = None


class InsightsRequest(BaseModel):
    time_range_days: Optional[int] = 30


class SupervisorRequest(BaseModel):
    """Request model for the Supervisor Agent."""
    query: str
    conversation_history: Optional[List[dict]] = None
    auto_approve: Optional[bool] = True


router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent_config():
    """Generate config with thread_id for checkpointing."""
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def safe_import_agent(module_path: str, builder_name: str):
    """Safely import an agent builder function."""
    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, builder_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load agent {builder_name}: {str(e)}"
        )


# ============================================================================
# CORE AGENT ENDPOINTS
# ============================================================================

@router.post("/discovery")
def discovery(req: AgentRequest):
    """Run the discovery agent to find data products matching a query."""
    agent = build_discovery_agent()
    result = agent.invoke(
        {"query": req.query, "results": [], "messages": []},
        config=get_agent_config()
    )
    return {
        "results": result.get("results", []),
        "recommendations": result.get("recommendations", [])
    }


@router.post("/impact")
def impact_analysis(req: ImpactRequest):
    """Analyze the impact of a data product failure."""
    agent = build_impact_agent()
    result = agent.invoke(
        {"product_id": req.product_id, "impact": {}, "status": "", "messages": []},
        config=get_agent_config()
    )
    return {
        "product_id": req.product_id,
        "impact": result.get("impact", {}),
        "risk_score": result.get("risk_score", 0),
        "business_impact": result.get("business_impact", ""),
        "mitigation_suggestions": result.get("mitigation_suggestions", []),
        "status": result.get("status")
    }


@router.post("/healing")
def healing(req: IncidentRequest):
    """Trigger the self-healing agent for an incident."""
    agent = build_healing_agent()
    result = agent.invoke(
        {
            "incident_id": req.incident_id,
            "severity": req.severity,
            "recommendation": "",
            "action": "",
            "status": "",
            "messages": []
        },
        config=get_agent_config()
    )
    return {
        "incident_id": result.get("incident_id"),
        "action": result.get("action"),
        "recommendation": result.get("recommendation"),
        "root_cause": result.get("root_cause"),
        "root_cause_confidence": result.get("root_cause_confidence"),
        "assessed_severity": result.get("assessed_severity"),
        "remediation_steps": result.get("remediation_steps", []),
        "requires_approval": result.get("requires_approval", False),
        "incident_narrative": result.get("incident_narrative"),
        "status": result.get("status")
    }


@router.post("/steward")
def steward(req: IncidentRequest):
    """Invoke the AI data steward agent."""
    agent = build_steward_agent()
    result = agent.invoke(
        {
            "incident_id": req.incident_id,
            "severity": req.severity,
            "status": "new",
            "messages": []
        },
        config=get_agent_config()
    )
    return {
        "incident_id": result.get("incident_id"),
        "governance_recommendations": result.get("governance_recommendations", []),
        "preventive_measures": result.get("preventive_measures", []),
        "policy_updates": result.get("policy_updates", []),
        "root_cause": result.get("root_cause"),
        "status": result.get("status")
    }


@router.post("/qa")
def qa(req: AgentRequest):
    """Ask a question to the QA agent."""
    agent = build_qa_agent()
    result = agent.invoke(
        {"question": req.query, "answer": "", "context": [], "sources": [], "messages": []},
        config=get_agent_config()
    )
    return {
        "question": req.query,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", [])
    }


# ============================================================================
# ADVANCED AGENT ENDPOINTS
# ============================================================================

@router.post("/predictive")
def predictive_analysis(req: PredictiveRequest):
    """Run predictive analysis on products to forecast potential issues."""
    try:
        from src.agents.predictive_agent import build_predictive_agent
        agent = build_predictive_agent()
        result = agent.invoke(
            {"product_ids": req.product_ids, "messages": []},
            config=get_agent_config()
        )
        return {
            "product_ids": req.product_ids,
            "predictions": result.get("predictions", []),
            "risk_factors": result.get("risk_factors", []),
            "preventive_actions": result.get("preventive_actions", []),
            "status": result.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orchestrator")
def orchestrate_incidents(req: OrchestratorRequest):
    """Orchestrate multiple incidents for coordinated resolution."""
    try:
        from src.agents.orchestrator_agent import build_orchestrator_agent
        agent = build_orchestrator_agent()
        result = agent.invoke(
            {"incident_ids": req.incident_ids, "messages": []},
            config=get_agent_config()
        )
        return {
            "incident_ids": req.incident_ids,
            "incident_analysis": result.get("incident_analysis", []),
            "prioritized_incidents": result.get("prioritized_incidents", []),
            "batch_actions": result.get("batch_actions", []),
            "orchestration_summary": result.get("orchestration_summary"),
            "status": result.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contract-evolution")
def contract_evolution(req: ContractEvolutionRequest):
    """Analyze contract evolution opportunities based on violation patterns."""
    try:
        from src.agents.contract_evolution_agent import build_contract_evolution_agent
        agent = build_contract_evolution_agent()
        result = agent.invoke(
            {"contract_id": req.contract_id, "messages": []},
            config=get_agent_config()
        )
        return {
            "contract_id": req.contract_id,
            "violation_analysis": result.get("violation_analysis"),
            "threshold_recommendations": result.get("threshold_recommendations", []),
            "new_rule_suggestions": result.get("new_rule_suggestions", []),
            "evolution_plan": result.get("evolution_plan"),
            "status": result.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cross-domain")
def cross_domain_analysis(req: CrossDomainRequest):
    """Analyze cross-domain impact of an event."""
    try:
        from src.agents.cross_domain_agent import build_cross_domain_agent
        agent = build_cross_domain_agent()
        result = agent.invoke(
            {
                "event_type": req.event_type,
                "affected_product_id": req.product_id,
                "severity": req.severity,
                "description": req.description,
                "messages": []
            },
            config=get_agent_config()
        )
        return {
            "product_id": req.product_id,
            "event_type": req.event_type,
            "affected_domains": result.get("affected_domains", []),
            "cross_domain_impacts": result.get("cross_domain_impacts", []),
            "coordination_plan": result.get("coordination_plan"),
            "executive_summary": result.get("executive_summary"),
            "status": result.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification")
def generate_notifications(req: NotificationRequest):
    """Generate stakeholder notifications for an event."""
    try:
        from src.agents.notification_agent import build_notification_agent
        agent = build_notification_agent()
        result = agent.invoke(
            {
                "event_type": req.event_type,
                "severity": req.severity,
                "affected_product_id": req.product_id,
                "summary": req.summary,
                "details": req.details or req.summary,
                "messages": []
            },
            config=get_agent_config()
        )
        return {
            "event_type": req.event_type,
            "notifications": result.get("notifications", []),
            "escalation_actions": result.get("escalation_actions", []),
            "delivery_status": result.get("delivery_status", []),
            "status": result.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sla-monitor")
def monitor_slas(req: SLAMonitorRequest):
    """Monitor SLA compliance and detect breaches."""
    try:
        from src.agents.sla_agent import run_sla_monitoring
        result = run_sla_monitoring(req.product_ids)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights")
def generate_insights(req: InsightsRequest):
    """Generate governance insights and recommendations."""
    try:
        from src.agents.insights_agent import run_insights_analysis
        result = run_insights_analysis(req.time_range_days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STREAMING ENDPOINTS (SSE)
# ============================================================================

@router.post("/healing/stream")
async def healing_stream(req: IncidentRequest):
    """Stream healing agent progress via Server-Sent Events."""

    async def generate():
        try:
            agent = build_healing_agent()

            # Simulate streaming by yielding state updates
            initial_state = {
                "incident_id": req.incident_id,
                "severity": req.severity,
                "recommendation": "",
                "action": "",
                "status": "starting",
                "messages": []
            }

            # Yield initial state
            yield f"data: {json.dumps({'status': 'loading_incident', 'progress': 10})}\n\n"
            await asyncio.sleep(0.1)

            # Run agent
            result = agent.invoke(initial_state, config=get_agent_config())

            # Yield progress updates
            yield f"data: {json.dumps({'status': 'analyzing', 'progress': 50})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'status': 'generating_recommendation', 'progress': 80})}\n\n"
            await asyncio.sleep(0.1)

            # Yield final result
            final_result = {
                "status": "completed",
                "progress": 100,
                "result": {
                    "incident_id": result.get("incident_id"),
                    "action": result.get("action"),
                    "recommendation": result.get("recommendation"),
                    "root_cause": result.get("root_cause"),
                    "status": result.get("status")
                }
            }
            yield f"data: {json.dumps(final_result)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.post("/insights/stream")
async def insights_stream(req: InsightsRequest):
    """Stream insights generation progress via Server-Sent Events."""

    async def generate():
        try:
            from src.agents.insights_agent import run_insights_analysis

            yield f"data: {json.dumps({'status': 'gathering_data', 'progress': 10})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'status': 'analyzing_health', 'progress': 30})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'status': 'analyzing_incidents', 'progress': 50})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'status': 'generating_insights', 'progress': 70})}\n\n"
            await asyncio.sleep(0.1)

            # Run actual analysis
            result = run_insights_analysis(req.time_range_days)

            yield f"data: {json.dumps({'status': 'finalizing', 'progress': 90})}\n\n"
            await asyncio.sleep(0.1)

            final_result = {
                "status": "completed",
                "progress": 100,
                "result": result
            }
            yield f"data: {json.dumps(final_result)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/available")
def list_available_agents():
    """List all available agents and their descriptions."""
    return {
        "agents": [
            {
                "id": "discovery",
                "name": "Discovery Agent",
                "description": "Discover and catalog data products",
                "endpoint": "/api/agents/discovery",
                "category": "core"
            },
            {
                "id": "qa",
                "name": "Q&A Agent",
                "description": "Ask natural language questions about data products",
                "endpoint": "/api/agents/qa",
                "category": "core"
            },
            {
                "id": "healing",
                "name": "Healing Agent",
                "description": "Self-healing for data quality issues with LLM-powered analysis",
                "endpoint": "/api/agents/healing",
                "category": "core"
            },
            {
                "id": "steward",
                "name": "Steward Agent",
                "description": "Data governance recommendations and compliance monitoring",
                "endpoint": "/api/agents/steward",
                "category": "core"
            },
            {
                "id": "impact",
                "name": "Impact Agent",
                "description": "Analyze downstream impact with risk assessment",
                "endpoint": "/api/agents/impact",
                "category": "core"
            },
            {
                "id": "predictive",
                "name": "Predictive Agent",
                "description": "Predict issues using historical patterns",
                "endpoint": "/api/agents/predictive",
                "category": "advanced"
            },
            {
                "id": "orchestrator",
                "name": "Orchestrator Agent",
                "description": "Coordinate multiple incidents for batch resolution",
                "endpoint": "/api/agents/orchestrator",
                "category": "advanced"
            },
            {
                "id": "contract-evolution",
                "name": "Contract Evolution Agent",
                "description": "Evolve data contracts based on violation patterns",
                "endpoint": "/api/agents/contract-evolution",
                "category": "advanced"
            },
            {
                "id": "cross-domain",
                "name": "Cross-Domain Agent",
                "description": "Analyze impacts spanning multiple business domains",
                "endpoint": "/api/agents/cross-domain",
                "category": "advanced"
            },
            {
                "id": "notification",
                "name": "Notification Agent",
                "description": "Generate tailored stakeholder notifications",
                "endpoint": "/api/agents/notification",
                "category": "advanced"
            },
            {
                "id": "sla-monitor",
                "name": "SLA Monitor Agent",
                "description": "Monitor SLA compliance and detect/predict breaches",
                "endpoint": "/api/agents/sla-monitor",
                "category": "advanced"
            },
            {
                "id": "insights",
                "name": "Insights Agent",
                "description": "Generate automated governance insights and recommendations",
                "endpoint": "/api/agents/insights",
                "category": "advanced"
            },
            {
                "id": "supervisor",
                "name": "Supervisor Agent",
                "description": "Global orchestrator that coordinates all agents via natural language",
                "endpoint": "/api/agents/supervisor",
                "category": "orchestration"
            }
        ]
    }


# ============================================================================
# SUPERVISOR AGENT ENDPOINTS
# ============================================================================

class SupervisorRequest(BaseModel):
    """Request model for the Supervisor Agent."""
    query: str
    conversation_history: Optional[List[dict]] = None
    auto_approve: Optional[bool] = True


@router.post("/supervisor")
def supervisor(req: SupervisorRequest):
    """
    Run the Supervisor Agent - the global orchestrator.

    The Supervisor Agent interprets natural language queries, determines which
    agents to invoke, coordinates their execution, and synthesizes results.

    Example queries:
    - "What's the current health of my data governance?"
    - "There's a problem with Customer data - investigate and fix it"
    - "What's the downstream impact if Order data fails?"
    - "Generate a governance report for the executive team"

    Args:
        query: Natural language query
        conversation_history: Previous conversation context (optional)
        auto_approve: Auto-approve actions requiring approval (default: True)

    Returns:
        Synthesized response with recommendations and follow-up questions
    """
    try:
        from src.agents.supervisor_agent import run_supervisor
        result = run_supervisor(
            query=req.query,
            conversation_history=req.conversation_history,
            approved=req.auto_approve
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supervisor/stream")
async def supervisor_stream(req: SupervisorRequest):
    """
    Stream Supervisor Agent progress via Server-Sent Events.

    Provides real-time updates as the supervisor:
    1. Classifies intent
    2. Creates execution plan
    3. Runs each agent
    4. Synthesizes response
    """

    async def generate():
        try:
            yield f"data: {json.dumps({'status': 'understanding_intent', 'progress': 10, 'message': 'Analyzing your query...'})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'status': 'creating_plan', 'progress': 20, 'message': 'Determining which agents to use...'})}\n\n"
            await asyncio.sleep(0.1)

            # Run the actual supervisor
            from src.agents.supervisor_agent import run_supervisor
            result = run_supervisor(
                query=req.query,
                conversation_history=req.conversation_history,
                approved=req.auto_approve
            )

            # Stream intermediate progress
            for i, log_entry in enumerate(result.get("execution_log", [])):
                if log_entry.get("step", "").startswith("execute_"):
                    agent_name = log_entry["step"].replace("execute_", "")
                    progress = 30 + (i * 10)
                    yield f"data: {json.dumps({'status': 'executing', 'progress': min(progress, 80), 'message': f'Running {agent_name} agent...', 'agent': agent_name})}\n\n"
                    await asyncio.sleep(0.05)

            yield f"data: {json.dumps({'status': 'synthesizing', 'progress': 90, 'message': 'Combining results...'})}\n\n"
            await asyncio.sleep(0.1)

            # Final result
            final_result = {
                "status": "completed",
                "progress": 100,
                "result": result
            }
            yield f"data: {json.dumps(final_result)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/supervisor/capabilities")
def get_supervisor_capabilities_endpoint():
    """
    Get information about the Supervisor Agent's capabilities.

    Returns details about:
    - Supported intents
    - Available agents it can orchestrate
    - Example queries
    """
    try:
        from src.agents.supervisor_agent import get_supervisor_capabilities
        return get_supervisor_capabilities()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
