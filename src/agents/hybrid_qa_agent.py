"""
Hybrid QA Agent with Graph RAG
Combines semantic search, graph queries, and keyword matching for comprehensive Q&A.
"""
import os
from typing import TypedDict, List, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_ollama import OllamaLLM

from dotenv import load_dotenv

load_dotenv()

from src.graph.manager import Neo4jManager
from src.ontology.loader import get_ontology
from src.rag.intent_classifier import IntentClassifier, QueryIntent
from src.rag.result_fusion import ResultFusion
from src.marketplace.semantic_search import SemanticMarketplace
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger


# ============================================================================
# STATE DEFINITION
# ============================================================================

class HybridQAState(TypedDict):
    """State for the hybrid QA agent."""
    question: str
    intent: str
    confidence: float
    entities: List[str]

    # Results from different sources
    semantic_results: List[dict]
    graph_results: List[dict]
    keyword_results: List[dict]

    # Fused results
    fused_results: List[dict]
    sources_used: List[str]

    # Final output
    answer: str
    citations: List[str]
    generated_cypher: str
    status: str


# ============================================================================
# PROMPTS
# ============================================================================

ANSWER_SYNTHESIS_PROMPT = """You are a data governance expert for the DPOS (Data Product Operating System).

Based on the retrieved information, provide a clear and helpful answer to the user's question.

Question: {question}

Retrieved Information:
{context}

Instructions:
1. Provide a direct answer to the question
2. Include specific names, numbers, and details from the retrieved data
3. If the information is insufficient, say so clearly
4. Keep the answer concise but complete

Answer:"""


# ============================================================================
# AGENT BUILDER
# ============================================================================

