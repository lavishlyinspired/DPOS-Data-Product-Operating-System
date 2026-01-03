"""
Contract Evolution Agent
Intelligent agent for managing and evolving data contracts over time.
Uses LLM to analyze contract effectiveness and suggest improvements.
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


class ContractEvolutionState(TypedDict):
    """State for contract evolution workflow."""
    contract_id: str
    contract_details: Optional[Dict]
    violation_history: List[Dict]
    related_contracts: List[Dict]
    effectiveness_score: float
    evolution_recommendations: List[Dict]
    threshold_adjustments: List[Dict]
    new_rule_suggestions: List[Dict]
    deprecation_candidates: List[str]
    stakeholder_impact: Optional[str]
    evolution_plan: Optional[str]
    messages: Annotated[List[str], operator.add]


class ContractEvolutionAgent:
    """
    Agent that intelligently evolves data contracts based on:
    - Historical violation patterns
    - Business context changes
    - Industry best practices
    - Stakeholder feedback
    """

    def __init__(self, graph_manager=None):
        self.graph_manager = graph_manager
        self._llm = None

        if LLM_AVAILABLE:
            try:
                config = LLMConfig()
                self._llm = UnifiedLLM(config)
                logger.info("ContractEvolutionAgent initialized with LLM support")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")

        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the contract evolution workflow."""
        workflow = StateGraph(ContractEvolutionState)

        # Add nodes
        workflow.add_node("load_contract", self._load_contract)
        workflow.add_node("analyze_violations", self._analyze_violations)
        workflow.add_node("assess_effectiveness", self._assess_effectiveness)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("plan_evolution", self._plan_evolution)

        # Define edges
        workflow.set_entry_point("load_contract")
        workflow.add_edge("load_contract", "analyze_violations")
        workflow.add_edge("analyze_violations", "assess_effectiveness")
        workflow.add_edge("assess_effectiveness", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "plan_evolution")
        workflow.add_edge("plan_evolution", END)

        return workflow.compile()

    def evolve_contract(self, contract_id: str) -> ContractEvolutionState:
        """
        Analyze and evolve a data contract.

        Args:
            contract_id: The contract to evolve

        Returns:
            Evolution analysis and recommendations
        """
        initial_state: ContractEvolutionState = {
            "contract_id": contract_id,
            "contract_details": None,
            "violation_history": [],
            "related_contracts": [],
            "effectiveness_score": 0.0,
            "evolution_recommendations": [],
            "threshold_adjustments": [],
            "new_rule_suggestions": [],
            "deprecation_candidates": [],
            "stakeholder_impact": None,
            "evolution_plan": None,
            "messages": [f"Starting contract evolution analysis for {contract_id}"]
        }

        return self.workflow.invoke(initial_state)

    def _load_contract(self, state: ContractEvolutionState) -> ContractEvolutionState:
        """Load contract details and related information."""
        contract_id = state["contract_id"]

        # Load contract from graph
        contract_details = None
        related_contracts = []
        violation_history = []

        if self.graph_manager:
            try:
                # Get contract details
                result = self.graph_manager.execute_query(
                    """
                    MATCH (c:Contract {id: $contract_id})
                    OPTIONAL MATCH (c)-[:APPLIES_TO]->(dp:DataProduct)
                    OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
                    RETURN c, collect(DISTINCT dp) as products, collect(DISTINCT r) as rules
                    """,
                    {"contract_id": contract_id}
                )

                if result:
                    contract_details = {
                        "contract": dict(result[0].get("c", {})),
                        "products": [dict(p) for p in result[0].get("products", [])],
                        "rules": [dict(r) for r in result[0].get("rules", [])]
                    }

                # Get violation history
                violations = self.graph_manager.execute_query(
                    """
                    MATCH (c:Contract {id: $contract_id})-[:HAS_RULE]->(r:Rule)
                    MATCH (i:Incident)-[:VIOLATES]->(r)
                    RETURN i, r
                    ORDER BY i.created_at DESC
                    LIMIT 50
                    """,
                    {"contract_id": contract_id}
                )
                violation_history = [
                    {"incident": dict(v.get("i", {})), "rule": dict(v.get("r", {}))}
                    for v in violations
                ]

                # Get related contracts
                related = self.graph_manager.execute_query(
                    """
                    MATCH (c:Contract {id: $contract_id})-[:APPLIES_TO]->(dp:DataProduct)
                    MATCH (other:Contract)-[:APPLIES_TO]->(dp)
                    WHERE other.id <> $contract_id
                    RETURN DISTINCT other
                    """,
                    {"contract_id": contract_id}
                )
                related_contracts = [dict(r.get("other", {})) for r in related]

            except Exception as e:
                logger.error(f"Failed to load contract data: {e}")
                state["messages"].append(f"Error loading contract: {e}")

        # For demo/fallback
        if not contract_details:
            contract_details = {
                "contract": {
                    "id": contract_id,
                    "name": f"Contract {contract_id}",
                    "version": "1.0",
                    "created_at": "2024-01-01"
                },
                "products": [],
                "rules": [
                    {"id": "rule_1", "type": "null_rate", "threshold": 0.05},
                    {"id": "rule_2", "type": "freshness", "max_age_hours": 24}
                ]
            }

        state["contract_details"] = contract_details
        state["related_contracts"] = related_contracts
        state["violation_history"] = violation_history
        state["messages"].append(
            f"Loaded contract with {len(contract_details.get('rules', []))} rules "
            f"and {len(violation_history)} historical violations"
        )

        return state

    def _analyze_violations(self, state: ContractEvolutionState) -> ContractEvolutionState:
        """Analyze violation patterns to identify systemic issues."""
        violations = state["violation_history"]
        contract = state["contract_details"]

        if not violations:
            state["messages"].append("No violation history to analyze")
            return state

        # Count violations by rule
        rule_violations = {}
        for v in violations:
            rule_id = v.get("rule", {}).get("id", "unknown")
            rule_violations[rule_id] = rule_violations.get(rule_id, 0) + 1

        # Identify problematic rules (high violation rate)
        threshold_adjustments = []
        deprecation_candidates = []

        for rule_id, count in rule_violations.items():
            if count > 10:  # Frequent violations
                # Find the rule details
                rule_detail = next(
                    (r for r in contract.get("rules", []) if r.get("id") == rule_id),
                    {}
                )

                if count > 20:
                    # Consider deprecating or major revision
                    deprecation_candidates.append(rule_id)
                else:
                    # Suggest threshold adjustment
                    threshold_adjustments.append({
                        "rule_id": rule_id,
                        "current_threshold": rule_detail.get("threshold"),
                        "violation_count": count,
                        "suggestion": "Consider relaxing threshold or providing exceptions"
                    })

        state["threshold_adjustments"] = threshold_adjustments
        state["deprecation_candidates"] = deprecation_candidates
        state["messages"].append(
            f"Analyzed {len(violations)} violations. "
            f"Found {len(threshold_adjustments)} rules needing adjustment, "
            f"{len(deprecation_candidates)} deprecation candidates"
        )

        return state

    def _assess_effectiveness(self, state: ContractEvolutionState) -> ContractEvolutionState:
        """Assess overall contract effectiveness using LLM."""
        contract = state["contract_details"]
        violations = state["violation_history"]
        adjustments = state["threshold_adjustments"]

        # Calculate base effectiveness score
        total_rules = len(contract.get("rules", []))
        problematic_rules = len(adjustments) + len(state["deprecation_candidates"])

        if total_rules > 0:
            base_score = 1.0 - (problematic_rules / total_rules)
        else:
            base_score = 0.5

        # Adjust for violation frequency
        if violations:
            violation_rate = len(violations) / max(total_rules, 1)
            base_score = base_score * (1 - min(violation_rate / 10, 0.5))

        state["effectiveness_score"] = round(base_score, 2)

        # Use LLM for deeper analysis
        if self._llm and contract:
            prompt = f"""Analyze this data contract's effectiveness:

CONTRACT:
{json.dumps(contract, indent=2, default=str)}

VIOLATION SUMMARY:
- Total violations: {len(violations)}
- Rules with frequent violations: {len(adjustments)}
- Rules considered for deprecation: {len(state["deprecation_candidates"])}

Current effectiveness score: {state["effectiveness_score"]}

Assess the contract and provide:
1. Key strengths of the current contract
2. Critical weaknesses or gaps
3. Industry best practices that could be applied
4. Overall health assessment

Return a JSON object:
{{
    "strengths": ["list of strengths"],
    "weaknesses": ["list of weaknesses"],
    "best_practices": ["applicable best practices"],
    "health_assessment": "overall assessment paragraph",
    "adjusted_score": 0.0-1.0
}}
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are a data governance expert specializing in data contracts and quality rules."
                )

                if response.success and response.content:
                    json_match = json.loads(
                        response.content[response.content.find("{"):response.content.rfind("}")+1]
                    )
                    if "adjusted_score" in json_match:
                        state["effectiveness_score"] = json_match["adjusted_score"]
                    state["messages"].append(
                        f"LLM assessment: {json_match.get('health_assessment', 'Assessment complete')[:200]}"
                    )

            except Exception as e:
                logger.warning(f"LLM effectiveness assessment failed: {e}")

        state["messages"].append(f"Contract effectiveness score: {state['effectiveness_score']}")
        return state

    def _generate_recommendations(self, state: ContractEvolutionState) -> ContractEvolutionState:
        """Generate evolution recommendations using LLM."""
        recommendations = []
        new_rule_suggestions = []

        contract = state["contract_details"]
        violations = state["violation_history"]
        effectiveness = state["effectiveness_score"]

        # Generate recommendations with LLM
        if self._llm:
            prompt = f"""Based on this contract analysis, generate evolution recommendations:

