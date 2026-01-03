"""
Pytest Configuration and Fixtures
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock, patch


# ============================================================================
# Neo4j Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def neo4j_session():
    """Creates a connection to Neo4j. Requires docker-compose to be running."""
    from src.graph.manager import Neo4jManager
    mgr = Neo4jManager()
    yield mgr
    mgr.close()


@pytest.fixture
def mock_neo4j_manager():
    """Mock Neo4j manager for unit tests."""
    with patch('src.graph.manager.Neo4jManager') as mock:
        manager = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=manager)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield manager


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def sample_domain():
    """Create a sample domain for testing."""
    from src.models import Domain
    return Domain(
        id="TEST_DOM",
        name="Test Domain",
        owner="test@test.com",
        team="Test"
    )


@pytest.fixture
def sample_product():
    """Create a sample data product for testing."""
    from src.models import DataProduct
    return DataProduct(
        id="TEST_PROD",
        name="Test Product",
        title="Test Data Product",
        owner="test@test.com",
        domain_id="TEST_DOM"
    )


@pytest.fixture
def sample_field():
    """Create a sample field for testing."""
    from src.models import Field
    return Field(
        id="TEST_FIELD",
        name="email",
        type="string",
        is_pii=True
    )


# ============================================================================
# Contract Fixtures
# ============================================================================

@pytest.fixture
def sample_contract_rules():
    """Create sample contract rules for testing."""
    return [
        {
            'id': 'rule1',
            'type': 'null_rate',
            'field': 'email',
            'threshold': 0.1,
            'severity': 'error'
        },
        {
            'id': 'rule2',
            'type': 'pattern',
            'field': 'id',
            'pattern': '^CUST[0-9]+$',
            'severity': 'warning'
        },
        {
            'id': 'rule3',
            'type': 'enum',
            'field': 'status',
            'allowed_values': ['active', 'inactive', 'pending'],
            'severity': 'error'
        }
    ]


@pytest.fixture
def sample_validation_data():
    """Create sample data for validation testing."""
    return [
        {"id": "CUST001", "email": "john@test.com", "status": "active"},
        {"id": "CUST002", "email": "jane@test.com", "status": "inactive"},
        {"id": "CUST003", "email": None, "status": "pending"},
    ]


# ============================================================================
# API Test Fixtures
# ============================================================================

@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    return TestClient(app)


@pytest.fixture
def mock_contract_validator():
    """Mock contract validator for testing."""
    with patch('src.contracts.validator.ContractValidator') as mock:
        validator = MagicMock()
        validator.validate_batch.return_value = {
            'result': 'passed',
            'total_records': 0,
            'failed_records': 0,
            'violations': []
        }
        mock.return_value = validator
        yield validator


# ============================================================================
# Agent Fixtures
# ============================================================================

@pytest.fixture
def mock_healing_agent():
    """Mock healing agent for testing."""
    with patch('src.agents.healing_agent.build_healing_agent') as mock:
        agent = MagicMock()
        agent.invoke.return_value = {
            'incident_id': 'INC001',
            'severity': 'medium',
            'recommendation': 'Review data quality',
            'action': 'analyzed',
            'status': 'completed'
        }
        mock.return_value = agent
        yield mock


@pytest.fixture
def mock_incident_impact_agent():
    """Mock incident impact agent for testing."""
    with patch('src.agents.incident_impact.build_incident_impact_agent') as mock:
        agent = MagicMock()
        agent.invoke.return_value = {
            'incident_id': 'INC001',
            'impact': 'medium',
            'affected_products': ['DP001', 'DP002'],
            'analysis': 'Impact analysis complete'
        }
        mock.return_value = agent
        yield mock


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires external services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "neo4j: mark test as requiring Neo4j"
    )
