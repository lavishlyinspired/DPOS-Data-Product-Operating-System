"""Demo: Ontology-guided knowledge extraction (no Neo4j/Kafka/Ollama required).

This is a newbie-friendly script you can run to see real output immediately.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\demo_knowledge_extraction.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.knowledge.document_processor import DocumentProcessor
from src.knowledge.ontology_extractor import OntologyExtractor


def main() -> None:
    text = (
        "We have a data product \"Customer Orders\" in the Sales domain. "
        "It is owned by the Analytics team. "
        "orders_mart consumes from customers_raw."
    )

    doc = DocumentProcessor(chunk_size=500, chunk_overlap=0).process_text(text, source="demo")
    result = OntologyExtractor().extract(doc.chunks)

    print("=== Input Text ===")
    print(text)

    print("\n=== Extracted Entities ===")
    for entity in result.entities:
        print(f"- {entity.entity_type}: {entity.properties} (confidence={entity.confidence})")

    print("\n=== Extracted Relationships ===")
    for rel in result.relationships:
        print(f"- {rel.relationship_type}: {rel.source_entity} -> {rel.target_entity} (confidence={rel.confidence})")

    print("\n=== Warnings ===")
    print(result.warnings)

    print("\n=== Processing Time (seconds) ===")
    print(result.processing_time)


if __name__ == "__main__":
    main()
