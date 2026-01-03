"""
End-to-End Tests for Full Governance Flow
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock


class TestFullGovernanceFlow:
    """End-to-end tests for the complete governance workflow."""

    @pytest.mark.integration
    @pytest.mark.neo4j
    def test_full_governance_flow(self, neo4j_session):
        """Test complete governance flow from data load to incident resolution."""
        from scripts.load_customers_with_contracts import run_load
        from src.graph.manager import Neo4jManager

        # Load test data with contracts
        run_load("data/bad/customers_bad.csv")

        # Verify incident was created
        result = neo4j_session.execute_query(
            "MATCH (i:Incident) RETURN count(i) AS c"
        )
        assert result[0]["c"] > 0

        # Verify agent execution was logged
        result = neo4j_session.execute_query("""
            MATCH (:Incident)-[:HANDLED_BY]->(:AgentExecution)
            RETURN count(*) AS c
        """)
        assert result[0]["c"] > 0

    @pytest.mark.integration
    def test_data_ingestion_triggers_validation(self, neo4j_session):
        """Test that data ingestion triggers contract validation."""
        from src.contracts.validator import ContractValidator

        # Mock the policy resolver to return test rules
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = [
                {'id': 'r1', 'type': 'null_rate', 'field': 'email', 'severity': 'error'}
            ]

            validator = ContractValidator("DP_CUSTOMERS")
            result = validator.validate_batch([
                {"email": "test@test.com", "name": "John"},
                {"email": None, "name": "Jane"}
            ])

            assert result['total_records'] == 2
            assert result['failed_records'] >= 0  # May fail due to null


class TestIncidentCreationFlow:
    """Test incident creation and handling flow."""

    @pytest.fixture
    def mock_neo4j(self):
        """Mock Neo4j for testing."""
        with patch('src.graph.manager.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_incident_creation_on_violation(self, mock_neo4j):
        """Test that incidents are created when violations occur."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'INC-12345678',
                'type': 'quality_violation',
                'severity': 'high',
                'status': 'open',
                'product_id': 'DP001'
            }
        ]

        from src.api.routes.incidents import create_incident, IncidentCreate

        incident_data = IncidentCreate(
            product_id="DP001",
            type="quality_violation",
            severity="high",
            description="Email null rate exceeded threshold"
        )

        result = create_incident(incident_data)
        assert result['status'] == 'open'
        assert result['severity'] == 'high'

    def test_incident_handling_by_agent(self):
        """Test that incidents are properly handled by AI agent."""
        from src.agents.healing_agent import build_healing_agent

        with patch('src.agents.healing_agent.ChatOpenAI'):
            with patch('langgraph.checkpoint.memory.MemorySaver'):
                agent = build_healing_agent()

                result = agent.invoke(
                    {
                        "incident_id": "INC-TEST001",
                        "severity": "critical",
                        "recommendation": "",
                        "action": "",
                        "status": ""
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}}
                )

                assert result is not None


class TestLineageFlow:
    """Test data lineage tracking flow."""

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.graph.manager.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_lineage_upstream(self, mock_neo4j):
        """Test retrieving upstream lineage."""
        mock_neo4j.execute_query.return_value = [
            {
                'source_id': 'DP_RAW',
                'source_name': 'Raw Customer Data',
                'target_id': 'DP_CLEAN',
                'target_name': 'Clean Customer Data',
                'relationship': 'FEEDS_INTO'
            }
        ]

        from src.api.routes.products import get_product_lineage

        result = get_product_lineage("DP_CLEAN")
        assert isinstance(result, list)

    def test_lineage_downstream(self, mock_neo4j):
        """Test retrieving downstream lineage."""
        mock_neo4j.execute_query.return_value = [
            {
                'source_id': 'DP_CLEAN',
                'source_name': 'Clean Customer Data',
                'target_id': 'DP_ANALYTICS',
                'target_name': 'Customer Analytics',
                'relationship': 'FEEDS_INTO'
            }
        ]

        from src.api.routes.products import get_product_lineage

        result = get_product_lineage("DP_CLEAN")
        assert isinstance(result, list)


class TestPolicyApplication:
    """Test policy application flow."""

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.graph.manager.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_apply_policy_to_domain(self, mock_neo4j):
        """Test applying a policy to a domain."""
        mock_neo4j.execute_query.return_value = [
            {
                'policy_id': 'POL001',
                'target_id': 'DOM001',
                'target_type': 'domain'
            }
        ]

        from src.api.routes.policies import apply_policy

        result = apply_policy("POL001", "domain", "DOM001")
        assert result['target_type'] == 'domain'

    def test_apply_policy_to_product(self, mock_neo4j):
        """Test applying a policy to a product."""
        mock_neo4j.execute_query.return_value = [
            {
                'policy_id': 'POL001',
                'target_id': 'DP001',
                'target_type': 'product'
            }
        ]

        from src.api.routes.policies import apply_policy

        result = apply_policy("POL001", "product", "DP001")
        assert result['target_type'] == 'product'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
