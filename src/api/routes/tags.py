"""
Tags API Routes
Endpoints for managing tags.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class TagCreate(BaseModel):
    """Schema for creating a tag."""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


@router.get("")
def list_tags():
    """
    List all tags with usage counts.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (t:Tag)
        OPTIONAL MATCH (t)<-[:HAS_TAG]-(p:DataProduct)
        WITH t, count(p) as usage_count
        RETURN t.id as id, t.name as name, t.description as description,
               t.color as color, usage_count
        ORDER BY t.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{tag_id}")
def get_tag(tag_id: str):
    """
    Get detailed information about a specific tag.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (t:Tag {id: $id})
        OPTIONAL MATCH (t)<-[:HAS_TAG]-(p:DataProduct)
        WITH t, collect({id: p.id, name: p.name, type: p.type}) as products
        RETURN t.id as id, t.name as name, t.description as description,
               t.color as color, products
        """

        results = mgr.execute_query(query, {"id": tag_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
        return dict(results[0])


@router.post("")
def create_tag(tag: TagCreate):
    """
    Create a new tag.
    """
    import uuid
    tag_id = f"TAG-{uuid.uuid4().hex[:8].upper()}"

    with Neo4jManager() as mgr:
        query = """
        MERGE (t:Tag {id: $id})
        SET t.name = $name,
            t.description = $description,
            t.color = $color,
            t.created_at = datetime()
        RETURN t.id as id, t.name as name, t.description as description,
               t.color as color, t.created_at as created_at
        """

        params = tag.model_dump()
        params["id"] = tag_id
        results = mgr.execute_query(query, params)
        return dict(results[0])


@router.post("/{tag_id}/apply/{product_id}")
def apply_tag(tag_id: str, product_id: str):
    """
    Apply a tag to a product.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (t:Tag {id: $tag_id}), (p:DataProduct {id: $product_id})
        MERGE (p)-[:HAS_TAG]->(t)
        RETURN t.id as tag_id, p.id as product_id
        """

        results = mgr.execute_query(query, {"tag_id": tag_id, "product_id": product_id})
        if not results:
            raise HTTPException(status_code=404, detail="Tag or product not found")
        return dict(results[0])
