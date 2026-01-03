"""
SLAs API Routes
Endpoints for managing Service Level Agreements.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class SLACreate(BaseModel):
    """Schema for creating an SLA."""
    id: str
    name: str
    description: Optional[str] = None
    metrics: Optional[List[dict]] = None
    contract_id: Optional[str] = None


@router.get("")
def list_slas():
    """
    List all SLAs.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (s:SLA)
        OPTIONAL MATCH (c:Contract)-[:HAS_SLA]->(s)
        OPTIONAL MATCH (c)<-[:HAS_CONTRACT]-(p:DataProduct)
        RETURN s.id as id, s.name as name, s.description as description,
               s.target_value as target_value, s.metric_type as metric_type,
               s.threshold as threshold, s.is_active as is_active,
               c.id as contract_id, c.name as contract_name,
               p.id as product_id, p.name as product_name
        ORDER BY s.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{sla_id}")
def get_sla(sla_id: str):
    """
    Get detailed information about a specific SLA.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (s:SLA {id: $id})
        OPTIONAL MATCH (c:Contract)-[:HAS_SLA]->(s)
        OPTIONAL MATCH (c)<-[:HAS_CONTRACT]-(p:DataProduct)
        RETURN s.id as id, s.name as name, s.description as description,
               s.target_value as target_value, s.metric_type as metric_type,
               s.threshold as threshold, s.is_active as is_active,
               s.created_at as created_at,
               c.id as contract_id, c.name as contract_name,
               p.id as product_id, p.name as product_name
        """

        results = mgr.execute_query(query, {"id": sla_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"SLA {sla_id} not found")
        return dict(results[0])


@router.post("")
def create_sla(sla: SLACreate):
    """
    Create a new SLA.
    """
    with Neo4jManager() as mgr:
        query = """
        MERGE (s:SLA {id: $id})
        SET s.name = $name,
            s.description = $description,
            s.is_active = true,
            s.created_at = datetime()
        RETURN s.id as id, s.name as name, s.description as description,
               s.is_active as is_active, s.created_at as created_at
        """

        params = sla.model_dump()
        results = mgr.execute_query(query, params)

        # Link to contract if provided
        if sla.contract_id:
            mgr.execute_query("""
                MATCH (s:SLA {id: $sla_id}), (c:Contract {id: $contract_id})
                MERGE (c)-[:HAS_SLA]->(s)
            """, {"sla_id": sla.id, "contract_id": sla.contract_id})

        return dict(results[0])


@router.get("/{sla_id}/status")
def get_sla_status(sla_id: str):
    """
    Get current status/compliance of an SLA.
    """
    with Neo4jManager() as mgr:
        # In a real implementation, this would check actual metrics
        query = """
        MATCH (s:SLA {id: $id})
        RETURN s.id as id, s.name as name,
               s.target_value as target_value, s.metric_type as metric_type,
               s.threshold as threshold
        """

        results = mgr.execute_query(query, {"id": sla_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"SLA {sla_id} not found")

        sla_data = dict(results[0])
        # Mock compliance check
        sla_data["current_value"] = 99.5
        sla_data["is_compliant"] = True
        sla_data["compliance_percentage"] = 100.0

        return sla_data
