"""
Tests for Healing Agent
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock


class TestHealingAgent:
    """Test cases for the healing agent functionality."""

    def test_healing_agent_builds_successfully(self):
        """Test that healing agent can be built."""
        from src.agents.healing_agent import build_healing_agent
        agent = build_healing_agent()
        assert agent is not None

    @pytest.mark.integration
    def test_healing_agent_invoke(self):
        """Test healing agent invocation with thread_id."""
        from src.agents.healing_agent import build_healing_agent

        agent = build_healing_agent()
        result = agent.invoke(
            {
                "incident_id": "INC_TEST_001",
                "severity": "medium",
                "recommendation": "",
                "action": "",
                "status": ""
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert "status" in result

    def test_healing_agent_with_critical_severity(self):
        """Test healing agent handles critical severity."""
        from src.agents.healing_agent import build_healing_agent

        agent = build_healing_agent()
        result = agent.invoke(
            {
                "incident_id": "INC_CRIT_001",
                "severity": "critical",
                "recommendation": "",
                "action": "",
                "status": ""
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert result.get("status") in ["completed", "escalated"]


class TestIncidentImpactAgent:
    """Test cases for incident impact analysis agent."""

    def test_incident_impact_agent_builds(self):
        """Test that incident impact agent can be built."""
        from src.agents.incident_impact import build_incident_impact_agent
        agent = build_incident_impact_agent()
        assert agent is not None

    @pytest.mark.integration
    def test_incident_impact_analysis(self):
        """Test incident impact analysis."""
        from src.agents.incident_impact import build_incident_impact_agent

        agent = build_incident_impact_agent()
        result = agent.invoke(
            {"incident_id": "INC_001"},
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert "impact" in result or "analysis" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
