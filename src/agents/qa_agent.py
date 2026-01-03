"""
QA Agent
Question Answering agent for data product queries.
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import search_products, get_contract_rules
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger


class QAAgentState(TypedDict):
    """State for the Q&A agent."""
    question: str
    context: List[dict]
    answer: str
    sources: List[str]


def build_qa_agent():
    """Build an enhanced Q&A agent with checkpointing."""
    log = get_agent_logger("QAAgent")

    def gather_context(state: QAAgentState) -> QAAgentState:
        """Gather relevant context for the question."""
        log.info(f"Gathering context for: {state['question']}")

        # Search for relevant products
        products = search_products.invoke(state["question"])

        context = []
        sources = []

        for product in products[:3]:
            context.append(product)
            sources.append(f"DataProduct: {product.get('name', 'Unknown')}")

            # Get rules if relevant
            question_lower = state["question"].lower()
            if "contract" in question_lower or "rule" in question_lower:
                rules = get_contract_rules.invoke(product["id"])
                for rule in rules[:3]:
                    context.append(rule)
                    sources.append(f"Rule: {rule.get('name', 'Unknown')}")

        return {
            **state,
            "context": context,
            "sources": sources
        }

    def generate_answer(state: QAAgentState) -> QAAgentState:
        """Generate an answer based on context."""
        log.info("Generating answer")

        context = state.get("context", [])

        if not context:
            answer = "I couldn't find relevant information to answer your question. Please try rephrasing or be more specific about the data product you're interested in."
        else:
            # Build answer from context
            answer_parts = [f"Based on my search, I found {len(context)} relevant items:\n"]

            for item in context:
                if "description" in item:
                    desc = item.get('description', 'No description')
                    if desc:
                        desc = desc[:100]
                    answer_parts.append(f"- {item.get('name', 'Unknown')}: {desc}")
                elif "type" in item:
                    answer_parts.append(
                        f"- Rule '{item.get('name')}' of type '{item.get('type')}' "
                        f"applies to field '{item.get('field', 'N/A')}'"
                    )

            answer = "\n".join(answer_parts)

        return {
            **state,
            "answer": answer
        }

    # Build the graph
    graph = StateGraph(QAAgentState)

    graph.add_node("gather", gather_context)
    graph.add_node("answer", generate_answer)

    graph.set_entry_point("gather")
    graph.add_edge("gather", "answer")
    graph.add_edge("answer", END)

    return graph.compile(checkpointer=get_checkpointer())
