"""
Products API Routes
Endpoints for managing data products.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    id: str
    name: str
    description: Optional[str] = None
    type: Optional[str] = "dataset"
    owner: Optional[str] = None
    domain_id: Optional[str] = None


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None


@router.get("")
def list_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    domain: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """
    List all data products with optional filtering.
    """
    with Neo4jManager() as mgr:
        conditions = []
        params = {"limit": limit, "offset": offset}

        if domain:
            conditions.append("(d.id = $domain OR d.name = $domain)")
            params["domain"] = domain

        if status:
            conditions.append("p.status = $status")
            params["status"] = status

        if search:
            conditions.append("(toLower(p.name) CONTAINS toLower($search) OR toLower(p.description) CONTAINS toLower($search))")
            params["search"] = search

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
        MATCH (p:DataProduct)
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {{status: 'open'}})
        {where_clause}
        WITH p, d, count(i) as open_incidents
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.status as status, p.owner as owner,
               p.created_at as created_at, p.updated_at as updated_at,
               d.name as domain, d.id as domain_id,
               CASE WHEN open_incidents = 0 THEN 'healthy' ELSE 'degraded' END as health,
               open_incidents
        ORDER BY p.name
        SKIP $offset
        LIMIT $limit
        """

        results = mgr.execute_query(query, params)
        return [dict(r) for r in results]


@router.get("/{product_id}")
def get_product(product_id: str):
    """
    Get detailed information about a specific product.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct {id: $id})
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        OPTIONAL MATCH (p)-[:HAS_CONTRACT]->(c:Contract)
        OPTIONAL MATCH (p)-[:HAS_SCHEMA]->(s:Schema)-[:HAS_FIELD]->(f:Field)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        OPTIONAL MATCH (p)-[:OWNED_BY]->(u:User)
        WITH p, d, collect(DISTINCT c) as contracts,
             collect(DISTINCT {name: f.name, type: f.type, required: f.required}) as fields,
             count(DISTINCT i) as open_incidents, u
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.status as status, p.owner as owner,
               p.created_at as created_at, p.updated_at as updated_at,
               d.name as domain, d.id as domain_id,
               size(contracts) as contract_count,
               fields,
               open_incidents,
               CASE WHEN open_incidents = 0 THEN 'healthy' ELSE 'degraded' END as health,
               u.name as owner_name, u.email as owner_email
        """

        results = mgr.execute_query(query, {"id": product_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return dict(results[0])


@router.get("/{product_id}/health")
def get_product_health(product_id: str):
    """
    Get health status and metrics for a product.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct {id: $id})
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident)
        WITH p,
             count(CASE WHEN i.status = 'open' THEN 1 END) as open_incidents,
             count(CASE WHEN i.status = 'resolved' THEN 1 END) as resolved_incidents,
             count(CASE WHEN i.severity = 'critical' AND i.status = 'open' THEN 1 END) as critical_incidents
        OPTIONAL MATCH (p)-[:HAS_CONTRACT]->(c:Contract {is_active: true})-[:HAS_RULE]->(r:Rule)
        WITH p, open_incidents, resolved_incidents, critical_incidents, count(r) as total_rules
        RETURN p.id as id, p.name as name,
               CASE
                   WHEN critical_incidents > 0 THEN 'critical'
                   WHEN open_incidents > 0 THEN 'degraded'
                   ELSE 'healthy'
               END as health_status,
               open_incidents,
               resolved_incidents,
               critical_incidents,
               total_rules,
               CASE
                   WHEN open_incidents = 0 THEN 100
                   WHEN critical_incidents > 0 THEN 25
                   ELSE 75
               END as health_score
        """

        results = mgr.execute_query(query, {"id": product_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return dict(results[0])


@router.get("/{product_id}/contracts")
def get_product_contracts(product_id: str):
    """
    Get all contracts associated with a product.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct {id: $id})-[:HAS_CONTRACT]->(c:Contract)
        OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
        WITH c, collect({
            id: r.id,
            name: r.name,
            type: r.type,
            field: r.field,
            condition: r.condition
        }) as rules
        RETURN c.id as id, c.name as name, c.description as description,
               c.version as version, c.is_active as is_active,
               c.created_at as created_at, rules
        ORDER BY c.name
        """

        results = mgr.execute_query(query, {"id": product_id})
        return [dict(r) for r in results]


@router.get("/{product_id}/incidents")
def get_product_incidents(product_id: str, status: Optional[str] = None):
    """
    Get incidents associated with a product.
    """
    with Neo4jManager() as mgr:
        where_clause = ""
        params = {"id": product_id}

        if status:
            where_clause = "AND i.status = $status"
            params["status"] = status

        query = f"""
        MATCH (p:DataProduct {{id: $id}})-[:HAS_INCIDENT]->(i:Incident)
        WHERE true {where_clause}
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               i.created_at as created_at, i.resolved_at as resolved_at
        ORDER BY
            CASE i.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
            i.created_at DESC
        """

        results = mgr.execute_query(query, params)
        return [dict(r) for r in results]


@router.get("/{product_id}/lineage")
def get_product_lineage(product_id: str, depth: int = Query(3, ge=1, le=10)):
    """
    Get data lineage for a product (upstream and downstream).
    """
    with Neo4jManager() as mgr:
        # Upstream sources
        upstream_query = f"""
        MATCH path = (p:DataProduct {{id: $id}})-[:CONSUMES_FROM*1..{depth}]->(source:DataProduct)
        RETURN DISTINCT source.id as id, source.name as name, length(path) as distance
        ORDER BY distance
        """

        # Downstream consumers
        downstream_query = f"""
        MATCH path = (consumer:DataProduct)-[:CONSUMES_FROM*1..{depth}]->(p:DataProduct {{id: $id}})
        RETURN DISTINCT consumer.id as id, consumer.name as name, length(path) as distance
        ORDER BY distance
        """

        upstream = mgr.execute_query(upstream_query, {"id": product_id})
        downstream = mgr.execute_query(downstream_query, {"id": product_id})

        return {
            "product_id": product_id,
            "upstream": [dict(r) for r in upstream],
            "downstream": [dict(r) for r in downstream]
        }
