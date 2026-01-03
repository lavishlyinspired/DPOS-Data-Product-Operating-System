"""
Tests for Data Models
"""
import pytest
from src.models import Domain, DataProduct, Field


class TestDomain:
    """Test cases for Domain model."""

    def test_domain_creation(self, sample_domain):
        """Test basic domain creation."""
        assert sample_domain.id == "TEST_DOM"
        assert sample_domain.name == "Test Domain"
        assert sample_domain.owner == "test@test.com"

    def test_domain_with_optional_fields(self):
        """Test domain creation with all fields."""
        domain = Domain(
            id="DOM001",
            name="Sales Domain",
            owner="sales@company.com",
            team="Sales Team",
            description="Handles all sales data"
        )
        assert domain.id == "DOM001"
        assert domain.description == "Handles all sales data"


class TestDataProduct:
    """Test cases for DataProduct model."""

    def test_data_product_creation(self, sample_product):
        """Test basic data product creation."""
        assert sample_product.id == "TEST_PROD"
        assert sample_product.domain_id == "TEST_DOM"
        assert sample_product.name == "Test Product"

    def test_data_product_with_all_fields(self):
        """Test data product with all fields populated."""
        product = DataProduct(
            id="DP001",
            name="Customer Data",
            title="Customer Master Data",
            owner="data@company.com",
            domain_id="DOM001",
            type="dataset",
            description="Customer information",
            status="active"
        )
        assert product.id == "DP001"
        assert product.type == "dataset"
        assert product.status == "active"


class TestField:
    """Test cases for Field model."""

    def test_field_creation(self, sample_field):
        """Test basic field creation."""
        assert sample_field.id == "TEST_FIELD"
        assert sample_field.name == "email"
        assert sample_field.type == "string"

    def test_field_pii_detection(self):
        """Test PII field detection."""
        pii_field = Field(id="f1", name="email", type="string", is_pii=True)
        assert pii_field.is_pii is True

        non_pii_field = Field(id="f2", name="count", type="integer", is_pii=False)
        assert non_pii_field.is_pii is False

    def test_field_types(self):
        """Test different field types."""
        string_field = Field(id="f1", name="name", type="string")
        assert string_field.type == "string"

        int_field = Field(id="f2", name="age", type="integer")
        assert int_field.type == "integer"

        date_field = Field(id="f3", name="created_at", type="datetime")
        assert date_field.type == "datetime"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
