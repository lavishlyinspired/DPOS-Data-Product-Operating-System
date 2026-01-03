"""
DPOS Ontology Module
Provides ontology loading, validation, and LLM context generation.
"""

from src.ontology.loader import OntologyLoader, get_ontology
from src.ontology.validator import OntologyValidator

__all__ = ["OntologyLoader", "OntologyValidator", "get_ontology"]
