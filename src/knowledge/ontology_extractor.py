"""
Ontology-Guided Knowledge Extractor
Extracts structured entities from text using the DPOS ontology.
Supports hybrid extraction: regex patterns + LLM-based semantic extraction.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, UTC
import re
import uuid
import json
import logging

from src.ontology.loader import get_ontology
from src.knowledge.document_processor import DocumentChunk

logger = logging.getLogger(__name__)

# Try to import LLM components
try:
    from src.core.llm import UnifiedLLM, LLMConfig
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class ExtractedEntity:
    """An entity extracted from text."""
    entity_type: str
    properties: Dict[str, Any]
    confidence: float
    source_chunk: int
    source_text: str
    extraction_method: str


@dataclass
class ExtractedRelationship:
    """A relationship extracted from text."""
    relationship_type: str
    source_entity: str
    target_entity: str
    properties: Dict[str, Any]
    confidence: float
    source_text: str


@dataclass
class ExtractionResult:
    """Result of knowledge extraction."""
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
    warnings: List[str]
    processing_time: float


class OntologyExtractor:
    """
    Extracts knowledge from text using the DPOS ontology as a guide.
    Hybrid approach: regex patterns for structured data + LLM for semantic extraction.
    """

    def __init__(self, use_llm: bool = True):
        self.ontology = get_ontology()
        self.use_llm = use_llm and LLM_AVAILABLE
        self._compile_patterns()
        self._llm = None

        if self.use_llm:
            try:
                config = LLMConfig()
                self._llm = UnifiedLLM(config)
                logger.info("LLM-enhanced extraction enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for extraction: {e}")
                self.use_llm = False

    def _compile_patterns(self):
        """Compile regex patterns for entity extraction."""
        self.patterns = {
            # Data Product patterns
            "DataProduct": [
                r"(?:data\s+product|product)\s+[\"']([^\"']+)[\"']",
                r"(?:the|a)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:data\s+product|product|table|dataset)",
                r"([a-z_]+)\s+(?:table|dataset)",
            ],

            # Owner patterns
            "owner": [
                r"(?:owned\s+by|owner\s+is|managed\s+by)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+team)?)",
                r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(?:owns|manages|is\s+responsible\s+for)",
            ],

            # Domain patterns
            "Domain": [
                r"(?:in\s+the|belongs\s+to|part\s+of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+domain",
                r"([A-Z][a-z]+)\s+domain",
            ],

            # Rule patterns
            "Rule": [
                r"(?:must\s+have|should\s+have|requires?)\s+(?:less\s+than|at\s+most)\s+(\d+(?:\.\d+)?)\s*%?\s+(?:null|missing|empty)",
                r"([a-z_]+)\s+field\s+(?:must|should)\s+(?:be|match|contain)",
                r"(?:pattern|format)\s+[\"']([^\"']+)[\"']",
            ],

            # Relationship patterns (lineage)
            "lineage": [
                r"([a-z_]+)\s+(?:consumes\s+from|reads\s+from|depends\s+on|sources?\s+from)\s+([a-z_]+)",
                r"([a-z_]+)\s+(?:is\s+derived\s+from|comes\s+from|based\s+on)\s+([a-z_]+)",
            ],

            # Incident patterns
            "Incident": [
                r"(?:incident|issue|problem|error)\s+(?:with|in|for)\s+([A-Za-z_]+)",
                r"([A-Za-z_]+)\s+(?:failed|broke|has\s+issues?)",
            ],
        }

    def extract(self, chunks: List[DocumentChunk]) -> ExtractionResult:
        """
        Extract entities and relationships from document chunks.
        Uses hybrid approach: regex patterns + LLM semantic extraction.

        Args:
            chunks: List of document chunks to process

        Returns:
            ExtractionResult with entities and relationships
        """
        start_time = datetime.now(UTC)

        entities = []
        relationships = []
        warnings = []

        for chunk in chunks:
            # Extract entities using regex patterns
            chunk_entities = self._extract_entities(chunk)
            entities.extend(chunk_entities)

            # Extract relationships using regex patterns
            chunk_relationships = self._extract_relationships(chunk)
            relationships.extend(chunk_relationships)

            # LLM-enhanced extraction for complex/ambiguous content
            if self.use_llm and self._llm:
                llm_entities, llm_relationships = self._extract_with_llm(chunk)
                entities.extend(llm_entities)
                relationships.extend(llm_relationships)

        # Deduplicate entities
        entities = self._deduplicate_entities(entities)

        # Validate against ontology
        validation_warnings = self._validate_extractions(entities, relationships)
        warnings.extend(validation_warnings)

        processing_time = (datetime.now(UTC) - start_time).total_seconds()

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            warnings=warnings,
            processing_time=processing_time
        )

    def _extract_with_llm(self, chunk: DocumentChunk) -> tuple:
        """
        Use LLM to extract entities and relationships that regex might miss.
        Focuses on semantic understanding of complex text.
        """
        entities = []
        relationships = []

        if not self._llm:
            return entities, relationships

        # Build ontology context for the LLM
        ontology_context = self._build_ontology_context()

        prompt = f"""Analyze the following text and extract structured data entities and relationships.

