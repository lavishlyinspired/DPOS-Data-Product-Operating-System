"""
Tests for Incidents API Routes
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestIncidentsAPI:
    """Test cases for Incidents API endpoints."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.api.routes.incidents.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_list_incidents(self, client, mock_neo4j):
        """Test listing all incidents."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'INC001',
                'type': 'quality_violation',
                'severity': 'high',
                'status': 'open',
                'product_id': 'DP001',
                'product_name': 'Customer Data'
            }
        ]

        response = client.get("/api/incidents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_incidents_filter_by_status(self, client, mock_neo4j):
        """Test listing incidents filtered by status."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/incidents?status=open")
        assert response.status_code == 200

    def test_list_incidents_filter_by_severity(self, client, mock_neo4j):
        """Test listing incidents filtered by severity."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/incidents?severity=critical")
        assert response.status_code == 200

    def test_get_incident(self, client, mock_neo4j):
        """Test getting a specific incident."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'INC001',
                'type': 'quality_violation',
                'severity': 'high',
                'status': 'open',
                'description': 'Email validation failed',
                'product_id': 'DP001',
                'product_name': 'Customer Data',
                'agent_executions': []
            }
        ]

        response = client.get("/api/incidents/INC001")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == 'INC001'

    def test_get_incident_not_found(self, client, mock_neo4j):
        """Test getting a non-existent incident."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/incidents/INVALID")
        assert response.status_code == 404

    def test_create_incident(self, client, mock_neo4j):
        """Test creating a new incident."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'INC002',
                'type': 'schema_violation',
                'severity': 'medium',
                'status': 'open',
                'product_id': 'DP001',
                'product_name': 'Customer Data'
            }
        ]

        response = client.post("/api/incidents", json={
            "product_id": "DP001",
            "type": "schema_violation",
            "severity": "medium",
            "description": "Schema mismatch detected"
        })
        assert response.status_code == 200

    def test_update_incident(self, client, mock_neo4j):
        """Test updating an incident."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'INC001',
                'status': 'investigating',
                'severity': 'high'
            }
        ]

        response = client.patch("/api/incidents/INC001", json={
            "status": "investigating"
        })
        assert response.status_code == 200

    def test_incident_stats(self, client, mock_neo4j):
        """Test getting incident statistics."""
        mock_neo4j.execute_query.return_value = [
            {
                'open_count': 5,
                'resolved_count': 10,
                'investigating_count': 2,
                'critical_open': 1,
                'high_open': 2,
                'total': 17
            }
        ]

        response = client.get("/api/incidents/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert 'open_count' in data


class TestIncidentHandling:
    """Test cases for incident handling with AI agent."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_healing_agent(self):
        with patch('src.api.routes.incidents.build_healing_agent') as mock:
            agent = MagicMock()
            agent.invoke.return_value = {
                'action': 'analyzed',
                'recommendation': 'Review data quality rules',
                'status': 'completed'
            }
            mock.return_value = agent
            yield mock

    def test_handle_incident(self, client, mock_healing_agent):
        """Test handling an incident with AI agent."""
        response = client.post("/api/incidents/INC001/handle?severity=high")
        assert response.status_code == 200
        data = response.json()
        assert 'action' in data
        assert 'status' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