def build_hybrid_qa_agent():
    """Build the hybrid QA agent with LangGraph."""
    log = get_agent_logger("HybridQAAgent")
    intent_classifier = IntentClassifier()
    result_fusion = ResultFusion()
    ontology = get_ontology()

    # Initialize LLM (configured via environment variables)
    try:
        llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    except Exception:
        llm = None
        log.warning("Ollama not available, using template-based answers")

    def classify_intent(state: HybridQAState) -> HybridQAState:
        """Classify the question intent."""
        log.info(f"Classifying: {state['question']}")

        classification = intent_classifier.classify(state["question"])

        return {
            **state,
            "intent": classification.primary_intent.value,
            "confidence": classification.confidence,
            "entities": classification.extracted_entities,
            "status": "classified"
        }

    def route_by_intent(state: HybridQAState) -> Literal["semantic", "graph", "keyword", "hybrid"]:
        """Route to appropriate retrieval based on intent."""
        intent = state.get("intent", "hybrid")

        if intent == "semantic":
            return "semantic"
        elif intent == "graph":
            return "graph"
        elif intent == "keyword":
            return "keyword"
        else:
            return "hybrid"

    def semantic_search(state: HybridQAState) -> HybridQAState:
        """Perform semantic search."""
        log.info("Performing semantic search")

        try:
            with SemanticMarketplace() as marketplace:
                results = marketplace.hybrid_search(
                    query=state["question"],
                    limit=10
                )

                # Convert to dict format
                semantic_results = []
                for result in results:
                    semantic_results.append({
                        "id": result.get("id", ""),
                        "name": result.get("name", ""),
                        "description": result.get("description", ""),
                        "type": "semantic_match",
                        "score": result.get("score", 0)
                    })

                return {
                    **state,
                    "semantic_results": semantic_results,
                    "status": "semantic_done"
                }
        except Exception as e:
            log.error(f"Semantic search failed: {e}")
            return {
                **state,
                "semantic_results": [],
                "status": "semantic_failed"
            }

    def graph_query(state: HybridQAState) -> HybridQAState:
        """Perform graph query using Cypher."""
        log.info("Performing graph query")

        question = state["question"]
        entities = state.get("entities", [])

        # Generate Cypher based on question
        cypher = _generate_cypher_for_qa(question, entities)

        if cypher:
            with Neo4jManager() as mgr:
                try:
                    results = mgr.execute_query(cypher)
                    graph_results = [dict(r) for r in results[:20]]

                    return {
                        **state,
                        "graph_results": graph_results,
                        "generated_cypher": cypher,
                        "status": "graph_done"
                    }
                except Exception as e:
                    log.error(f"Graph query failed: {e}")

        return {
            **state,
            "graph_results": [],
            "generated_cypher": cypher or "",
            "status": "graph_failed"
        }

    def keyword_search(state: HybridQAState) -> HybridQAState:
        """Perform keyword/exact match search."""
        log.info("Performing keyword search")

        entities = state.get("entities", [])
        question = state["question"]

        keyword_results = []

        with Neo4jManager() as mgr:
            # Search for specific entities
            for entity in entities:
                # Try product lookup
                q = """
                MATCH (n)
                WHERE n.id = $entity OR n.name CONTAINS $entity
                RETURN labels(n)[0] as type, n.id as id, n.name as name,
                       n.description as description, n.status as status
                LIMIT 5
                """
                try:
                    results = mgr.execute_query(q, {"entity": entity})
                    for r in results:
                        keyword_results.append(dict(r))
                except Exception:
                    pass

            # General keyword search if no entities
            if not entities:
                keywords = [w for w in question.split() if len(w) > 3]
                for keyword in keywords[:3]:
                    q = """
                    MATCH (p:DataProduct)
                    WHERE toLower(p.name) CONTAINS toLower($kw)
                       OR toLower(p.description) CONTAINS toLower($kw)
                    RETURN 'DataProduct' as type, p.id as id, p.name as name,
                           p.description as description
                    LIMIT 3
                    """
                    try:
                        results = mgr.execute_query(q, {"kw": keyword})
                        for r in results:
                            keyword_results.append(dict(r))
                    except Exception:
                        pass

        return {
            **state,
            "keyword_results": keyword_results,
            "status": "keyword_done"
        }

    def hybrid_retrieval(state: HybridQAState) -> HybridQAState:
        """Perform all retrieval methods in parallel (simulated sequentially)."""
        log.info("Performing hybrid retrieval")

        # Run all three methods
        state = semantic_search(state)
        state = graph_query(state)
        state = keyword_search(state)

        return {
            **state,
            "status": "hybrid_done"
        }

    def fuse_results(state: HybridQAState) -> HybridQAState:
        """Fuse results from all sources."""
        log.info("Fusing results")

        fusion_result = result_fusion.fuse(
            semantic_results=state.get("semantic_results", []),
            graph_results=state.get("graph_results", []),
            keyword_results=state.get("keyword_results", [])
        )

        # Extract top results
        fused = []
        for ranked in fusion_result.results[:15]:
            fused.append({
                **ranked.content,
                "_source": ranked.source,
                "_score": ranked.fusion_score
            })

        return {
            **state,
            "fused_results": fused,
            "sources_used": fusion_result.sources_used,
            "status": "fused"
        }

    def generate_answer(state: HybridQAState) -> HybridQAState:
        """Generate natural language answer from fused results."""
        log.info("Generating answer")

        results = state.get("fused_results", [])
        question = state["question"]

        if not results:
            answer = "I couldn't find relevant information to answer your question. Please try rephrasing or ask about specific data products, incidents, or contracts."
            citations = []
        elif llm:
            # Format context
            context_parts = []
            citations = []
            for i, result in enumerate(results[:8], 1):
                source = result.get("_source", "unknown")
                name = result.get("name", result.get("id", f"Result {i}"))

                # Build context entry
                entry = f"[{i}] {name}"
                if result.get("description"):
                    entry += f": {result['description'][:200]}"
                if result.get("status"):
                    entry += f" (Status: {result['status']})"
                if result.get("type"):
                    entry += f" [Type: {result['type']}]"

                context_parts.append(entry)
                citations.append(f"{name} (via {source})")

            context = "\n".join(context_parts)

            # Generate answer with LLM
            try:
                prompt = ANSWER_SYNTHESIS_PROMPT.format(
                    question=question,
                    context=context
                )
                answer = llm.invoke(prompt).strip()
            except Exception as e:
                log.error(f"LLM answer generation failed: {e}")
                answer = _format_simple_answer(results, question)
        else:
            answer = _format_simple_answer(results, question)
            citations = [r.get("name", r.get("id", "Unknown")) for r in results[:5]]

        return {
            **state,
            "answer": answer,
            "citations": citations,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(HybridQAState)

    graph.add_node("classify", classify_intent)
    graph.add_node("semantic", semantic_search)
    graph.add_node("graph", graph_query)
    graph.add_node("keyword", keyword_search)
    graph.add_node("hybrid", hybrid_retrieval)
    graph.add_node("fuse", fuse_results)
    graph.add_node("answer", generate_answer)

    graph.set_entry_point("classify")

    # Route based on intent
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "semantic": "semantic",
            "graph": "graph",
            "keyword": "keyword",
            "hybrid": "hybrid"
        }
    )

    # All paths lead to fusion
    graph.add_edge("semantic", "fuse")
    graph.add_edge("graph", "fuse")
    graph.add_edge("keyword", "fuse")
    graph.add_edge("hybrid", "fuse")

    graph.add_edge("fuse", "answer")
    graph.add_edge("answer", END)

    return graph.compile(checkpointer=get_checkpointer())


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _generate_cypher_for_qa(question: str, entities: List[str]) -> Optional[str]:
    """Generate a Cypher query for the question."""
    question_lower = question.lower()

    # Product queries
    if "product" in question_lower:
        if entities:
            return f"""
MATCH (p:DataProduct)
WHERE p.id IN {entities} OR p.name IN {entities}
OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {{status: 'open'}})
RETURN p.id, p.name, p.description, p.status, p.owner,
       d.name as domain, count(i) as open_incidents
"""
        elif "how many" in question_lower or "count" in question_lower:
            return "MATCH (p:DataProduct) RETURN count(p) as total_products"
        else:
            return """
MATCH (p:DataProduct)
OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
RETURN p.id, p.name, p.status, d.name as domain
ORDER BY p.name
LIMIT 20
"""

    # Incident queries
    if "incident" in question_lower:
        return """
MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
WHERE i.status IN ['open', 'investigating']
RETURN p.name as product, i.id, i.severity, i.description, i.status
ORDER BY
  CASE i.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
  i.created_at DESC
LIMIT 15
"""

    # Lineage queries
    if any(w in question_lower for w in ["lineage", "upstream", "downstream", "depends"]):
        if entities:
            return f"""
MATCH (p:DataProduct {{id: '{entities[0]}'}})
OPTIONAL MATCH upstream = (p)-[:CONSUMES_FROM*1..3]->(up)
OPTIONAL MATCH downstream = (down)-[:CONSUMES_FROM*1..3]->(p)
RETURN p.name as product,
       collect(DISTINCT up.name) as upstream_sources,
       collect(DISTINCT down.name) as downstream_consumers
"""
        return """
MATCH (p:DataProduct)-[r:CONSUMES_FROM]->(source:DataProduct)
RETURN p.name as consumer, source.name as source, type(r) as relationship
LIMIT 30
"""

    # Domain queries
    if "domain" in question_lower:
        return """
MATCH (d:Domain)
OPTIONAL MATCH (d)<-[:IN_DOMAIN]-(p:DataProduct)
RETURN d.name, d.owner, d.description, count(p) as product_count
ORDER BY product_count DESC
"""

    # Health/status queries
    if any(w in question_lower for w in ["health", "status", "quality"]):
        return """
MATCH (p:DataProduct)
OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
WITH p, count(i) as incidents
RETURN p.name, p.status,
       CASE WHEN incidents = 0 THEN 'healthy' ELSE 'degraded' END as health,
       incidents as open_incidents
ORDER BY incidents DESC
LIMIT 20
"""

    return None


def _format_simple_answer(results: List[dict], question: str) -> str:
    """Format results into a simple answer."""
    if not results:
        return "No relevant information found."

    lines = [f"Based on the available data, here's what I found:"]

    for i, result in enumerate(results[:5], 1):
        name = result.get("name", result.get("id", f"Item {i}"))
        desc = result.get("description", "")
        if desc:
            desc = desc[:100] + "..." if len(desc) > 100 else desc
            lines.append(f"  {i}. {name}: {desc}")
        else:
            status = result.get("status", "")
            lines.append(f"  {i}. {name}" + (f" ({status})" if status else ""))

    if len(results) > 5:
        lines.append(f"  ... and {len(results) - 5} more results")

    return "\n".join(lines)
