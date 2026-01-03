"""
Cross-Domain Impact Agent
Analyzes incidents and changes that span multiple business domains.
Uses LLM to understand complex cross-domain dependencies and impacts.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime, UTC
import operator
import logging
import json

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# Try to import LLM components
try:
    from src.core.llm import UnifiedLLM, LLMConfig
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class CrossDomainState(TypedDict):
    """State for cross-domain impact analysis."""
    trigger_event: Dict  # The event that triggered analysis
    affected_domains: List[str]
    domain_products: Dict[str, List[Dict]]  # Products per domain
    cross_domain_dependencies: List[Dict]
    impact_by_domain: Dict[str, Dict]
    cascading_effects: List[Dict]
    mitigation_by_domain: Dict[str, List[str]]
    coordination_plan: Optional[str]
    executive_summary: Optional[str]
    messages: Annotated[List[str], operator.add]


class CrossDomainImpactAgent:
    """
    Agent that analyzes impacts spanning multiple business domains.
    Coordinates understanding across Sales, Marketing, Operations, Finance, etc.
    """

    def __init__(self, graph_manager=None):
        self.graph_manager = graph_manager
        self._llm = None

        if LLM_AVAILABLE:
            try:
                config = LLMConfig()
                self._llm = UnifiedLLM(config)
                logger.info("CrossDomainImpactAgent initialized with LLM support")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")

        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the cross-domain analysis workflow."""
        workflow = StateGraph(CrossDomainState)

        workflow.add_node("identify_domains", self._identify_affected_domains)
        workflow.add_node("map_dependencies", self._map_cross_domain_dependencies)
        workflow.add_node("analyze_cascading", self._analyze_cascading_effects)
        workflow.add_node("generate_mitigations", self._generate_domain_mitigations)
        workflow.add_node("create_coordination", self._create_coordination_plan)

        workflow.set_entry_point("identify_domains")
        workflow.add_edge("identify_domains", "map_dependencies")
        workflow.add_edge("map_dependencies", "analyze_cascading")
        workflow.add_edge("analyze_cascading", "generate_mitigations")
        workflow.add_edge("generate_mitigations", "create_coordination")
        workflow.add_edge("create_coordination", END)

        return workflow.compile()

    def analyze_cross_domain_impact(
        self,
        event_type: str,
        affected_product: str,
        severity: str = "medium",
        description: str = ""
    ) -> CrossDomainState:
        """
        Analyze cross-domain impact of an event.

        Args:
            event_type: Type of event (incident, change, deprecation)
            affected_product: Primary affected data product
            severity: Event severity
            description: Event description

        Returns:
            Cross-domain analysis results
        """
        initial_state: CrossDomainState = {
            "trigger_event": {
                "type": event_type,
                "product": affected_product,
                "severity": severity,
                "description": description,
                "timestamp": datetime.now(UTC).isoformat()
            },
            "affected_domains": [],
            "domain_products": {},
            "cross_domain_dependencies": [],
            "impact_by_domain": {},
            "cascading_effects": [],
            "mitigation_by_domain": {},
            "coordination_plan": None,
            "executive_summary": None,
            "messages": [f"Starting cross-domain analysis for {event_type} on {affected_product}"]
        }

        return self.workflow.invoke(initial_state)

    def _identify_affected_domains(self, state: CrossDomainState) -> CrossDomainState:
        """Identify all business domains affected by the event."""
        event = state["trigger_event"]
        affected_domains = []
        domain_products = {}

        if self.graph_manager:
            try:
                # Find the primary product and its domain
                result = self.graph_manager.execute_query(
                    """
                    MATCH (dp:DataProduct {name: $product_name})
                    OPTIONAL MATCH (dp)-[:BELONGS_TO]->(d:Domain)
                    OPTIONAL MATCH (downstream:DataProduct)-[:CONSUMES_FROM*1..3]->(dp)
                    OPTIONAL MATCH (downstream)-[:BELONGS_TO]->(dd:Domain)
                    RETURN d.name as primary_domain,
                           collect(DISTINCT dd.name) as downstream_domains,
                           collect(DISTINCT downstream) as downstream_products
                    """,
                    {"product_name": event["product"]}
                )

                if result:
                    primary_domain = result[0].get("primary_domain")
                    if primary_domain:
                        affected_domains.append(primary_domain)

                    downstream_domains = result[0].get("downstream_domains", [])
                    affected_domains.extend([d for d in downstream_domains if d])

                    # Group products by domain
                    for product in result[0].get("downstream_products", []):
                        if product:
                            product_dict = dict(product)
                            domain = product_dict.get("domain", "Unknown")
                            if domain not in domain_products:
                                domain_products[domain] = []
                            domain_products[domain].append(product_dict)

            except Exception as e:
                logger.error(f"Failed to identify domains: {e}")

        # Fallback: infer domains from product name
        if not affected_domains:
            product_lower = event["product"].lower()
            domain_keywords = {
                "Sales": ["sales", "order", "customer", "revenue"],
                "Marketing": ["campaign", "marketing", "lead", "promotion"],
                "Operations": ["inventory", "shipping", "fulfillment", "warehouse"],
                "Finance": ["payment", "invoice", "billing", "accounting"],
                "Analytics": ["report", "dashboard", "metric", "kpi"]
            }

            for domain, keywords in domain_keywords.items():
                if any(kw in product_lower for kw in keywords):
                    affected_domains.append(domain)

            if not affected_domains:
                affected_domains = ["Operations"]  # Default

        state["affected_domains"] = list(set(affected_domains))
        state["domain_products"] = domain_products
        state["messages"].append(
            f"Identified {len(state['affected_domains'])} affected domains: "
            f"{', '.join(state['affected_domains'])}"
        )

        return state

    def _map_cross_domain_dependencies(self, state: CrossDomainState) -> CrossDomainState:
        """Map dependencies between domains."""
        dependencies = []
        domains = state["affected_domains"]

        if self.graph_manager and len(domains) > 1:
            try:
                result = self.graph_manager.execute_query(
                    """
                    MATCH (d1:Domain)<-[:BELONGS_TO]-(dp1:DataProduct)
                    MATCH (d2:Domain)<-[:BELONGS_TO]-(dp2:DataProduct)
                    MATCH (dp2)-[:CONSUMES_FROM]->(dp1)
                    WHERE d1.name IN $domains AND d2.name IN $domains AND d1 <> d2
                    RETURN d1.name as source_domain, d2.name as target_domain,
                           dp1.name as source_product, dp2.name as target_product,
                           count(*) as dependency_count
                    """,
                    {"domains": domains}
                )

                for row in result:
                    dependencies.append({
                        "source_domain": row.get("source_domain"),
                        "target_domain": row.get("target_domain"),
                        "source_product": row.get("source_product"),
                        "target_product": row.get("target_product"),
                        "strength": row.get("dependency_count", 1)
                    })

            except Exception as e:
                logger.error(f"Failed to map dependencies: {e}")

        # Use LLM to enrich understanding
        if self._llm and domains:
            prompt = f"""Analyze cross-domain dependencies for these business domains:

DOMAINS: {', '.join(domains)}

TRIGGER EVENT: {json.dumps(state['trigger_event'], indent=2)}

KNOWN DEPENDENCIES: {json.dumps(dependencies, indent=2)}

Identify additional implicit dependencies between these domains that might not be captured in data lineage.
Consider:
1. Business process dependencies
2. Shared reference data
3. Timing/scheduling dependencies
4. Regulatory/compliance linkages

Return a JSON array of additional dependencies:
[
    {{
        "source_domain": "domain name",
        "target_domain": "domain name",
        "dependency_type": "type (business_process|shared_data|timing|compliance)",
        "description": "explanation",
        "criticality": "high|medium|low"
    }}
]
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are a business analyst expert in cross-functional dependencies."
                )

                if response.success and response.content:
                    json_match = response.content[
                        response.content.find("["):response.content.rfind("]")+1
                    ]
                    additional = json.loads(json_match)
                    dependencies.extend(additional)

            except Exception as e:
                logger.warning(f"LLM dependency analysis failed: {e}")

        state["cross_domain_dependencies"] = dependencies
        state["messages"].append(
            f"Mapped {len(dependencies)} cross-domain dependencies"
        )

        return state

    def _analyze_cascading_effects(self, state: CrossDomainState) -> CrossDomainState:
        """Analyze cascading effects across domains using LLM."""
        cascading_effects = []
        impact_by_domain = {}

        event = state["trigger_event"]
        domains = state["affected_domains"]
        dependencies = state["cross_domain_dependencies"]

        if self._llm:
            prompt = f"""Analyze cascading effects of this event across business domains:

