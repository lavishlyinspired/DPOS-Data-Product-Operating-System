"""
Tests for Products API Routes
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestProductsAPI:
    """Test cases for Products API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        """Mock Neo4j manager."""
        with patch('src.api.routes.products.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_list_products(self, client, mock_neo4j):
        """Test listing all products."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DP001',
                'name': 'Customer Data',
                'type': 'dataset',
                'domain_id': 'DOM001',
                'domain_name': 'Sales',
                'health_score': 95.0
            }
        ]

        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_products_with_domain_filter(self, client, mock_neo4j):
        """Test listing products filtered by domain."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products?domain=sales")
        assert response.status_code == 200

    def test_get_product(self, client, mock_neo4j):
        """Test getting a specific product."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DP001',
                'name': 'Customer Data',
                'type': 'dataset',
                'description': 'Customer information',
                'domain_name': 'Sales'
            }
        ]

        response = client.get("/api/products/DP001")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == 'DP001'

    def test_get_product_not_found(self, client, mock_neo4j):
        """Test getting a non-existent product."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products/INVALID")
        assert response.status_code == 404

    def test_get_product_health(self, client, mock_neo4j):
        """Test getting product health metrics."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'DP001',
                'health_score': 95.0,
                'quality_score': 90.0,
                'availability_score': 100.0
            }
        ]

        response = client.get("/api/products/DP001/health")
        assert response.status_code == 200

    def test_get_product_contracts(self, client, mock_neo4j):
        """Test getting product contracts."""
        mock_neo4j.execute_query.return_value = [
            {
                'id': 'CONTRACT001',
                'name': 'Email Validation',
                'type': 'quality'
            }
        ]

        response = client.get("/api/products/DP001/contracts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_product_incidents(self, client, mock_neo4j):
        """Test getting product incidents."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products/DP001/incidents")
        assert response.status_code == 200

    def test_get_product_lineage(self, client, mock_neo4j):
        """Test getting product lineage."""
        mock_neo4j.execute_query.return_value = [
            {
                'source_id': 'DP002',
                'source_name': 'Raw Data',
                'target_id': 'DP001',
                'target_name': 'Customer Data'
            }
        ]

        response = client.get("/api/products/DP001/lineage")
        assert response.status_code == 200


class TestProductsAPIPagination:
    """Test pagination for Products API."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.api.routes.products.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield manager

    def test_products_with_limit(self, client, mock_neo4j):
        """Test products endpoint with limit parameter."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products?limit=10")
        assert response.status_code == 200

    def test_products_with_offset(self, client, mock_neo4j):
        """Test products endpoint with offset parameter."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products?offset=20")
        assert response.status_code == 200

    def test_products_with_pagination(self, client, mock_neo4j):
        """Test products endpoint with both limit and offset."""
        mock_neo4j.execute_query.return_value = []

        response = client.get("/api/products?limit=10&offset=20")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
