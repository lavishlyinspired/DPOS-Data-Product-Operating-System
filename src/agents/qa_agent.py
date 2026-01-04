"""
QA Agent
Question Answering agent for data product queries.
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from src.agents.tools.common_tools import search_products, get_contract_rules
from src.agents.checkpointer import get_checkpointer
from src.agents.utils.logger import get_agent_logger
from src.core.llm import get_llm_if_available


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

        llm = get_llm_if_available()
        if llm and context:
            try:
                # Compact context for prompt.
                ctx_lines: List[str] = []
                for item in context[:12]:
                    if "description" in item:
                        name = item.get("name", item.get("id", "Unknown"))
                        desc = (item.get("description") or "").strip().replace("\n", " ")
                        status = item.get("status")
                        pid = item.get("id")
                        parts = [name]
                        if pid:
                            parts.append(f"id={pid}")
                        if status:
                            parts.append(f"status={status}")
                        line = "- " + " | ".join(parts)
                        if desc:
                            line += f" :: {desc[:240]}"
                        ctx_lines.append(line)
                    else:
                        # Likely a contract rule shape
                        rname = item.get("name", "Rule")
                        rtype = item.get("type", "")
                        field = item.get("field", "")
                        rule_parts = [rname]
                        if rtype:
                            rule_parts.append(f"type={rtype}")
                        if field:
                            rule_parts.append(f"field={field}")
                        ctx_lines.append("- " + " | ".join(rule_parts))

                prompt = (
                    "You are a data product governance assistant.\n"
                    "Answer the user's question using ONLY the provided context.\n"
                    "Also provide a short next-step checklist (3-6 bullets).\n\n"
                    f"QUESTION: {state.get('question', '')}\n\n"
                    "CONTEXT:\n"
                    + "\n".join(ctx_lines)
                    + "\n\n"
                    "Return plain text ONLY in this format:\n"
                    "ANSWER: <text>\n"
                    "NEXT_STEPS:\n"
                    "- <bullet>\n"
                )

                resp = llm.invoke(prompt)
                content = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()

                answer_text = ""
                steps: List[str] = []
                in_steps = False
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("ANSWER:"):
                        answer_text = line.replace("ANSWER:", "", 1).strip()
                        in_steps = False
                        continue
                    if line.startswith("NEXT_STEPS:"):
                        in_steps = True
                        continue
                    if in_steps and line.startswith("-"):
                        steps.append(line.lstrip("-").strip())

                if not answer_text:
                    # If parsing failed, keep full content but still return.
                    answer_text = content

                if steps:
                    answer_text = answer_text.rstrip() + "\n\nNext steps:\n" + "\n".join(f"- {s}" for s in steps[:6])

                return {
                    **state,
                    "answer": answer_text,
                }
            except Exception as e:
                log.warning(f"LLM answer synthesis failed: {e}")

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
