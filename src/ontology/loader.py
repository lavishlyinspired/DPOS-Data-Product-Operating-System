"""
Ontology Loader
Loads and parses the DPOS ontology YAML file for use by agents and validation.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class PropertyDef:
    """Definition of a node property."""
    name: str
    type: str
    required: bool = False
    unique: bool = False
    enum: Optional[List[str]] = None
    default: Any = None
    description: str = ""


@dataclass
class RelationshipDef:
    """Definition of a relationship."""
    name: str
    target: str
    cardinality: str = "many"
    required: bool = False
    description: str = ""


@dataclass
class NodeDef:
    """Definition of a node type."""
    name: str
    description: str
    properties: Dict[str, PropertyDef]
    relationships: Dict[str, RelationshipDef]


class OntologyLoader:
    """Loads and provides access to the DPOS ontology."""

    _instance = None
    _ontology = None

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_ontology(config_path)
        return cls._instance

    def _load_ontology(self, config_path: str = None):
        """Load the ontology from YAML file."""
        if config_path is None:
            # Find config relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "dpos_ontology.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self._ontology = yaml.safe_load(f)

        # Parse into structured objects
        self._nodes: Dict[str, NodeDef] = {}
        self._parse_nodes()

    def _parse_nodes(self):
        """Parse node definitions from raw YAML."""
        for node_name, node_data in self._ontology.get('nodes', {}).items():
            properties = {}
            for prop_name, prop_data in node_data.get('properties', {}).items():
                properties[prop_name] = PropertyDef(
                    name=prop_name,
                    type=prop_data.get('type', 'string'),
                    required=prop_data.get('required', False),
                    unique=prop_data.get('unique', False),
                    enum=prop_data.get('enum'),
                    default=prop_data.get('default'),
                    description=prop_data.get('description', '')
                )

            relationships = {}
            for rel_name, rel_data in node_data.get('relationships', {}).items():
                relationships[rel_name] = RelationshipDef(
                    name=rel_name,
                    target=rel_data.get('target', ''),
                    cardinality=rel_data.get('cardinality', 'many'),
                    required=rel_data.get('required', False),
                    description=rel_data.get('description', '')
                )

            self._nodes[node_name] = NodeDef(
                name=node_name,
                description=node_data.get('description', ''),
                properties=properties,
                relationships=relationships
            )

    @property
    def version(self) -> str:
        """Get ontology version."""
        return self._ontology.get('version', '1.0')

    @property
    def namespace(self) -> str:
        """Get ontology namespace."""
        return self._ontology.get('namespace', 'dpos')

    def get_node_types(self) -> List[str]:
        """Get all node type names."""
        return list(self._nodes.keys())

    def get_node(self, node_type: str) -> Optional[NodeDef]:
        """Get a specific node definition."""
        return self._nodes.get(node_type)

    def get_relationship_types(self) -> List[str]:
        """Get all relationship type names from the ontology."""
        return list(self._ontology.get('relationships', {}).keys())

    def get_query_examples(self) -> Dict[str, Dict]:
        """Get query examples for LLM context."""
        return self._ontology.get('query_examples', {})

    def to_llm_context(self) -> str:
        """
        Generate a context string for LLM prompts.
        Provides a concise overview of the ontology for query generation.
        """
        lines = [
            "# DPOS Knowledge Graph Ontology",
            "",
            "## Node Types:",
        ]

        for node_name, node_def in self._nodes.items():
            lines.append(f"\n### {node_name}")
            lines.append(f"Description: {node_def.description}")

            # Key properties
            props = []
            for prop_name, prop_def in node_def.properties.items():
                prop_str = f"{prop_name}: {prop_def.type}"
                if prop_def.required:
                    prop_str += " (required)"
                if prop_def.enum:
                    prop_str += f" [{', '.join(prop_def.enum)}]"
                props.append(prop_str)

            if props:
                lines.append("Properties: " + ", ".join(props[:5]))
                if len(props) > 5:
                    lines.append(f"  ... and {len(props) - 5} more")

            # Relationships
            if node_def.relationships:
                rels = []
                for rel_name, rel_def in node_def.relationships.items():
                    rels.append(f"-[:{rel_name}]->({rel_def.target})")
                lines.append("Relationships: " + ", ".join(rels))

        # Add query examples
        examples = self.get_query_examples()
        if examples:
            lines.append("\n## Example Cypher Queries:")
            for example_name, example_data in list(examples.items())[:3]:
                lines.append(f"\n### {example_data.get('description', example_name)}")
                lines.append("```cypher")
                lines.append(example_data.get('cypher', '').strip())
                lines.append("```")

        return "\n".join(lines)

    def to_cypher_constraints(self) -> List[str]:
        """
        Generate Cypher constraint statements for Neo4j schema.
        """
        constraints = []

        for node_name, node_def in self._nodes.items():
            for prop_name, prop_def in node_def.properties.items():
                if prop_def.unique:
                    constraints.append(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_name}) "
                        f"REQUIRE n.{prop_name} IS UNIQUE"
                    )

        return constraints


# Global accessor
_ontology_loader = None


def get_ontology() -> OntologyLoader:
    """Get the global ontology loader instance."""
    global _ontology_loader
    if _ontology_loader is None:
        _ontology_loader = OntologyLoader()
    return _ontology_loader
