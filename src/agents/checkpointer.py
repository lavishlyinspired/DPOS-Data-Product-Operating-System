"""
Checkpointer module for LangGraph agents.
Provides persistence for agent state, enabling:
- Resumable workflows after failures
- Human-in-the-loop interrupts
- Conversation history across sessions
"""
from langgraph.checkpoint.memory import MemorySaver
from typing import Optional
import os


# Singleton checkpointer instance
_memory_checkpointer: Optional[MemorySaver] = None


def get_checkpointer() -> MemorySaver:
    """
    Returns a singleton MemorySaver checkpointer.
    For production, consider using PostgresSaver or similar persistent storage.
    """
    global _memory_checkpointer
    if _memory_checkpointer is None:
        _memory_checkpointer = MemorySaver()
    return _memory_checkpointer


def get_thread_config(thread_id: str) -> dict:
    """
    Generate a configuration dict for a specific thread.
    Thread IDs are used to track separate conversation/workflow instances.
    """
    return {"configurable": {"thread_id": thread_id}}


def reset_checkpointer():
    """Reset the checkpointer (useful for testing)."""
    global _memory_checkpointer
    _memory_checkpointer = None
