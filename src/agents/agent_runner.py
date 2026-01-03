"""
Agent Runner - Central entry point for invoking DPOS agents.
All agents now use checkpointing for persistence and resumability.
"""
import uuid
from src.agents.discovery_agent import build_discovery_agent
from src.agents.impact_agent import build_impact_agent
from src.agents.healing_agent import build_healing_agent
from src.agents.steward_agent import build_steward_agent
from src.agents.qa_agent import build_qa_agent
from src.agents.checkpointer import get_thread_config


# Lazy-loaded agents
_healing_agent = None
_steward_agent = None
_impact_agent = None
_qa_agent = None
_discovery_agent = None


def _get_healing_agent():
    global _healing_agent
    if _healing_agent is None:
        _healing_agent = build_healing_agent()
    return _healing_agent


def _get_steward_agent():
    global _steward_agent
    if _steward_agent is None:
        _steward_agent = build_steward_agent()
    return _steward_agent


def _get_impact_agent():
    global _impact_agent
    if _impact_agent is None:
        _impact_agent = build_impact_agent()
    return _impact_agent


def _get_qa_agent():
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = build_qa_agent()
    return _qa_agent


def _get_discovery_agent():
    global _discovery_agent
    if _discovery_agent is None:
        _discovery_agent = build_discovery_agent()
    return _discovery_agent


def handle_incident(incident_id: str, severity: str = "medium", thread_id: str = None):
    """
    Handle an incident using the healing agent.
    This is the main entry point called by the enforcement engine.

    Args:
        incident_id: The incident ID to handle
        severity: Incident severity (low, medium, high, critical)
        thread_id: Optional thread ID for resuming conversations

    Returns:
        The final agent state
    """
    print(f"[AGENT] Healing Agent invoked for Incident {incident_id}")

    agent = _get_healing_agent()

    # Generate thread ID if not provided
    if thread_id is None:
        thread_id = f"healing_{incident_id}_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state = {
        "incident_id": incident_id,
        "severity": severity,
        "product_id": None,
        "diagnosis": None,
        "root_cause": None,
        "recommendation": "",
        "action": "",
        "fallback_available": False,
        "requires_approval": False,
        "approved": False,
        "status": "new",
        "messages": []
    }

    final_state = agent.invoke(initial_state, config)

    if final_state:
        print("[AGENT] Healing Agent finished with state:")
        print(f"  Status: {final_state.get('status')}")
        print(f"  Action: {final_state.get('action')}")
        print(f"  Recommendation: {final_state.get('recommendation')}")

    return final_state


def handle_incident_steward(incident_id: str, severity: str = "medium", thread_id: str = None):
    """
    Handle an incident using the steward agent for governance.

    Args:
        incident_id: The incident ID to handle
        severity: Incident severity
        thread_id: Optional thread ID for resuming conversations

    Returns:
        The final agent state
    """
    print(f"[AGENT] Steward Agent invoked for Incident {incident_id}")

    agent = _get_steward_agent()

    if thread_id is None:
        thread_id = f"steward_{incident_id}_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state = {
        "incident_id": incident_id,
        "severity": severity,
        "product_id": None,
        "analysis": None,
        "quality_score": None,
        "remediation_steps": [],
        "notifications_sent": [],
        "status": "new"
    }

    final_state = agent.invoke(initial_state, config)

    if final_state:
        print("[AGENT] Steward Agent finished")
        print(f"  Status: {final_state.get('status')}")
        print(f"  Remediation Steps: {len(final_state.get('remediation_steps', []))}")

    return final_state


def analyze_impact(product_id: str, incident_id: str = None, thread_id: str = None):
    """
    Analyze the impact of a product failure.

    Args:
        product_id: The product ID to analyze
        incident_id: Optional related incident ID
        thread_id: Optional thread ID for resuming conversations

    Returns:
        The final agent state with impact analysis
    """
    print(f"[IMPACT] Analysis for {product_id}")

    agent = _get_impact_agent()

    if thread_id is None:
        thread_id = f"impact_{product_id}_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state = {
        "product_id": product_id,
        "incident_id": incident_id,
        "downstream_products": [],
        "affected_pipelines": [],
        "affected_users": 0,
        "business_impact": "",
        "risk_score": 0.0,
        "status": "new"
    }

    result = agent.invoke(initial_state, config)

    if result:
        print(f"[IMPACT] Analysis complete")
        print(f"  Risk Score: {result.get('risk_score')}")
        print(f"  Business Impact: {result.get('business_impact')}")
        print(f"  Downstream Products: {len(result.get('downstream_products', []))}")

    return result


def ask_question(question: str, thread_id: str = None):
    """
    Ask a question to the QA agent.

    Args:
        question: The question to ask
        thread_id: Optional thread ID for conversation continuity

    Returns:
        The final agent state with answer
    """
    print(f"[QA] Agent: {question}")

    agent = _get_qa_agent()

    if thread_id is None:
        thread_id = f"qa_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state = {
        "question": question,
        "context": [],
        "answer": "",
        "sources": []
    }

    result = agent.invoke(initial_state, config)

    if result:
        print(f"[QA] Answer generated with {len(result.get('sources', []))} sources")

    return result


def discover_products(query: str, thread_id: str = None):
    """
    Discover data products matching a query.

    Args:
        query: Search query
        thread_id: Optional thread ID

    Returns:
        The final agent state with discovered products
    """
    print(f"[DISCOVERY] Agent: {query}")

    agent = _get_discovery_agent()

    if thread_id is None:
        thread_id = f"discovery_{uuid.uuid4().hex[:8]}"

    config = get_thread_config(thread_id)

    initial_state = {
        "query": query,
        "sources_scanned": [],
        "discovered_products": [],
        "recommendations": [],
        "status": "new"
    }

    result = agent.invoke(initial_state, config)

    if result:
        print(f"[DISCOVERY] Found {len(result.get('discovered_products', []))} products")

    return result


# Aliases for backwards compatibility
handle_incident_enhanced = handle_incident