CONTRACT DETAILS:
{json.dumps(contract, indent=2, default=str)}

ANALYSIS RESULTS:
- Effectiveness score: {effectiveness}
- Threshold adjustments needed: {json.dumps(state["threshold_adjustments"], indent=2)}
- Deprecation candidates: {state["deprecation_candidates"]}
- Recent violation count: {len(violations)}

Generate specific, actionable recommendations for evolving this contract.
Consider:
1. Rule threshold adjustments with specific new values
2. New rules that should be added based on gaps
3. Rules that should be deprecated or consolidated
4. Stakeholder communication needs
5. Migration strategy for changes

Return a JSON object:
{{
    "recommendations": [
        {{
            "type": "threshold_adjustment|new_rule|deprecation|consolidation",
            "priority": "high|medium|low",
            "description": "detailed description",
            "implementation": "how to implement",
            "risk": "potential risks"
        }}
    ],
    "new_rules": [
        {{
            "name": "rule name",
            "type": "rule type",
            "threshold": "suggested threshold",
            "rationale": "why this rule is needed"
        }}
    ],
    "stakeholder_impact": "paragraph describing impact on stakeholders"
}}
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are a data governance strategist. Generate practical, implementable recommendations for contract evolution."
                )

                if response.success and response.content:
                    json_match = response.content[
                        response.content.find("{"):response.content.rfind("}")+1
                    ]
                    data = json.loads(json_match)

                    recommendations = data.get("recommendations", [])
                    new_rule_suggestions = data.get("new_rules", [])
                    state["stakeholder_impact"] = data.get("stakeholder_impact")

            except Exception as e:
                logger.warning(f"LLM recommendation generation failed: {e}")

        # Fallback recommendations if LLM failed
        if not recommendations:
            for adj in state["threshold_adjustments"]:
                recommendations.append({
                    "type": "threshold_adjustment",
                    "priority": "medium",
                    "description": f"Adjust threshold for rule {adj['rule_id']}",
                    "implementation": "Review current threshold and adjust based on violation patterns",
                    "risk": "May allow some previously caught issues through"
                })

            for dep in state["deprecation_candidates"]:
                recommendations.append({
                    "type": "deprecation",
                    "priority": "high",
                    "description": f"Consider deprecating or replacing rule {dep}",
                    "implementation": "Review rule effectiveness and stakeholder needs",
                    "risk": "Loss of quality checks if not properly replaced"
                })

        state["evolution_recommendations"] = recommendations
        state["new_rule_suggestions"] = new_rule_suggestions
        state["messages"].append(
            f"Generated {len(recommendations)} recommendations and "
            f"{len(new_rule_suggestions)} new rule suggestions"
        )

        return state

    def _plan_evolution(self, state: ContractEvolutionState) -> ContractEvolutionState:
        """Create a comprehensive evolution plan."""
        recommendations = state["evolution_recommendations"]
        contract = state["contract_details"]

        if not recommendations:
            state["evolution_plan"] = "No evolution needed at this time."
            state["messages"].append("Contract appears healthy, no evolution plan created")
            return state

        # Use LLM to create comprehensive plan
        if self._llm:
            prompt = f"""Create a comprehensive contract evolution plan:

CONTRACT: {contract.get('contract', {}).get('name', 'Unknown')}
VERSION: {contract.get('contract', {}).get('version', '1.0')}

RECOMMENDATIONS:
{json.dumps(recommendations, indent=2)}

NEW RULES SUGGESTED:
{json.dumps(state["new_rule_suggestions"], indent=2)}

STAKEHOLDER IMPACT:
{state.get("stakeholder_impact", "Not assessed")}

Create a detailed evolution plan that includes:
1. Executive summary
2. Phase-by-phase implementation approach
3. Risk mitigation strategies
4. Rollback procedures
5. Success metrics
6. Communication plan

Write the plan in a clear, professional format suitable for stakeholder review.
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are a technical program manager creating implementation plans. Write clear, actionable plans."
                )

                if response.success and response.content:
                    state["evolution_plan"] = response.content

            except Exception as e:
                logger.warning(f"LLM plan generation failed: {e}")

        # Fallback plan
        if not state["evolution_plan"]:
            high_priority = [r for r in recommendations if r.get("priority") == "high"]
            medium_priority = [r for r in recommendations if r.get("priority") == "medium"]

            plan_parts = [
                f"# Contract Evolution Plan for {contract.get('contract', {}).get('name', 'Unknown')}",
                "",
                "## Phase 1: High Priority Changes",
                *[f"- {r['description']}" for r in high_priority],
                "",
                "## Phase 2: Medium Priority Changes",
                *[f"- {r['description']}" for r in medium_priority],
                "",
                "## New Rules to Implement",
                *[f"- {r['name']}: {r['rationale']}" for r in state["new_rule_suggestions"]],
                "",
                "## Next Steps",
                "1. Review this plan with stakeholders",
                "2. Prioritize and schedule implementation",
                "3. Create migration scripts",
                "4. Test in staging environment",
                "5. Deploy with monitoring"
            ]

            state["evolution_plan"] = "\n".join(plan_parts)

        state["messages"].append("Contract evolution plan created")
        return state


# Factory function
def create_contract_evolution_agent(graph_manager=None) -> ContractEvolutionAgent:
    """Create a contract evolution agent instance."""
    return ContractEvolutionAgent(graph_manager)
