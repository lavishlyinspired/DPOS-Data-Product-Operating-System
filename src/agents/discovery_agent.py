"""
Discovery Agent
Discovers and catalogs data assets in the DPOS knowledge graph.
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import search_products
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available


class DiscoveryAgentState(TypedDict):
    """State for the discovery agent."""
    query: str
    sources_scanned: List[str]
    discovered_products: List[dict]
    recommendations: List[str]
    status: str


def build_discovery_agent():
    """Build an enhanced discovery agent with checkpointing."""
    log = get_agent_logger("DiscoveryAgent")

    def search_catalog(state: DiscoveryAgentState) -> DiscoveryAgentState:
        """Search the data catalog."""
        log.info(f"Searching catalog for: {state['query']}")

        products = search_products.invoke(state["query"])

        return {
            **state,
            "discovered_products": products,
            "sources_scanned": ["Neo4j Data Catalog"],
            "status": "searched"
        }

    def generate_recommendations(state: DiscoveryAgentState) -> DiscoveryAgentState:
        """Generate recommendations based on search results."""
        log.info("Generating recommendations")

        products = state.get("discovered_products", [])
        recommendations: List[str] = []

        llm = get_llm_if_available()
        if llm and products:
            try:
                # Keep prompt short and deterministic-ish; ask for actionable checklist.
                product_lines = []
                for p in products[:10]:
                    name = p.get("name", "Unknown")
                    pid = p.get("id", "")
                    status = p.get("status", "")
                    domain = p.get("domain", "")
                    ptype = p.get("type", "")
                    parts = [name]
                    if pid:
                        parts.append(f"id={pid}")
                    if ptype:
                        parts.append(f"type={ptype}")
                    if status:
                        parts.append(f"status={status}")
                    if domain:
                        parts.append(f"domain={domain}")
                    product_lines.append("- " + " | ".join(parts))

                prompt = (
                    "You are a data product discovery assistant.\n"
                    "Given a discovery query and matching products, produce: \n"
                    "1) A one-paragraph summary of what was found\n"
                    "2) A next-step checklist (3-6 bullets) for what the user should do next\n\n"
                    f"Query: {state.get('query', '')}\n\n"
                    "Top matches:\n"
                    + "\n".join(product_lines)
                    + "\n\n"
                    "Return plain text only in this exact format:\n"
                    "SUMMARY: <text>\n"
                    "NEXT_STEPS:\n"
                    "- <bullet>\n"
                )

                resp = llm.invoke(prompt)
                content = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()

                summary = ""
                steps: List[str] = []
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("SUMMARY:"):
                        summary = line.replace("SUMMARY:", "", 1).strip()
                    elif line.startswith("-"):
                        steps.append(line.lstrip("-").strip())

                if summary:
                    recommendations.append(summary)
                recommendations.extend(steps[:6])

                if recommendations:
                    return {
                        **state,
                        "recommendations": recommendations,
                        "status": "completed",
                    }
            except Exception as e:
                log.warning(f"LLM recommendations failed: {e}")

        if not products:
            recommendations.append("No products found. Try broader search terms.")
            recommendations.append("Consider checking the data domains: Customer, Order, Inventory")
        else:
            recommendations.append(f"Found {len(products)} matching data products")
            for p in products[:3]:
                recommendations.append(f"Consider: {p.get('name', 'Unknown')} ({p.get('type', 'unknown')} type)")

        return {
            **state,
            "recommendations": recommendations,
            "status": "completed"
        }

    # Build the graph
    graph = StateGraph(DiscoveryAgentState)

    graph.add_node("search", search_catalog)
    graph.add_node("recommend", generate_recommendations)

    graph.set_entry_point("search")
    graph.add_edge("search", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile(checkpointer=get_checkpointer())