ONTOLOGY CONTEXT:
{ontology_context}

TEXT TO ANALYZE:
{chunk.content}

Extract any entities (DataProduct, Domain, Rule, Incident, Contract, SLA) and relationships between them.
Focus on:
1. Implicit ownership or responsibility mentions
2. Complex dependency descriptions
3. Business rules expressed in natural language
4. Quality requirements or thresholds mentioned conversationally
5. Temporal relationships (created after, depends on previous version, etc.)

Return a JSON object with this structure:
{{
    "entities": [
        {{
            "type": "EntityType",
            "name": "entity name",
            "properties": {{"key": "value"}},
            "confidence": 0.0-1.0
        }}
    ],
    "relationships": [
        {{
            "type": "RELATIONSHIP_TYPE",
            "source": "source entity name",
            "target": "target entity name",
            "properties": {{}},
            "confidence": 0.0-1.0
        }}
    ]
}}

Only include entities and relationships you are confident about (confidence > 0.6).
If no entities or relationships are found, return empty arrays.
"""

        try:
            response = self._llm.invoke(
                prompt,
                system_prompt="You are a knowledge extraction expert. Extract structured entities and relationships from text based on the given ontology. Return valid JSON only."
            )

            if response.success and response.content:
                # Parse LLM response
                parsed = self._parse_llm_extraction(response.content, chunk)
                entities = parsed.get("entities", [])
                relationships = parsed.get("relationships", [])

        except Exception as e:
            logger.warning(f"LLM extraction failed for chunk {chunk.chunk_index}: {e}")

        return entities, relationships

    def _build_ontology_context(self) -> str:
        """Build a concise ontology description for LLM context."""
        context_parts = ["Available entity types and their properties:"]

        for node_name, node_def in self.ontology.nodes.items():
            props = ", ".join([
                f"{p}{'*' if prop.required else ''}"
                for p, prop in node_def.properties.items()
            ])
            context_parts.append(f"- {node_name}: {props}")

        context_parts.append("\nAvailable relationship types:")
        for rel_name, rel_def in self.ontology.relationships.items():
            context_parts.append(f"- {rel_name}: {rel_def.source} -> {rel_def.target}")

        return "\n".join(context_parts)

    def _parse_llm_extraction(self, content: str, chunk: DocumentChunk) -> Dict:
        """Parse LLM extraction response into entities and relationships."""
        result = {"entities": [], "relationships": []}

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                return result

            data = json.loads(json_match.group())

            # Process entities
            for entity_data in data.get("entities", []):
                if entity_data.get("confidence", 0) < 0.6:
                    continue

                entity = ExtractedEntity(
                    entity_type=entity_data.get("type", "Unknown"),
                    properties={
                        "name": entity_data.get("name", ""),
                        "id": f"{entity_data.get('type', 'ENT')[:3]}_{uuid.uuid4().hex[:8]}",
                        **entity_data.get("properties", {})
                    },
                    confidence=entity_data.get("confidence", 0.7),
                    source_chunk=chunk.chunk_index,
                    source_text=chunk.content[:100],
                    extraction_method="llm"
                )
                result["entities"].append(entity)

            # Process relationships
            for rel_data in data.get("relationships", []):
                if rel_data.get("confidence", 0) < 0.6:
                    continue

                relationship = ExtractedRelationship(
                    relationship_type=rel_data.get("type", "RELATED_TO"),
                    source_entity=rel_data.get("source", ""),
                    target_entity=rel_data.get("target", ""),
                    properties=rel_data.get("properties", {}),
                    confidence=rel_data.get("confidence", 0.7),
                    source_text=chunk.content[:100]
                )
                result["relationships"].append(relationship)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM extraction response: {e}")
        except Exception as e:
            logger.warning(f"Error processing LLM extraction: {e}")

        return result

    def _extract_entities(self, chunk: DocumentChunk) -> List[ExtractedEntity]:
        """Extract entities from a single chunk."""
        entities = []
        text = chunk.content

        # Extract DataProducts
        data_product_patterns = self.patterns["DataProduct"]
        for i, pattern in enumerate(data_product_patterns):
            # Pattern 0: quoted name after 'data product'/'product' -> case-insensitive
            # Pattern 1: "Capitalized Name data product" -> case-sensitive to avoid matching "a data product"
            # Pattern 2+: other heuristics -> case-insensitive
            flags = re.IGNORECASE if i != 1 else 0
            for match in re.finditer(pattern, text, flags):
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 100:
                    entities.append(ExtractedEntity(
                        entity_type="DataProduct",
                        properties={
                            "name": name,
                            "id": f"DP_{uuid.uuid4().hex[:8]}",
                            "status": "draft"
                        },
                        confidence=0.7,
                        source_chunk=chunk.chunk_index,
                        source_text=match.group(0),
                        extraction_method="pattern"
                    ))

        # Extract Domains
        for pattern in self.patterns["Domain"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                if len(name) > 2:
                    entities.append(ExtractedEntity(
                        entity_type="Domain",
                        properties={
                            "name": name,
                            "id": f"DOM_{uuid.uuid4().hex[:8]}"
                        },
                        confidence=0.6,
                        source_chunk=chunk.chunk_index,
                        source_text=match.group(0),
                        extraction_method="pattern"
                    ))

        # Extract Rules (null rate rules)
        for pattern in self.patterns["Rule"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.lastindex:
                    value = match.group(1)
                    try:
                        threshold = float(value.replace('%', '')) / 100
                        entities.append(ExtractedEntity(
                            entity_type="Rule",
                            properties={
                                "id": f"RULE_{uuid.uuid4().hex[:8]}",
                                "type": "null_rate",
                                "threshold": threshold,
                                "severity": "medium",
                                "enabled": True
                            },
                            confidence=0.8,
                            source_chunk=chunk.chunk_index,
                            source_text=match.group(0),
                            extraction_method="pattern"
                        ))
                    except ValueError:
                        pass

        # Extract owner information and associate with products
        for pattern in self.patterns["owner"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                owner = match.group(1).strip()
                # Find nearby product mentions
                for entity in entities:
                    if entity.entity_type == "DataProduct":
                        entity.properties["owner"] = owner

        return entities

    def _extract_relationships(self, chunk: DocumentChunk) -> List[ExtractedRelationship]:
        """Extract relationships from a single chunk."""
        relationships = []
        text = chunk.content.lower()

        # Extract lineage relationships
        for pattern in self.patterns["lineage"]:
            for match in re.finditer(pattern, text):
                source = match.group(1)
                target = match.group(2)

                relationships.append(ExtractedRelationship(
                    relationship_type="CONSUMES_FROM",
                    source_entity=source,
                    target_entity=target,
                    properties={},
                    confidence=0.7,
                    source_text=match.group(0)
                ))

        return relationships

    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate entities, keeping highest confidence."""
        seen = {}

        for entity in entities:
            key = (entity.entity_type, entity.properties.get("name", "").lower())

            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity

        return list(seen.values())

    def _validate_extractions(
        self,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship]
    ) -> List[str]:
        """Validate extractions against the ontology."""
        warnings = []

        for entity in entities:
            node_def = self.ontology.get_node(entity.entity_type)
            if not node_def:
                warnings.append(f"Unknown entity type: {entity.entity_type}")
                continue

            # Check required properties
            for prop_name, prop_def in node_def.properties.items():
                if prop_def.required and prop_name not in entity.properties:
                    warnings.append(
                        f"Missing required property '{prop_name}' for {entity.entity_type}"
                    )

        return warnings

    def to_cypher_statements(self, result: ExtractionResult) -> List[str]:
        """
        Generate Cypher MERGE statements to insert extracted knowledge.

        Args:
            result: Extraction result

        Returns:
            List of Cypher statements
        """
        statements = []

        for entity in result.entities:
            props = ", ".join(
                f"{k}: ${k}" for k in entity.properties.keys()
            )
            stmt = f"MERGE (n:{entity.entity_type} {{id: $id}}) SET n += {{{props}}}"
            statements.append({
                "query": stmt,
                "params": entity.properties
            })

        for rel in result.relationships:
            stmt = f"""
            MATCH (a {{name: $source_name}})
            MATCH (b {{name: $target_name}})
            MERGE (a)-[r:{rel.relationship_type}]->(b)
            """
            statements.append({
                "query": stmt,
                "params": {
                    "source_name": rel.source_entity,
                    "target_name": rel.target_entity
                }
            })

        return statements
