"""
Tests for Domains API Routes
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestDomainsAPI:
    """Test cases for Domains API endpoints."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.api.routes.domains.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_list_domains(self, client, mock_neo4j):
        """Test listing all domains."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DOM001',
                'name': 'Sales',
                'description': 'Sales domain',
                'owner': 'sales@company.com',
                'product_count': 5
            }
        ]

        response = client.get("/api/domains")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_domain(self, client, mock_neo4j):
        """Test getting a specific domain."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DOM001',
                'name': 'Sales',
                'description': 'Sales domain',
                'owner': 'sales@company.com',
                'products': []
            }
        ]

        response = client.get("/api/domains/DOM001")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == 'DOM001'

    def test_get_domain_not_found(self, client, mock_neo4j):
        """Test getting a non-existent domain."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/domains/INVALID")
        assert response.status_code == 404

    def test_create_domain(self, client, mock_neo4j):
        """Test creating a new domain."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DOM002',
                'name': 'Marketing',
                'description': 'Marketing domain',
                'owner': 'marketing@company.com'
            }
        ]

        response = client.post("/api/domains", json={
            "id": "DOM002",
            "name": "Marketing",
            "description": "Marketing domain",
            "owner": "marketing@company.com"
        })
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
