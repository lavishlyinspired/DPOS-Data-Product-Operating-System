"""
Agent Logger Utility
Provides consistent logging for all DPOS agents.
"""
import logging
from datetime import datetime, UTC


def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a configured logger for an agent.
    
    Args:
        agent_name: Name of the agent (e.g., 'HealingAgent', 'ImpactAgent')
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"dpos.agents.{agent_name}")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f"%(asctime)s | {agent_name} | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


class AgentLogContext:
    """Context manager for agent execution logging."""
    
    def __init__(self, agent_name: str, operation: str):
        self.logger = get_agent_logger(agent_name)
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now(UTC)
        self.logger.info(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now(UTC) - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(f"Failed {self.operation} after {duration:.2f}s: {exc_val}")
        else:
            self.logger.info(f"Completed {self.operation} in {duration:.2f}s")
        return False
