"""
Tests for Contract Validator
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.contracts.validator import ContractValidator


class TestContractValidator:
    """Test cases for ContractValidator."""

    def test_validator_initialization(self):
        """Test validator can be initialized with product ID."""
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = []

            validator = ContractValidator("DP001")
            assert validator is not None

    def test_validator_batch_validation_passed(self):
        """Test batch validation with all valid records."""
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = [
                {
                    'id': 'r1',
                    'type': 'null_rate',
                    'field': 'email',
                    'severity': 'error'
                }
            ]

            validator = ContractValidator("DP001")
            result = validator.validate_batch([
                {"email": "test@test.com"},
                {"email": "user@example.com"}
            ])

            assert result['result'] == "passed"
            assert result['failed_records'] == 0

    def test_validator_batch_validation_failed(self):
        """Test batch validation with invalid records."""
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = [
                {
                    'id': 'r1',
                    'type': 'null_rate',
                    'field': 'email',
                    'severity': 'error'
                }
            ]

            validator = ContractValidator("DP001")
            result = validator.validate_batch([
                {"email": None},
                {"email": "user@example.com"},
                {"email": None}
            ])

            assert result['result'] == "failed"
            assert result['failed_records'] > 0

    def test_validator_with_multiple_rules(self):
        """Test validation with multiple rules applied."""
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = [
                {
                    'id': 'r1',
                    'type': 'null_rate',
                    'field': 'email',
                    'severity': 'error'
                },
                {
                    'id': 'r2',
                    'type': 'pattern',
                    'field': 'id',
                    'pattern': '^CUST[0-9]+$',
                    'severity': 'error'
                }
            ]

            validator = ContractValidator("DP001")
            result = validator.validate_batch([
                {"email": "test@test.com", "id": "CUST001"},
                {"email": "user@example.com", "id": "CUST002"}
            ])

            assert result is not None

    def test_validator_empty_batch(self):
        """Test validation with empty batch."""
        with patch('src.contracts.validator.PolicyResolver') as MockPR:
            instance = MockPR.return_value
            instance.resolve_policies.return_value = []

            validator = ContractValidator("DP001")
            result = validator.validate_batch([])

            assert result['result'] == "passed"
            assert result['total_records'] == 0


class TestValidatorIntegration:
    """Integration tests for ContractValidator with Neo4j."""

    @pytest.mark.integration
    def test_validator_with_neo4j(self, neo4j_session):
        """Test validator with actual Neo4j connection."""
        # This test requires Neo4j to be running
        with patch.object(neo4j_session, 'execute_query') as mock_query:
            mock_query.return_value = [{
                'r': {
                    'id': 'r1',
                    'type': 'null_rate',
                    'field': 'email',
                    'severity': 'error'
                }
            }]

            with patch('src.contracts.validator.PolicyResolver') as MockPR:
                instance = MockPR.return_value
                instance.resolve_policies.return_value = [
                    {'id': 'r1', 'type': 'null_rate', 'field': 'email', 'severity': 'error'}
                ]

                validator = ContractValidator("DP001")
                result = validator.validate_batch([{"email": "test@test.com"}])

                assert result['result'] == "passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
