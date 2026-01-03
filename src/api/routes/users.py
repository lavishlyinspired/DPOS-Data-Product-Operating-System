"""
Users API Routes
Endpoints for managing users.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class UserCreate(BaseModel):
    """Schema for creating a user."""
    id: str
    name: str
    email: str
    role: Optional[str] = "viewer"


@router.get("")
def list_users():
    """
    List all users.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (u:User)
        OPTIONAL MATCH (u)<-[:OWNED_BY]-(p:DataProduct)
        WITH u, count(p) as products_owned
        RETURN u.id as id, u.name as name, u.email as email,
               u.role as role, u.created_at as created_at,
               products_owned
        ORDER BY u.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{user_id}")
def get_user(user_id: str):
    """
    Get detailed information about a specific user.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (u:User {id: $id})
        OPTIONAL MATCH (u)<-[:OWNED_BY]-(p:DataProduct)
        WITH u, collect({id: p.id, name: p.name, type: p.type}) as owned_products
        RETURN u.id as id, u.name as name, u.email as email,
               u.role as role, u.created_at as created_at,
               owned_products
        """

        results = mgr.execute_query(query, {"id": user_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return dict(results[0])


@router.post("")
def create_user(user: UserCreate):
    """
    Create a new user.
    """
    with Neo4jManager() as mgr:
        query = """
        MERGE (u:User {id: $id})
        SET u.name = $name,
            u.email = $email,
            u.role = $role,
            u.created_at = datetime()
        RETURN u.id as id, u.name as name, u.email as email,
               u.role as role, u.created_at as created_at
        """

        results = mgr.execute_query(query, user.model_dump())
        return dict(results[0])