EVENT:
{json.dumps(event, indent=2)}

AFFECTED DOMAINS: {', '.join(domains)}

CROSS-DOMAIN DEPENDENCIES:
{json.dumps(dependencies, indent=2)}

For each affected domain, analyze:
1. Direct impact from the event
2. Indirect/cascading impacts from other domains
3. Business process disruptions
4. Customer-facing effects
5. Revenue/cost implications

Return a JSON object:
{{
    "cascading_effects": [
        {{
            "sequence": 1,
            "from_domain": "source",
            "to_domain": "target",
            "effect": "description of cascading effect",
            "timeline": "immediate|hours|days",
            "severity": "high|medium|low"
        }}
    ],
    "impact_by_domain": {{
        "DomainName": {{
            "direct_impact": "description",
            "indirect_impacts": ["list of indirect impacts"],
            "affected_processes": ["list of business processes"],
            "customer_impact": "description or null",
            "estimated_severity": "high|medium|low"
        }}
    }}
}}
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are a business continuity expert analyzing cross-functional impacts."
                )

                if response.success and response.content:
                    json_match = response.content[
                        response.content.find("{"):response.content.rfind("}")+1
                    ]
                    data = json.loads(json_match)
                    cascading_effects = data.get("cascading_effects", [])
                    impact_by_domain = data.get("impact_by_domain", {})

            except Exception as e:
                logger.warning(f"LLM cascading analysis failed: {e}")

        # Fallback analysis
        if not impact_by_domain:
            severity_map = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}
            base_severity = severity_map.get(event.get("severity", "medium"), "medium")

            for domain in domains:
                impact_by_domain[domain] = {
                    "direct_impact": f"Potential disruption to {domain} operations",
                    "indirect_impacts": [f"Downstream effects from {dep['source_domain']}"
                                         for dep in dependencies
                                         if dep.get("target_domain") == domain],
                    "affected_processes": [f"{domain} data processing"],
                    "customer_impact": "Under assessment",
                    "estimated_severity": base_severity
                }

        state["cascading_effects"] = cascading_effects
        state["impact_by_domain"] = impact_by_domain
        state["messages"].append(
            f"Analyzed {len(cascading_effects)} cascading effects across "
            f"{len(impact_by_domain)} domains"
        )

        return state

    def _generate_domain_mitigations(self, state: CrossDomainState) -> CrossDomainState:
        """Generate mitigation strategies per domain."""
        mitigation_by_domain = {}
        impact_by_domain = state["impact_by_domain"]

        if self._llm:
            prompt = f"""Generate mitigation strategies for each affected domain:

IMPACT BY DOMAIN:
{json.dumps(impact_by_domain, indent=2)}

CASCADING EFFECTS:
{json.dumps(state["cascading_effects"], indent=2)}

For each domain, provide specific, actionable mitigation steps.
Consider:
1. Immediate containment actions
2. Communication requirements
3. Workarounds and fallback procedures
4. Recovery steps
5. Prevention measures for the future

Return a JSON object:
{{
    "DomainName": [
        "Step 1: immediate action",
        "Step 2: containment",
        "Step 3: communication",
        "Step 4: recovery"
    ]
}}
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are an incident response specialist creating mitigation plans."
                )

                if response.success and response.content:
                    json_match = response.content[
                        response.content.find("{"):response.content.rfind("}")+1
                    ]
                    mitigation_by_domain = json.loads(json_match)

            except Exception as e:
                logger.warning(f"LLM mitigation generation failed: {e}")

        # Fallback mitigations
        if not mitigation_by_domain:
            for domain in state["affected_domains"]:
                mitigation_by_domain[domain] = [
                    f"Assess current {domain} operations status",
                    f"Notify {domain} team leads",
                    f"Identify critical {domain} processes",
                    "Implement temporary workarounds if available",
                    "Monitor for additional issues"
                ]

        state["mitigation_by_domain"] = mitigation_by_domain
        state["messages"].append(
            f"Generated mitigation strategies for {len(mitigation_by_domain)} domains"
        )

        return state

    def _create_coordination_plan(self, state: CrossDomainState) -> CrossDomainState:
        """Create a cross-domain coordination plan."""
        if self._llm:
            prompt = f"""Create a cross-domain coordination plan for this incident:

