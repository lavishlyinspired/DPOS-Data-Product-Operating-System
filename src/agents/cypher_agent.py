"""
Cypher Query Generation Agent
Uses LangGraph to translate natural language questions into Cypher queries.
"""
import os
from typing import TypedDict, List, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_ollama import OllamaLLM
import re

from dotenv import load_dotenv

load_dotenv()

from src.graph.manager import Neo4jManager
from src.ontology.loader import get_ontology
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger


# ============================================================================
# STATE DEFINITION
# ============================================================================

class CypherAgentState(TypedDict):
    """State for the Cypher generation agent."""
    question: str
    ontology_context: str
    intent: str
    entities: List[str]
    generated_cypher: str
    is_valid: bool
    validation_error: str
    query_result: List[dict]
    natural_answer: str
    confidence: float
    status: str


# ============================================================================
# PROMPTS
# ============================================================================

CYPHER_SYSTEM_PROMPT = """You are a Cypher query expert for the DPOS (Data Product Operating System) knowledge graph.

Your task is to convert natural language questions into valid Cypher queries.

{ontology_context}

## Query Guidelines

1. Always use parameterized queries for user-provided values when possible
2. Use OPTIONAL MATCH for properties that may not exist
3. Limit results to 100 unless aggregating
4. Use meaningful aliases in RETURN clauses
5. Include ORDER BY for list queries
6. Use DISTINCT when traversing multiple paths
7. Never use destructive operations (DELETE, REMOVE, SET) - only read queries

## Common Patterns

### Counting with filters
MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
WHERE i.status = 'open'
RETURN count(DISTINCT p) as affected_products

### Multi-hop lineage
MATCH path = (start:DataProduct {{id: $id}})-[:CONSUMES_FROM*1..5]->(end)
WHERE NOT (end)-[:CONSUMES_FROM]->()
RETURN path

### Aggregation with grouping
MATCH (p:DataProduct)-[:IN_DOMAIN]->(d:Domain)
OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {{status: 'open'}})
RETURN d.name, count(DISTINCT p) as products, count(i) as open_incidents
ORDER BY open_incidents DESC

## Response Format

Return ONLY the Cypher query, no explanations or markdown.
If the question cannot be answered with the available schema, return:
// UNABLE: [reason]
"""


ANSWER_GENERATION_PROMPT = """Based on the query results, provide a natural language answer to the question.

Question: {question}

Query Results:
{results}

Provide a clear, concise answer. If no results were found, say so. Include relevant numbers and names from the results.
"""


# ============================================================================
# TOOLS
# ============================================================================

@tool
def execute_cypher(query: str, parameters: dict = None) -> dict:
    """
    Execute a Cypher query against the DPOS Neo4j database.
    Only SELECT/MATCH queries are allowed - no mutations.

    Args:
        query: Valid Cypher query string (read-only)
        parameters: Optional parameter dict for parameterized queries

    Returns:
        dict with 'results' list and 'metadata' about query execution
    """
    # Safety check - no mutations allowed
    query_upper = query.upper()
    forbidden = ['DELETE', 'REMOVE', 'SET ', 'CREATE', 'MERGE', 'DROP']
    for word in forbidden:
        if word in query_upper:
            return {
                "error": f"Mutation operations ({word}) are not allowed",
                "results": []
            }

    with Neo4jManager() as mgr:
        try:
            results = mgr.execute_query(query, parameters or {})
            return {
                "results": [dict(r) for r in results],
                "count": len(results),
                "error": None
            }
        except Exception as e:
            return {
                "error": str(e),
                "results": []
            }


# ============================================================================
# AGENT NODES
# ============================================================================

