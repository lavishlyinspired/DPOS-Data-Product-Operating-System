"""
Tests for SLA Monitoring Agent
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock


class TestSLAAgent:
    """Test cases for the SLA monitoring agent."""

    def test_sla_agent_builds_successfully(self):
        """Test that SLA agent can be built."""
        from src.agents.sla_agent import build_sla_agent
        agent = build_sla_agent()
        assert agent is not None

    @pytest.mark.integration
    def test_sla_agent_invoke_all_products(self):
        """Test SLA agent invocation for all products."""
        from src.agents.sla_agent import build_sla_agent

        agent = build_sla_agent()
        result = agent.invoke(
            {
                "product_ids": None,  # Monitor all
                "slas": [],
                "current_metrics": {},
                "breached_slas": [],
                "at_risk_slas": [],
                "healthy_slas": [],
                "breach_analysis": None,
                "risk_predictions": None,
                "recommendations": None,
                "trend_analysis": None,
                "notifications": [],
                "escalations": [],
                "status": "initialized",
                "messages": []
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert "status" in result
        assert result.get("status") == "completed"

    @pytest.mark.integration
    def test_sla_agent_invoke_specific_products(self):
        """Test SLA agent invocation for specific products."""
        from src.agents.sla_agent import build_sla_agent

        agent = build_sla_agent()
        result = agent.invoke(
            {
                "product_ids": ["DP001", "DP002"],
                "slas": [],
                "current_metrics": {},
                "breached_slas": [],
                "at_risk_slas": [],
                "healthy_slas": [],
                "breach_analysis": None,
                "risk_predictions": None,
                "recommendations": None,
                "trend_analysis": None,
                "notifications": [],
                "escalations": [],
                "status": "initialized",
                "messages": []
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert "status" in result

    def test_run_sla_monitoring_convenience(self):
        """Test the convenience run_sla_monitoring function."""
        from src.agents.sla_agent import run_sla_monitoring

        result = run_sla_monitoring()

        assert result is not None
        assert "status" in result
        assert "summary" in result

    def test_sla_monitoring_returns_summary(self):
        """Test that SLA monitoring returns proper summary."""
        from src.agents.sla_agent import run_sla_monitoring

        result = run_sla_monitoring()

        # Check summary structure
        assert "summary" in result
        summary = result["summary"]
        assert "total_slas" in summary
        assert "breached" in summary
        assert "at_risk" in summary
        assert "healthy" in summary


class TestSLABreachDetection:
    """Test breach detection logic."""

    def test_detect_freshness_breach(self):
        """Test freshness SLA breach detection."""
        from src.agents.sla_agent import run_sla_monitoring

        # Run and check for breach detection logic
        result = run_sla_monitoring(["DP001"])

        # Should have executed without error
        assert result["status"] == "completed"

    def test_detect_availability_breach(self):
        """Test availability SLA breach detection."""
        from src.agents.sla_agent import run_sla_monitoring

        result = run_sla_monitoring()
        assert "breached_slas" in result

    def test_at_risk_prediction(self):
        """Test at-risk SLA prediction."""
        from src.agents.sla_agent import run_sla_monitoring

        result = run_sla_monitoring()
        assert "at_risk_slas" in result
        assert "risk_predictions" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
