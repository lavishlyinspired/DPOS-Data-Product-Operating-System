"""
Pipelines API Routes
Endpoints for managing data pipelines.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.graph.manager import Neo4jManager


router = APIRouter()


class PipelineCreate(BaseModel):
    """Schema for creating a pipeline."""
    id: str
    name: str
    description: Optional[str] = None
    type: Optional[str] = "etl"
    schedule: Optional[str] = None
    source_product_id: Optional[str] = None
    target_product_id: Optional[str] = None


@router.get("")
def list_pipelines():
    """
    List all pipelines.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (pl:Pipeline)
        OPTIONAL MATCH (pl)-[:READS_FROM]->(source:DataProduct)
        OPTIONAL MATCH (pl)-[:WRITES_TO]->(target:DataProduct)
        RETURN pl.id as id, pl.name as name, pl.description as description,
               pl.type as type, pl.schedule as schedule, pl.status as status,
               pl.last_run as last_run, pl.next_run as next_run,
               source.id as source_product_id, source.name as source_product_name,
               target.id as target_product_id, target.name as target_product_name
        ORDER BY pl.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: str):
    """
    Get detailed information about a specific pipeline.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (pl:Pipeline {id: $id})
        OPTIONAL MATCH (pl)-[:READS_FROM]->(source:DataProduct)
        OPTIONAL MATCH (pl)-[:WRITES_TO]->(target:DataProduct)
        RETURN pl.id as id, pl.name as name, pl.description as description,
               pl.type as type, pl.schedule as schedule, pl.status as status,
               pl.last_run as last_run, pl.next_run as next_run,
               pl.config as config,
               source.id as source_product_id, source.name as source_product_name,
               target.id as target_product_id, target.name as target_product_name
        """

        results = mgr.execute_query(query, {"id": pipeline_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")
        return dict(results[0])


@router.post("")
def create_pipeline(pipeline: PipelineCreate):
    """
    Create a new pipeline.
    """
    with Neo4jManager() as mgr:
        query = """
        MERGE (pl:Pipeline {id: $id})
        SET pl.name = $name,
            pl.description = $description,
            pl.type = $type,
            pl.schedule = $schedule,
            pl.status = 'inactive',
            pl.created_at = datetime()
        RETURN pl.id as id, pl.name as name, pl.description as description,
               pl.type as type, pl.schedule as schedule, pl.status as status
        """

        params = pipeline.model_dump()
        results = mgr.execute_query(query, params)

        # Link to source/target products if provided
        if pipeline.source_product_id:
            mgr.execute_query("""
                MATCH (pl:Pipeline {id: $id}), (p:DataProduct {id: $pid})
                MERGE (pl)-[:READS_FROM]->(p)
            """, {"id": pipeline.id, "pid": pipeline.source_product_id})

        if pipeline.target_product_id:
            mgr.execute_query("""
                MATCH (pl:Pipeline {id: $id}), (p:DataProduct {id: $pid})
                MERGE (pl)-[:WRITES_TO]->(p)
            """, {"id": pipeline.id, "pid": pipeline.target_product_id})

        return dict(results[0])


@router.post("/{pipeline_id}/run")
def run_pipeline(pipeline_id: str):
    """
    Trigger a pipeline run.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (pl:Pipeline {id: $id})
        SET pl.status = 'running',
            pl.last_run = datetime()
        RETURN pl.id as id, pl.name as name, pl.status as status,
               pl.last_run as last_run
        """

        results = mgr.execute_query(query, {"id": pipeline_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        # In a real implementation, this would trigger an actual pipeline run
        return {
            "pipeline_id": pipeline_id,
            "status": "running",
            "message": "Pipeline execution started"
        }
