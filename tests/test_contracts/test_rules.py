"""
Tests for Contract Validation Rules
"""
import pytest
from src.contracts.rules.null_rate import NullRateRule
from src.contracts.rules.pattern import PatternRule
from src.contracts.rules.enum import EnumRule


class TestNullRateRule:
    """Test cases for NullRateRule validation."""

    def test_null_rate_rule_valid_value(self):
        """Test null rate rule with valid non-null value."""
        rule = NullRateRule({"field": "email", "severity": "error"})
        assert rule.validate({"email": "test@test.com"}) is True

    def test_null_rate_rule_null_value(self):
        """Test null rate rule with null value."""
        rule = NullRateRule({"field": "email", "severity": "error"})
        assert rule.validate({"email": None}) is False

    def test_null_rate_rule_empty_string(self):
        """Test null rate rule with empty string."""
        rule = NullRateRule({"field": "name", "severity": "warning"})
        # Empty string is not null
        result = rule.validate({"name": ""})
        assert result is True  # Empty string is not null

    def test_null_rate_rule_missing_field(self):
        """Test null rate rule when field is missing."""
        rule = NullRateRule({"field": "email", "severity": "error"})
        result = rule.validate({"name": "John"})
        assert result is False  # Missing field should be treated as null


class TestNullRateBatch:
    """Test cases for batch null rate validation."""

    def test_null_rate_batch_within_threshold(self):
        """Test batch validation when null rate is within threshold."""
        rule = NullRateRule({
            "id": "nr1",
            "field": "email",
            "threshold": 0.5
        })
        batch = [
            {"email": "a@test.com"},
            {"email": None},
            {"email": "b@test.com"},
            {"email": None},
        ]
        assert rule.validate_batch(batch) is True

    def test_null_rate_batch_exceeds_threshold(self):
        """Test batch validation when null rate exceeds threshold."""
        rule = NullRateRule({
            "id": "nr2",
            "field": "email",
            "threshold": 0.25
        })
        batch = [
            {"email": None},
            {"email": None},
            {"email": "x@test.com"},
            {"email": None},
        ]
        assert rule.validate_batch(batch) is False

    def test_null_rate_batch_all_valid(self):
        """Test batch with no null values."""
        rule = NullRateRule({
            "id": "nr3",
            "field": "email",
            "threshold": 0.1
        })
        batch = [
            {"email": "a@test.com"},
            {"email": "b@test.com"},
            {"email": "c@test.com"},
        ]
        assert rule.validate_batch(batch) is True

    def test_null_rate_batch_empty(self):
        """Test batch validation with empty batch."""
        rule = NullRateRule({
            "id": "nr4",
            "field": "email",
            "threshold": 0.5
        })
        batch = []
        # Empty batch should pass (no violations)
        assert rule.validate_batch(batch) is True


class TestPatternRule:
    """Test cases for PatternRule validation."""

    def test_pattern_rule_valid_id(self):
        """Test pattern rule with valid ID format."""
        rule = PatternRule({"field": "id", "pattern": "^CUST[0-9]{6}$"})
        assert rule.validate({"id": "CUST000001"}) is True

    def test_pattern_rule_invalid_id(self):
        """Test pattern rule with invalid ID format."""
        rule = PatternRule({"field": "id", "pattern": "^CUST[0-9]{6}$"})
        assert rule.validate({"id": "123"}) is False

    def test_pattern_rule_email_format(self):
        """Test pattern rule for email validation."""
        rule = PatternRule({
            "field": "email",
            "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"
        })
        assert rule.validate({"email": "test@example.com"}) is True
        assert rule.validate({"email": "invalid-email"}) is False

    def test_pattern_rule_phone_format(self):
        """Test pattern rule for phone number validation."""
        rule = PatternRule({
            "field": "phone",
            "pattern": r"^\+?[0-9]{10,15}$"
        })
        assert rule.validate({"phone": "+12025551234"}) is True
        assert rule.validate({"phone": "abc123"}) is False


class TestEnumRule:
    """Test cases for EnumRule validation."""

    def test_enum_rule_valid_status(self):
        """Test enum rule with valid status value."""
        rule = EnumRule({"field": "status", "allowed_values": ["active", "inactive"]})
        assert rule.validate({"status": "active"}) is True

    def test_enum_rule_invalid_status(self):
        """Test enum rule with invalid status value."""
        rule = EnumRule({"field": "status", "allowed_values": ["active", "inactive"]})
        assert rule.validate({"status": "pending"}) is False

    def test_enum_rule_case_sensitivity(self):
        """Test enum rule case sensitivity."""
        rule = EnumRule({"field": "status", "allowed_values": ["Active", "Inactive"]})
        # Should be case sensitive
        assert rule.validate({"status": "Active"}) is True
        assert rule.validate({"status": "active"}) is False

    def test_enum_rule_multiple_allowed(self):
        """Test enum rule with multiple allowed values."""
        rule = EnumRule({
            "field": "priority",
            "allowed_values": ["low", "medium", "high", "critical"]
        })
        assert rule.validate({"priority": "low"}) is True
        assert rule.validate({"priority": "critical"}) is True
        assert rule.validate({"priority": "urgent"}) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