def build_cypher_agent():
    """Build the Cypher generation agent with LangGraph."""
    log = get_agent_logger("CypherAgent")
    ontology = get_ontology()

    # Initialize LLM - try Ollama first (configured via environment variables)
    try:
        llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    except Exception:
        llm = None
        log.warning("Ollama not available, using template-based generation")

    def parse_question(state: CypherAgentState) -> CypherAgentState:
        """Parse the question to extract intent and entities."""
        log.info(f"Parsing question: {state['question']}")

        question_lower = state["question"].lower()

        # Intent classification
        if any(w in question_lower for w in ["how many", "count", "number of"]):
            intent = "count"
        elif any(w in question_lower for w in ["list", "show", "find", "what are"]):
            intent = "list"
        elif any(w in question_lower for w in ["lineage", "upstream", "downstream", "depends"]):
            intent = "lineage"
        elif any(w in question_lower for w in ["impact", "affected", "consumers"]):
            intent = "impact"
        elif any(w in question_lower for w in ["health", "status", "quality"]):
            intent = "health"
        else:
            intent = "general"

        # Entity extraction (simple keyword matching)
        entities = []
        node_types = ontology.get_node_types()
        for node_type in node_types:
            if node_type.lower() in question_lower:
                entities.append(node_type)

        # Check for specific entity names
        entity_patterns = [
            r'"([^"]+)"',  # Quoted strings
            r"'([^']+)'",  # Single quoted
            r"DP\d+",      # Product IDs
            r"INC_\w+",    # Incident IDs
        ]
        for pattern in entity_patterns:
            matches = re.findall(pattern, state["question"])
            entities.extend(matches)

        return {
            **state,
            "intent": intent,
            "entities": entities,
            "ontology_context": ontology.to_llm_context(),
            "status": "parsed"
        }

    def generate_cypher(state: CypherAgentState) -> CypherAgentState:
        """Generate Cypher query from the question."""
        log.info(f"Generating Cypher for intent: {state['intent']}")

        question = state["question"]
        intent = state["intent"]
        entities = state.get("entities", [])

        # Template-based generation for common patterns
        cypher = _generate_cypher_template(question, intent, entities)

        if cypher:
            log.info(f"Generated via template: {cypher[:100]}...")
        elif llm:
            # Use LLM for complex queries
            prompt = CYPHER_SYSTEM_PROMPT.format(
                ontology_context=state.get("ontology_context", "")
            )
            try:
                response = llm.invoke(f"{prompt}\n\nQuestion: {question}")
                cypher = response.strip()
                # Clean up response
                if cypher.startswith("```"):
                    cypher = cypher.split("```")[1]
                    if cypher.startswith("cypher"):
                        cypher = cypher[6:]
                cypher = cypher.strip()
            except Exception as e:
                log.error(f"LLM generation failed: {e}")
                cypher = "// UNABLE: LLM generation failed"
        else:
            cypher = "// UNABLE: No generation method available"

        return {
            **state,
            "generated_cypher": cypher,
            "status": "generated"
        }

    def validate_cypher(state: CypherAgentState) -> CypherAgentState:
        """Validate the generated Cypher query."""
        log.info("Validating Cypher query")

        cypher = state.get("generated_cypher", "")

        # Check for UNABLE marker
        if cypher.startswith("// UNABLE"):
            return {
                **state,
                "is_valid": False,
                "validation_error": cypher.replace("// UNABLE:", "").strip(),
                "confidence": 0.0,
                "status": "invalid"
            }

        # Basic syntax validation
        errors = []

        # Check for balanced parentheses
        if cypher.count("(") != cypher.count(")"):
            errors.append("Unbalanced parentheses")

        if cypher.count("[") != cypher.count("]"):
            errors.append("Unbalanced brackets")

        if cypher.count("{") != cypher.count("}"):
            errors.append("Unbalanced braces")

        # Check for required clauses
        cypher_upper = cypher.upper()
        if "MATCH" not in cypher_upper and "RETURN" in cypher_upper:
            errors.append("RETURN without MATCH")

        # Safety check - no mutations
        forbidden = ['DELETE', 'REMOVE', 'SET ', 'CREATE', 'MERGE', 'DROP']
        for word in forbidden:
            if word in cypher_upper:
                errors.append(f"Forbidden operation: {word}")

        is_valid = len(errors) == 0

        # Calculate confidence based on query complexity
        confidence = 0.9 if is_valid else 0.0
        if "*" in cypher:  # Variable length paths reduce confidence
            confidence *= 0.9

        return {
            **state,
            "is_valid": is_valid,
            "validation_error": "; ".join(errors) if errors else "",
            "confidence": confidence,
            "status": "validated" if is_valid else "invalid"
        }

    def route_after_validation(state: CypherAgentState) -> Literal["execute", "fallback"]:
        """Route based on validation result."""
        if state.get("is_valid", False):
            return "execute"
        return "fallback"

    def execute_query(state: CypherAgentState) -> CypherAgentState:
        """Execute the validated Cypher query."""
        log.info("Executing Cypher query")

        result = execute_cypher.invoke(state["generated_cypher"])

        if result.get("error"):
            return {
                **state,
                "query_result": [],
                "validation_error": result["error"],
                "status": "execution_failed"
            }

        return {
            **state,
            "query_result": result.get("results", []),
            "status": "executed"
        }

    def generate_answer(state: CypherAgentState) -> CypherAgentState:
        """Generate a natural language answer from the results."""
        log.info("Generating natural language answer")

        results = state.get("query_result", [])
        question = state["question"]

        if not results:
            answer = "I couldn't find any data matching your query."
        elif llm:
            # Use LLM to generate answer
            results_str = str(results[:10])  # Limit for context
            prompt = ANSWER_GENERATION_PROMPT.format(
                question=question,
                results=results_str
            )
            try:
                answer = llm.invoke(prompt).strip()
            except Exception:
                answer = _format_results_simple(results)
        else:
            answer = _format_results_simple(results)

        return {
            **state,
            "natural_answer": answer,
            "status": "completed"
        }

    def handle_fallback(state: CypherAgentState) -> CypherAgentState:
        """Handle cases where query generation failed."""
        log.warning(f"Fallback: {state.get('validation_error', 'Unknown error')}")

        return {
            **state,
            "natural_answer": f"I couldn't generate a valid query for your question. Error: {state.get('validation_error', 'Unknown error')}. Please try rephrasing or ask about specific data products, incidents, or contracts.",
            "query_result": [],
            "status": "fallback"
        }

    # Build the graph
    graph = StateGraph(CypherAgentState)

    graph.add_node("parse", parse_question)
    graph.add_node("generate", generate_cypher)
    graph.add_node("validate", validate_cypher)
    graph.add_node("execute", execute_query)
    graph.add_node("answer", generate_answer)
    graph.add_node("fallback", handle_fallback)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "generate")
    graph.add_edge("generate", "validate")

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "execute": "execute",
            "fallback": "fallback"
        }
    )

    graph.add_edge("execute", "answer")
    graph.add_edge("answer", END)
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=get_checkpointer())


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _generate_cypher_template(question: str, intent: str, entities: List[str]) -> Optional[str]:
    """Generate Cypher from templates for common query patterns."""
    question_lower = question.lower()

    # Count products
    if intent == "count" and "product" in question_lower:
        if "domain" in question_lower:
            return """
MATCH (p:DataProduct)-[:IN_DOMAIN]->(d:Domain)
RETURN d.name as domain, count(p) as product_count
ORDER BY product_count DESC
"""
        elif "incident" in question_lower or "open" in question_lower:
            return """
MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
RETURN count(DISTINCT p) as products_with_incidents
"""
        else:
            return "MATCH (p:DataProduct) RETURN count(p) as total_products"

    # List products
    if intent == "list" and "product" in question_lower:
        if "active" in question_lower:
            return """
MATCH (p:DataProduct {status: 'active'})
RETURN p.id, p.name, p.owner, p.type
ORDER BY p.name
LIMIT 50
"""
        else:
            return """
MATCH (p:DataProduct)
RETURN p.id, p.name, p.status, p.owner
ORDER BY p.name
LIMIT 50
"""

    # Incidents
    if "incident" in question_lower:
        if "critical" in question_lower or "open" in question_lower:
            return """
MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
WHERE i.status = 'open'
RETURN p.name as product, i.id, i.severity, i.description, i.created_at
ORDER BY
  CASE i.severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    ELSE 4
  END
LIMIT 20
"""

    # Lineage
    if intent == "lineage":
        # Check for specific product
        for entity in entities:
            if entity.startswith("DP") or "product" in entity.lower():
                return f"""
MATCH path = (p:DataProduct {{id: '{entity}'}})-[:CONSUMES_FROM*0..5]->(source)
RETURN p.name as product,
       [n in nodes(path) | n.name] as lineage_path,
       length(path) as depth
ORDER BY depth
"""

        return """
MATCH (p:DataProduct)-[:CONSUMES_FROM]->(source:DataProduct)
RETURN p.name as consumer, source.name as source
ORDER BY p.name
LIMIT 50
"""

    # Health/Dashboard
    if intent == "health":
        return """
MATCH (p:DataProduct)
OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
WITH p, count(i) as open_incidents
RETURN
  count(p) as total_products,
  sum(CASE WHEN open_incidents = 0 THEN 1 ELSE 0 END) as healthy,
  sum(CASE WHEN open_incidents > 0 THEN 1 ELSE 0 END) as degraded
"""

    # Contracts
    if "contract" in question_lower:
        return """
MATCH (p:DataProduct)-[:HAS_CONTRACT]->(c:Contract)
WHERE c.is_active = true
OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule {enabled: true})
RETURN p.name as product, c.id as contract, count(r) as rules
ORDER BY rules DESC
LIMIT 30
"""

    # Domains
    if "domain" in question_lower:
        return """
MATCH (d:Domain)
OPTIONAL MATCH (d)<-[:IN_DOMAIN]-(p:DataProduct)
RETURN d.name, d.owner, count(p) as products
ORDER BY products DESC
"""

    return None


def _format_results_simple(results: List[dict]) -> str:
    """Format results into a simple readable answer."""
    if not results:
        return "No results found."

    if len(results) == 1:
        result = results[0]
        if len(result) == 1:
            key, value = list(result.items())[0]
            return f"The {key} is {value}."
        parts = [f"{k}: {v}" for k, v in result.items()]
        return "Result: " + ", ".join(parts)

    # Multiple results
    lines = [f"Found {len(results)} results:"]
    for i, result in enumerate(results[:10], 1):
        parts = [f"{k}: {v}" for k, v in result.items()]
        lines.append(f"  {i}. " + ", ".join(parts))

    if len(results) > 10:
        lines.append(f"  ... and {len(results) - 10} more")

    return "\n".join(lines)
