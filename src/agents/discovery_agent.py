"""
Discovery Agent
Discovers and catalogs data assets in the DPOS knowledge graph.
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import search_products
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger


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
        recommendations = []

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
