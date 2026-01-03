"""
Intelligence API Routes
Provides natural language query and knowledge extraction endpoints.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import uuid

from src.agents.cypher_agent import build_cypher_agent
from src.agents.hybrid_qa_agent import build_hybrid_qa_agent
from src.knowledge.document_processor import DocumentProcessor
from src.knowledge.ontology_extractor import OntologyExtractor
from src.agents.checkpointer import get_thread_config


router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class QueryRequest(BaseModel):
    """Natural language query request."""
    question: str
    thread_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response to a natural language query."""
    answer: str
    sources: List[str]
    generated_cypher: Optional[str]
    intent: str
    confidence: float


class ExtractionRequest(BaseModel):
    """Knowledge extraction request."""
    text: str
    source: str = "api"


class ExtractedEntity(BaseModel):
    """An extracted entity."""
    entity_type: str
    properties: dict
    confidence: float
    source_text: str


class ExtractedRelationship(BaseModel):
    """An extracted relationship."""
    relationship_type: str
    source_entity: str
    target_entity: str
    confidence: float


class ExtractionResponse(BaseModel):
    """Response from knowledge extraction."""
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
    warnings: List[str]
    processing_time: float


class CypherRequest(BaseModel):
    """Direct Cypher execution request."""
    question: str
    thread_id: Optional[str] = None


class CypherResponse(BaseModel):
    """Response from Cypher generation."""
    generated_cypher: str
    results: List[dict]
    answer: str
    is_valid: bool
    confidence: float


# ============================================================================
# AGENTS (lazy loaded)
# ============================================================================

_cypher_agent = None
_hybrid_qa_agent = None


def _get_cypher_agent():
    global _cypher_agent
    if _cypher_agent is None:
        _cypher_agent = build_cypher_agent()
    return _cypher_agent


def _get_hybrid_qa_agent():
    global _hybrid_qa_agent
    if _hybrid_qa_agent is None:
        _hybrid_qa_agent = build_hybrid_qa_agent()
    return _hybrid_qa_agent


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def natural_language_query(request: QueryRequest):
    """
    Execute a natural language query against the DPOS knowledge graph.
    Uses hybrid retrieval (semantic + graph + keyword) for best results.
    """
    agent = _get_hybrid_qa_agent()

    thread_id = request.thread_id or f"query_{uuid.uuid4().hex[:8]}"
    config = get_thread_config(thread_id)

    initial_state = {
        "question": request.question,
        "intent": "",
        "confidence": 0.0,
        "entities": [],
        "semantic_results": [],
        "graph_results": [],
        "keyword_results": [],
        "fused_results": [],
        "sources_used": [],
        "answer": "",
        "citations": [],
        "generated_cypher": "",
        "status": "new"
    }

    try:
        result = agent.invoke(initial_state, config)

        return QueryResponse(
            answer=result.get("answer", "No answer generated"),
            sources=result.get("citations", []),
            generated_cypher=result.get("generated_cypher"),
            intent=result.get("intent", "unknown"),
            confidence=result.get("confidence", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cypher", response_model=CypherResponse)
async def generate_cypher(request: CypherRequest):
    """
    Generate and execute a Cypher query from natural language.
    Returns both the generated query and results.
    """
    agent = _get_cypher_agent()

    thread_id = request.thread_id or f"cypher_{uuid.uuid4().hex[:8]}"
    config = get_thread_config(thread_id)

    initial_state = {
        "question": request.question,
        "ontology_context": "",
        "intent": "",
        "entities": [],
        "generated_cypher": "",
        "is_valid": False,
        "validation_error": "",
        "query_result": [],
        "natural_answer": "",
        "confidence": 0.0,
        "status": "new"
    }

    try:
        result = agent.invoke(initial_state, config)

        return CypherResponse(
            generated_cypher=result.get("generated_cypher", ""),
            results=result.get("query_result", []),
            answer=result.get("natural_answer", ""),
            is_valid=result.get("is_valid", False),
            confidence=result.get("confidence", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract", response_model=ExtractionResponse)
async def extract_knowledge(request: ExtractionRequest):
    """
    Extract structured knowledge from unstructured text.
    Uses the DPOS ontology to guide extraction.
    """
    processor = DocumentProcessor()
    extractor = OntologyExtractor()

    try:
        # Process text into chunks
        doc = processor.process_text(request.text, request.source)

        # Extract knowledge
        result = extractor.extract(doc.chunks)

        # Convert to response format
        entities = [
            ExtractedEntity(
                entity_type=e.entity_type,
                properties=e.properties,
                confidence=e.confidence,
                source_text=e.source_text
            )
            for e in result.entities
        ]

        relationships = [
            ExtractedRelationship(
                relationship_type=r.relationship_type,
                source_entity=r.source_entity,
                target_entity=r.target_entity,
                confidence=r.confidence
            )
            for r in result.relationships
        ]

        return ExtractionResponse(
            entities=entities,
            relationships=relationships,
            warnings=result.warnings,
            processing_time=result.processing_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights():
    """
    Get automated governance insights.
    Returns trends, anomalies, and recommendations.
    """
    from src.graph.manager import Neo4jManager

    insights = {
        "generated_at": None,
        "health_summary": {},
        "trends": [],
        "recommendations": []
    }

    try:
        with Neo4jManager() as mgr:
            # Health summary
            health_query = """
            MATCH (p:DataProduct)
            OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
            WITH p, count(i) as incidents
            RETURN
                count(p) as total_products,
                sum(CASE WHEN incidents = 0 THEN 1 ELSE 0 END) as healthy,
                sum(CASE WHEN incidents > 0 THEN 1 ELSE 0 END) as degraded
            """
            health = mgr.execute_query(health_query)
            if health:
                insights["health_summary"] = dict(health[0])

            # Critical incidents
            incident_query = """
            MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
            WHERE i.status = 'open' AND i.severity IN ['critical', 'high']
            RETURN count(i) as critical_incidents
            """
            incidents = mgr.execute_query(incident_query)
            if incidents and incidents[0]["critical_incidents"] > 0:
                insights["recommendations"].append({
                    "type": "action",
                    "priority": "high",
                    "message": f"Address {incidents[0]['critical_incidents']} critical/high incidents"
                })

            # Products without contracts
            contract_query = """
            MATCH (p:DataProduct)
            WHERE NOT (p)-[:HAS_CONTRACT]->()
            RETURN count(p) as uncontracted
            """
            contracts = mgr.execute_query(contract_query)
            if contracts and contracts[0]["uncontracted"] > 0:
                insights["recommendations"].append({
                    "type": "governance",
                    "priority": "medium",
                    "message": f"{contracts[0]['uncontracted']} products lack data contracts"
                })

            from datetime import datetime, UTC
            insights["generated_at"] = datetime.now(UTC).isoformat()

    except Exception as e:
        insights["error"] = str(e)

    return insights