EVENT: {json.dumps(state["trigger_event"], indent=2)}

AFFECTED DOMAINS: {', '.join(state["affected_domains"])}

IMPACT BY DOMAIN: {json.dumps(state["impact_by_domain"], indent=2)}

MITIGATION BY DOMAIN: {json.dumps(state["mitigation_by_domain"], indent=2)}

Create a comprehensive coordination plan that includes:
1. Command structure and escalation paths
2. Communication protocol between domains
3. Synchronized timeline of actions
4. Resource sharing requirements
5. Status reporting cadence
6. Success criteria and handoff points

Write a clear, actionable coordination plan.
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are an incident commander creating cross-functional coordination plans."
                )

                if response.success and response.content:
                    state["coordination_plan"] = response.content

                    # Also generate executive summary
                    summary_response = self._llm.invoke(
                        f"Write a 3-4 sentence executive summary of this situation:\n{response.content}",
                        system_prompt="Write concise executive summaries."
                    )

                    if summary_response.success:
                        state["executive_summary"] = summary_response.content

            except Exception as e:
                logger.warning(f"LLM coordination plan failed: {e}")

        # Fallback plan
        if not state["coordination_plan"]:
            domains = state["affected_domains"]
            plan_parts = [
                "# Cross-Domain Coordination Plan",
                "",
                "## Immediate Actions",
                "1. Establish cross-domain incident channel",
                "2. Assign domain leads for coordination",
                "",
                "## Domain Responsibilities",
            ]

            for domain in domains:
                mitigations = state["mitigation_by_domain"].get(domain, [])
                plan_parts.append(f"\n### {domain}")
                for m in mitigations[:3]:
                    plan_parts.append(f"- {m}")

            plan_parts.extend([
                "",
                "## Status Reporting",
                "- Updates every 30 minutes during active incident",
                "- Domain leads report to incident commander",
                "",
                "## Recovery Criteria",
                "- All domains confirm normal operations",
                "- No new cascading effects detected"
            ])

            state["coordination_plan"] = "\n".join(plan_parts)
            state["executive_summary"] = (
                f"Cross-domain incident affecting {len(domains)} domains. "
                f"Coordination plan established with domain-specific mitigations."
            )

        state["messages"].append("Cross-domain coordination plan created")
        return state


# Factory function
def create_cross_domain_agent(graph_manager=None) -> CrossDomainImpactAgent:
    """Create a cross-domain impact agent instance."""
    return CrossDomainImpactAgent(graph_manager)
