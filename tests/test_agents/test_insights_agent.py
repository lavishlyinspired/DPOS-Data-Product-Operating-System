"""
Tests for Insights Agent
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock


class TestInsightsAgent:
    """Test cases for the insights agent."""

    def test_insights_agent_builds_successfully(self):
        """Test that insights agent can be built."""
        from src.agents.insights_agent import build_insights_agent
        agent = build_insights_agent()
        assert agent is not None

    @pytest.mark.integration
    def test_insights_agent_invoke(self):
        """Test insights agent invocation."""
        from src.agents.insights_agent import build_insights_agent

        agent = build_insights_agent()
        result = agent.invoke(
            {
                "time_range_days": 30,
                "products_data": [],
                "incidents_data": [],
                "contracts_data": [],
                "metrics_data": [],
                "health_summary": None,
                "incident_trends": None,
                "quality_patterns": None,
                "compliance_insights": None,
                "executive_summary": None,
                "key_findings": None,
                "recommendations": None,
                "risk_areas": None,
                "improvement_opportunities": None,
                "alerts": [],
                "status": "initialized",
                "messages": []
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        assert result is not None
        assert "status" in result
        assert result.get("status") == "completed"

    def test_run_insights_analysis_convenience(self):
        """Test the convenience run_insights_analysis function."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        assert result is not None
        assert "status" in result

    def test_insights_analysis_custom_time_range(self):
        """Test insights analysis with custom time range."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis(time_range_days=7)

        assert result is not None
        assert "status" in result


class TestHealthAnalysis:
    """Test health analysis functionality."""

    def test_health_summary_structure(self):
        """Test health summary has expected structure."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        if result.get("health_summary"):
            summary = result["health_summary"]
            assert "total_products" in summary
            assert "healthy" in summary
            assert "degraded" in summary
            assert "critical" in summary

    def test_overall_health_status(self):
        """Test overall health status is calculated."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        if result.get("health_summary"):
            assert "overall_health" in result["health_summary"]
            assert result["health_summary"]["overall_health"] in ["good", "degraded", "critical"]


class TestIncidentAnalysis:
    """Test incident trend analysis."""

    def test_incident_trends_structure(self):
        """Test incident trends has expected structure."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        if result.get("incident_trends"):
            trends = result["incident_trends"]
            assert "total" in trends
            assert "open" in trends

    def test_severity_breakdown(self):
        """Test incident severity breakdown."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        if result.get("incident_trends"):
            trends = result["incident_trends"]
            assert "critical" in trends
            assert "high" in trends
            assert "medium" in trends
            assert "low" in trends


class TestRecommendations:
    """Test recommendations generation."""

    def test_executive_summary_generated(self):
        """Test executive summary is generated."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        # Executive summary should be generated
        assert "executive_summary" in result

    def test_recommendations_list(self):
        """Test recommendations are generated."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        assert "recommendations" in result

    def test_alerts_generated(self):
        """Test alerts are generated for issues."""
        from src.agents.insights_agent import run_insights_analysis

        result = run_insights_analysis()

        assert "alerts" in result
        assert isinstance(result["alerts"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
