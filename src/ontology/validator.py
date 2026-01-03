"""
Ontology Validator
Validates data against the DPOS ontology schema.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.ontology.loader import get_ontology, PropertyDef


@dataclass
class ValidationError:
    """A validation error."""
    field: str
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]


class OntologyValidator:
    """Validates data against the DPOS ontology."""

    def __init__(self):
        self.ontology = get_ontology()

    def validate_node(self, node_type: str, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a node's data against its ontology definition.

        Args:
            node_type: The type of node (e.g., 'DataProduct')
            data: The node's properties as a dictionary

        Returns:
            ValidationResult with any errors or warnings
        """
        errors = []
        warnings = []

        node_def = self.ontology.get_node(node_type)
        if not node_def:
            errors.append(ValidationError(
                field="node_type",
                message=f"Unknown node type: {node_type}"
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Check required properties
        for prop_name, prop_def in node_def.properties.items():
            if prop_def.required and prop_name not in data:
                errors.append(ValidationError(
                    field=prop_name,
                    message=f"Required property '{prop_name}' is missing"
                ))
            elif prop_name in data:
                # Validate property value
                prop_errors = self._validate_property(prop_def, data[prop_name])
                errors.extend(prop_errors)

        # Check for unknown properties
        known_props = set(node_def.properties.keys())
        for prop_name in data.keys():
            if prop_name not in known_props:
                warnings.append(ValidationError(
                    field=prop_name,
                    message=f"Unknown property '{prop_name}' for {node_type}",
                    severity="warning"
                ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_property(self, prop_def: PropertyDef, value: Any) -> List[ValidationError]:
        """Validate a single property value."""
        errors = []

        if value is None:
            return errors

        # Type validation
        type_valid = self._check_type(prop_def.type, value)
        if not type_valid:
            errors.append(ValidationError(
                field=prop_def.name,
                message=f"Property '{prop_def.name}' should be {prop_def.type}, got {type(value).__name__}"
            ))
            return errors

        # Enum validation
        if prop_def.enum and value not in prop_def.enum:
            errors.append(ValidationError(
                field=prop_def.name,
                message=f"Property '{prop_def.name}' must be one of {prop_def.enum}, got '{value}'"
            ))

        return errors

    def _check_type(self, expected_type: str, value: Any) -> bool:
        """Check if a value matches the expected type."""
        type_mapping = {
            'string': str,
            'integer': int,
            'float': (int, float),
            'boolean': bool,
            'datetime': (str, datetime),
            'array': (list, tuple),
            'json': (dict, list),
        }

        expected = type_mapping.get(expected_type, str)
        return isinstance(value, expected)

    def validate_relationship(
        self,
        source_type: str,
        relationship: str,
        target_type: str
    ) -> ValidationResult:
        """
        Validate that a relationship is valid according to the ontology.

        Args:
            source_type: Source node type
            relationship: Relationship name
            target_type: Target node type

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        source_def = self.ontology.get_node(source_type)
        if not source_def:
            errors.append(ValidationError(
                field="source_type",
                message=f"Unknown source node type: {source_type}"
            ))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        rel_def = source_def.relationships.get(relationship)
        if not rel_def:
            errors.append(ValidationError(
                field="relationship",
                message=f"Unknown relationship '{relationship}' for {source_type}"
            ))
        elif rel_def.target != target_type:
            errors.append(ValidationError(
                field="target_type",
                message=f"Relationship '{relationship}' should target {rel_def.target}, not {target_type}"
            ))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_valid_values(self, node_type: str, property_name: str) -> Optional[List[str]]:
        """
        Get valid enum values for a property.

        Args:
            node_type: The node type
            property_name: The property name

        Returns:
            List of valid values if enum, None otherwise
        """
        node_def = self.ontology.get_node(node_type)
        if not node_def:
            return None

        prop_def = node_def.properties.get(property_name)
        if not prop_def:
            return None

        return prop_def.enum
