"""
Policies API Routes
Endpoints for managing governance policies.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""
    id: str
    name: str
    description: Optional[str] = None
    type: str = "governance"
    scope: str = "global"  # global, domain, product
    rules: Optional[List[dict]] = None


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    rules: Optional[List[dict]] = None


@router.get("")
def list_policies(
    scope: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    List all policies with optional filtering.
    """
    with Neo4jManager() as mgr:
        conditions = []
        params = {}

        if scope:
            conditions.append("p.scope = $scope")
            params["scope"] = scope

        if is_active is not None:
            conditions.append("p.is_active = $is_active")
            params["is_active"] = is_active

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
        MATCH (p:Policy)
        {where_clause}
        OPTIONAL MATCH (p)-[:APPLIES_TO]->(d:Domain)
        OPTIONAL MATCH (p)-[:APPLIES_TO]->(dp:DataProduct)
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.scope as scope, p.is_active as is_active,
               p.created_at as created_at, p.updated_at as updated_at,
               collect(DISTINCT d.name) as applied_domains,
               collect(DISTINCT dp.name) as applied_products
        ORDER BY p.name
        """

        results = mgr.execute_query(query, params)
        return [dict(r) for r in results]


@router.get("/{policy_id}")
def get_policy(policy_id: str):
    """
    Get detailed information about a specific policy.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:Policy {id: $id})
        OPTIONAL MATCH (p)-[:HAS_RULE]->(r:PolicyRule)
        OPTIONAL MATCH (p)-[:APPLIES_TO]->(d:Domain)
        OPTIONAL MATCH (p)-[:APPLIES_TO]->(dp:DataProduct)
        WITH p, collect(DISTINCT {
            id: r.id,
            name: r.name,
            type: r.type,
            condition: r.condition,
            action: r.action
        }) as rules,
        collect(DISTINCT d.name) as applied_domains,
        collect(DISTINCT dp.name) as applied_products
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.scope as scope, p.is_active as is_active,
               p.created_at as created_at, p.updated_at as updated_at,
               rules, applied_domains, applied_products
        """

        results = mgr.execute_query(query, {"id": policy_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        return dict(results[0])


@router.post("")
def create_policy(policy: PolicyCreate):
    """
    Create a new policy.
    """
    with Neo4jManager() as mgr:
        query = """
        MERGE (p:Policy {id: $id})
        SET p.name = $name,
            p.description = $description,
            p.type = $type,
            p.scope = $scope,
            p.is_active = true,
            p.created_at = datetime()
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.scope as scope, p.is_active as is_active,
               p.created_at as created_at
        """

        params = policy.model_dump()
        results = mgr.execute_query(query, params)
        return dict(results[0])


@router.patch("/{policy_id}")
def update_policy(policy_id: str, update: PolicyUpdate):
    """
    Update a policy.
    """
    with Neo4jManager() as mgr:
        set_clauses = ["p.updated_at = datetime()"]
        params = {"id": policy_id}

        if update.name:
            set_clauses.append("p.name = $name")
            params["name"] = update.name

        if update.description:
            set_clauses.append("p.description = $description")
            params["description"] = update.description

        if update.is_active is not None:
            set_clauses.append("p.is_active = $is_active")
            params["is_active"] = update.is_active

        query = f"""
        MATCH (p:Policy {{id: $id}})
        SET {', '.join(set_clauses)}
        RETURN p.id as id, p.name as name, p.description as description,
               p.is_active as is_active, p.updated_at as updated_at
        """

        results = mgr.execute_query(query, params)
        if not results:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        return dict(results[0])


@router.post("/{policy_id}/apply")
def apply_policy(policy_id: str, target_type: str, target_id: str):
    """
    Apply a policy to a domain or product.
    """
    with Neo4jManager() as mgr:
        if target_type == "domain":
            query = """
            MATCH (p:Policy {id: $policy_id}), (d:Domain {id: $target_id})
            MERGE (p)-[:APPLIES_TO]->(d)
            RETURN p.id as policy_id, d.id as target_id, 'domain' as target_type
            """
        elif target_type == "product":
            query = """
            MATCH (p:Policy {id: $policy_id}), (dp:DataProduct {id: $target_id})
            MERGE (p)-[:APPLIES_TO]->(dp)
            RETURN p.id as policy_id, dp.id as target_id, 'product' as target_type
            """
        else:
            raise HTTPException(status_code=400, detail="target_type must be 'domain' or 'product'")

        results = mgr.execute_query(query, {"policy_id": policy_id, "target_id": target_id})
        if not results:
            raise HTTPException(status_code=404, detail="Policy or target not found")
        return dict(results[0])
