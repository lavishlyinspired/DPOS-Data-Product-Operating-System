"""
DPOS API - Data Product Operating System
Main FastAPI application with security, middleware, and all routes.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Annotated
from contextlib import asynccontextmanager
import json
import csv
import io

from src.core.config import settings
from src.core.logging import get_logger, set_request_context
from src.core.security import get_current_user_optional, TokenData
from src.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware
)

from src.api.routes import products, contracts, lineage, marketplace, metrics, agents
from src.api.routes import intelligence, domains, incidents, pipelines, policies
from src.api.routes import users, tags, slas, auth

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(
        "DPOS API starting",
        extra={
            "environment": settings.environment,
            "version": "2.0.0"
        }
    )

    # Startup: Initialize resources
    try:
        from src.graph.manager import Neo4jManager
        with Neo4jManager() as mgr:
            if mgr.verify_connectivity():
                mgr.init_schema()
                logger.info("Database schema initialized")
            else:
                logger.warning("Neo4j not reachable; skipping schema initialization")
    except Exception as e:
        logger.warning(f"Could not initialize schema: {e}")

    yield

    # Shutdown: Cleanup resources
    logger.info("DPOS API shutting down")


app = FastAPI(
    title="DPOS API",
    description="Data Product Operating System - A comprehensive data mesh governance platform",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# Add middleware (order matters - last added is first executed)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_requests_per_minute,
    burst=settings.rate_limit_burst
)
app.add_middleware(RequestLoggingMiddleware)

# CORS - Use configured origins, not wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-Request-ID", "X-Response-Time"]
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Contracts"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["Incidents"])
app.include_router(lineage.router, prefix="/api/lineage", tags=["Lineage"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["Pipelines"])
app.include_router(policies.router, prefix="/api/policies", tags=["Policies"])
app.include_router(marketplace.router, prefix="/api/marketplace", tags=["Marketplace"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Intelligence"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(tags.router, prefix="/api/tags", tags=["Tags"])
app.include_router(slas.router, prefix="/api/slas", tags=["SLAs"])


@app.get("/")
def root():
    """Root endpoint - basic health check."""
    return {
        "message": "DPOS Running",
        "version": "2.0.0",
        "environment": settings.environment
    }


@app.get("/health")
def health():
    """
    Comprehensive health check endpoint.
    Checks all dependencies and returns detailed status.
    """
    from src.graph.manager import Neo4jManager
    from src.core.llm import get_llm_if_available

    status = {
        "status": "healthy",
        "version": "2.0.0",
        "environment": settings.environment,
        "checks": {
            "api": {"status": "healthy"},
            "database": {"status": "unknown"},
            "llm": {"status": "unknown"},
            "kafka": {"status": "unknown"}
        }
    }

    # Check Neo4j
    try:
        with Neo4jManager() as mgr:
            mgr.execute_query("RETURN 1")
            status["checks"]["database"] = {"status": "healthy", "type": "neo4j"}
    except Exception as e:
        status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e) if not settings.is_production else "Connection failed"
        }
        status["status"] = "degraded"

    # Check LLM
    try:
        llm = get_llm_if_available()
        if llm and llm.is_available:
            status["checks"]["llm"] = {
                "status": "healthy",
                "providers": llm.available_providers
            }
        else:
            status["checks"]["llm"] = {"status": "unavailable"}
    except Exception as e:
        status["checks"]["llm"] = {
            "status": "unhealthy",
            "error": str(e) if not settings.is_production else "Check failed"
        }

    # Check Kafka (optional)
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            request_timeout_ms=5000
        )
        producer.close()
        status["checks"]["kafka"] = {"status": "healthy"}
    except Exception:
        status["checks"]["kafka"] = {"status": "unavailable"}

    return status


@app.get("/api/dashboard/stats")
def dashboard_stats(
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)]
):
    """Get dashboard statistics."""
    from src.graph.manager import Neo4jManager

    stats = {
        "total_products": 0,
        "total_domains": 0,
        "active_contracts": 0,
        "open_incidents": 0,
        "avg_health_score": 0,
        "critical_incidents": 0,
        "healthy_products": 0,
        "degraded_products": 0,
        "recent_activity": []
    }

    try:
        with Neo4jManager() as mgr:
            # Count products
            result = mgr.execute_query("MATCH (p:DataProduct) RETURN count(p) as count")
            if result:
                stats["total_products"] = result[0]["count"]

            # Count domains
            result = mgr.execute_query("MATCH (d:Domain) RETURN count(d) as count")
            if result:
                stats["total_domains"] = result[0]["count"]

            # Count active contracts
            result = mgr.execute_query(
                "MATCH (c:Contract {is_active: true}) RETURN count(c) as count"
            )
            if result:
                stats["active_contracts"] = result[0]["count"]

            # Count open incidents by severity
            result = mgr.execute_query("""
                MATCH (i:Incident {status: 'open'})
                RETURN count(i) as total,
                       count(CASE WHEN i.severity = 'critical' THEN 1 END) as critical
            """)
            if result:
                stats["open_incidents"] = result[0]["total"]
                stats["critical_incidents"] = result[0]["critical"]

            # Calculate health metrics
            result = mgr.execute_query("""
                MATCH (p:DataProduct)
                OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
                WITH p, count(i) as incidents
                RETURN
                    avg(CASE WHEN incidents = 0 THEN 100 ELSE 50 END) as avg_health,
                    count(CASE WHEN incidents = 0 THEN 1 END) as healthy,
                    count(CASE WHEN incidents > 0 THEN 1 END) as degraded
            """)
            if result:
                stats["avg_health_score"] = round(result[0]["avg_health"] or 0)
                stats["healthy_products"] = result[0]["healthy"]
                stats["degraded_products"] = result[0]["degraded"]

            # Recent activity (last 10 incidents)
            result = mgr.execute_query("""
                MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
                RETURN i.id as id, i.type as type, i.severity as severity,
                       i.status as status, i.created_at as timestamp,
                       p.name as product_name
                ORDER BY i.created_at DESC
                LIMIT 10
            """)
            stats["recent_activity"] = [dict(r) for r in result]

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        stats["error"] = "Failed to fetch statistics"

    return stats


@app.get("/api/dashboard/health-by-domain")
def health_by_domain(
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)]
):
    """Get health breakdown by domain."""
    from src.graph.manager import Neo4jManager

    try:
        with Neo4jManager() as mgr:
            result = mgr.execute_query("""
                MATCH (d:Domain)
                OPTIONAL MATCH (d)<-[:IN_DOMAIN]-(p:DataProduct)
                OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
                WITH d, count(DISTINCT p) as products, count(i) as incidents
                RETURN d.id as id, d.name as name,
                       products as product_count,
                       incidents as open_incidents,
                       CASE WHEN incidents = 0 THEN 'healthy' ELSE 'degraded' END as health
                ORDER BY d.name
            """)
            return [dict(r) for r in result]
    except Exception as e:
        logger.error(f"Error fetching health by domain: {e}", exc_info=True)
        return []


# Data Ingestion Endpoints
@app.post("/api/ingest/csv/{product_id}")
async def ingest_csv(
    product_id: str,
    file: UploadFile = File(...),
    validate: bool = True,
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)] = None
):
    """
    Ingest CSV data for a product.
    Optionally validates against the product's contract.
    """
    from src.contracts.validator import ContractValidator

    # Validate file extension
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )

    try:
        decoded = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(decoded))
    records = list(reader)

    result = {
        "product_id": product_id,
        "file_name": file.filename,
        "records_received": len(records),
        "records_valid": 0,
        "records_invalid": 0,
        "validation_errors": []
    }

    if validate:
        try:
            validator = ContractValidator(product_id)
            validation_result = validator.validate_batch(records)
            result["validation_result"] = validation_result
            result["records_valid"] = validation_result.get("valid_count", len(records))
            result["records_invalid"] = validation_result.get("invalid_count", 0)
            result["validation_errors"] = validation_result.get("violations", [])
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            result["validation_error"] = str(e)
    else:
        result["records_valid"] = len(records)

    return result


@app.post("/api/ingest/json/{product_id}")
async def ingest_json(
    product_id: str,
    file: UploadFile = File(...),
    validate: bool = True,
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)] = None
):
    """
    Ingest JSON data for a product.
    Optionally validates against the product's contract.
    """
    from src.contracts.validator import ContractValidator

    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )

    try:
        data = json.loads(contents.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Handle both array and single object
    records = data if isinstance(data, list) else [data]

    result = {
        "product_id": product_id,
        "file_name": file.filename,
        "records_received": len(records),
        "records_valid": 0,
        "records_invalid": 0,
        "validation_errors": []
    }

    if validate:
        try:
            validator = ContractValidator(product_id)
            validation_result = validator.validate_batch(records)
            result["validation_result"] = validation_result
            result["records_valid"] = validation_result.get("valid_count", len(records))
            result["records_invalid"] = validation_result.get("invalid_count", 0)
            result["validation_errors"] = validation_result.get("violations", [])
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            result["validation_error"] = str(e)
    else:
        result["records_valid"] = len(records)

    return result


@app.post("/api/ingest/records/{product_id}")
async def ingest_records(
    product_id: str,
    records: list,
    validate: bool = True,
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)] = None
):
    """
    Ingest records directly for a product.
    """
    from src.contracts.validator import ContractValidator

    # Validate record count
    if len(records) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Too many records. Maximum 10000 per request."
        )

    result = {
        "product_id": product_id,
        "records_received": len(records),
        "records_valid": 0,
        "records_invalid": 0,
        "validation_errors": []
    }

    if validate:
        try:
            validator = ContractValidator(product_id)
            validation_result = validator.validate_batch(records)
            result["validation_result"] = validation_result
            result["records_valid"] = validation_result.get("valid_count", len(records))
            result["records_invalid"] = validation_result.get("invalid_count", 0)
            result["validation_errors"] = validation_result.get("violations", [])
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            result["validation_error"] = str(e)
    else:
        result["records_valid"] = len(records)

    return result


@app.get("/api/search")
def global_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results per category"),
    current_user: Annotated[Optional[TokenData], Depends(get_current_user_optional)] = None
):
    """
    Global search across products, domains, contracts, and incidents.
    """
    from src.graph.manager import Neo4jManager

    results = {
        "query": q,
        "products": [],
        "domains": [],
        "contracts": [],
        "incidents": []
    }

    try:
        with Neo4jManager() as mgr:
            search_term = q.lower()

            # Search products
            result = mgr.execute_query("""
                MATCH (p:DataProduct)
                WHERE toLower(p.name) CONTAINS $search OR toLower(p.description) CONTAINS $search
                RETURN p.id as id, p.name as name, p.description as description, 'product' as type
                LIMIT $limit
            """, {"search": search_term, "limit": limit})
            results["products"] = [dict(r) for r in result]

            # Search domains
            result = mgr.execute_query("""
                MATCH (d:Domain)
                WHERE toLower(d.name) CONTAINS $search OR toLower(d.description) CONTAINS $search
                RETURN d.id as id, d.name as name, d.description as description, 'domain' as type
                LIMIT $limit
            """, {"search": search_term, "limit": limit})
            results["domains"] = [dict(r) for r in result]

            # Search contracts
            result = mgr.execute_query("""
                MATCH (c:Contract)
                WHERE toLower(c.name) CONTAINS $search OR toLower(c.description) CONTAINS $search
                RETURN c.id as id, c.name as name, c.description as description, 'contract' as type
                LIMIT $limit
            """, {"search": search_term, "limit": limit})
            results["contracts"] = [dict(r) for r in result]

            # Search incidents
            result = mgr.execute_query("""
                MATCH (i:Incident)
                WHERE toLower(i.description) CONTAINS $search OR i.id CONTAINS $search
                RETURN i.id as id, i.type as name, i.description as description, 'incident' as type
                LIMIT $limit
            """, {"search": search_term, "limit": limit})
            results["incidents"] = [dict(r) for r in result]

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        results["error"] = "Search failed"

    return results
