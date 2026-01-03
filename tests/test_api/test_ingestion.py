"""
Tests for Data Ingestion API Routes
"""
import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestCSVIngestion:
    """Test cases for CSV data ingestion."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.api.main.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            manager.execute_query.return_value = []
            yield manager

    @pytest.fixture
    def mock_validator(self):
        with patch('src.api.main.ContractValidator') as mock:
            validator = MagicMock()
            validator.validate_batch.return_value = {
                'result': 'passed',
                'total_records': 3,
                'failed_records': 0,
                'violations': []
            }
            mock.return_value = validator
            yield validator

    def test_ingest_csv_valid(self, client, mock_neo4j, mock_validator):
        """Test ingesting valid CSV data."""
        csv_content = "id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post("/api/ingest/csv/DP001?validate=true", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['records_processed'] > 0

    def test_ingest_csv_without_validation(self, client, mock_neo4j):
        """Test ingesting CSV without validation."""
        csv_content = "id,name,email\n1,John,john@test.com"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post("/api/ingest/csv/DP001?validate=false", files=files)
        assert response.status_code == 200

    def test_ingest_csv_validation_failed(self, client, mock_neo4j, mock_validator):
        """Test ingesting CSV with validation failures."""
        mock_validator.validate_batch.return_value = {
            'result': 'failed',
            'total_records': 3,
            'failed_records': 2,
            'violations': [
                {'field': 'email', 'rule': 'null_rate', 'count': 2}
            ]
        }

        csv_content = "id,name,email\n1,John,\n2,Jane,"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post("/api/ingest/csv/DP001?validate=true", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data['validation']['result'] == 'failed'


class TestJSONIngestion:
    """Test cases for JSON data ingestion."""

    @pytest.fixture
    def client(self):
        from src.api.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_neo4j(self):
        with patch('src.api.main.Neo4jManager') as mock:
            manager = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=manager)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            manager.execute_query.return_value = []
            yield manager

    @pytest.fixture
    def mock_validator(self):
        with patch('src.api.main.ContractValidator') as mock:
            validator = MagicMock()
            validator.validate_batch.return_value = {
                'result': 'passed',
                'total_records': 2,
                'failed_records': 0,
                'violations': []
            }
            mock.return_value = validator
            yield validator

    def test_ingest_json_valid(self, client, mock_neo4j, mock_validator):
        """Test ingesting valid JSON data."""
        json_data = {
            "records": [
                {"id": "1", "name": "John", "email": "john@test.com"},
                {"id": "2", "name": "Jane", "email": "jane@test.com"}
            ]
        }

        response = client.post("/api/ingest/json/DP001?validate=true", json=json_data)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

    def test_ingest_json_without_validation(self, client, mock_neo4j):
        """Test ingesting JSON without validation."""
        json_data = {
            "records": [{"id": "1", "name": "John"}]
        }

        response = client.post("/api/ingest/json/DP001?validate=false", json=json_data)
        assert response.status_code == 200

    def test_ingest_json_empty_records(self, client, mock_neo4j, mock_validator):
        """Test ingesting empty JSON records."""
        json_data = {"records": []}

        response = client.post("/api/ingest/json/DP001?validate=true", json=json_data)
        assert response.status_code == 200
        data = response.json()
        assert data['records_processed'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
