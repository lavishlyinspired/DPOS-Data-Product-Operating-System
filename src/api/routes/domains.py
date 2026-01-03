"""
Domains API Routes
Endpoints for managing data domains.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class DomainCreate(BaseModel):
    """Schema for creating a domain."""
    id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None


@router.get("")
def list_domains():
    """
    List all domains with product counts.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (d:Domain)
        OPTIONAL MATCH (d)<-[:IN_DOMAIN]-(p:DataProduct)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        WITH d, count(DISTINCT p) as product_count, count(i) as open_incidents
        RETURN d.id as id, d.name as name, d.description as description,
               d.owner as owner, d.created_at as created_at,
               product_count,
               open_incidents,
               CASE WHEN open_incidents = 0 THEN 'healthy' ELSE 'degraded' END as health
        ORDER BY d.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{domain_id}")
def get_domain(domain_id: str):
    """
    Get detailed information about a specific domain.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (d:Domain {id: $id})
        OPTIONAL MATCH (d)<-[:IN_DOMAIN]-(p:DataProduct)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        WITH d, collect(DISTINCT {
            id: p.id,
            name: p.name,
            type: p.type,
            status: p.status
        }) as products, count(i) as open_incidents
        RETURN d.id as id, d.name as name, d.description as description,
               d.owner as owner, d.created_at as created_at,
               products,
               size(products) as product_count,
               open_incidents,
               CASE WHEN open_incidents = 0 THEN 'healthy' ELSE 'degraded' END as health
        """

        results = mgr.execute_query(query, {"id": domain_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Domain {domain_id} not found")
        return dict(results[0])


@router.get("/{domain_id}/products")
def get_domain_products(domain_id: str):
    """
    Get all products in a domain.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (d:Domain {id: $id})<-[:IN_DOMAIN]-(p:DataProduct)
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        WITH p, count(i) as open_incidents
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.status as status, p.owner as owner,
               open_incidents,
               CASE WHEN open_incidents = 0 THEN 'healthy' ELSE 'degraded' END as health
        ORDER BY p.name
        """

        results = mgr.execute_query(query, {"id": domain_id})
        return [dict(r) for r in results]


@router.post("")
def create_domain(domain: DomainCreate):
    """
    Create a new domain.
    """
    with Neo4jManager() as mgr:
        query = """
        MERGE (d:Domain {id: $id})
        SET d.name = $name,
            d.description = $description,
            d.owner = $owner,
            d.created_at = datetime()
        RETURN d.id as id, d.name as name, d.description as description,
               d.owner as owner, d.created_at as created_at
        """

        results = mgr.execute_query(query, domain.model_dump())
        return dict(results[0])
