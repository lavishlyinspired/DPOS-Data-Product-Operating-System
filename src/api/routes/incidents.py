"""
Incidents API Routes
Endpoints for managing incidents.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import uuid

from src.graph.manager import Neo4jManager
from src.agents.healing_agent import build_healing_agent


router = APIRouter()


class IncidentCreate(BaseModel):
    """Schema for creating an incident."""
    product_id: str
    type: str
    severity: str = "medium"
    description: Optional[str] = None


class IncidentUpdate(BaseModel):
    """Schema for updating an incident."""
    status: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    resolution: Optional[str] = None


@router.get("")
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """
    List all incidents with optional filtering.
    """
    with Neo4jManager() as mgr:
        conditions = []
        params = {"limit": limit}

        if status and status != "all":
            conditions.append("i.status = $status")
            params["status"] = status

        if severity:
            conditions.append("i.severity = $severity")
            params["severity"] = severity

        if product_id:
            conditions.append("p.id = $product_id")
            params["product_id"] = product_id

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
        MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident)
        {where_clause}
        OPTIONAL MATCH (i)-[:HANDLED_BY]->(a:AgentExecution)
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               i.created_at as created_at, i.resolved_at as resolved_at,
               p.id as product_id, p.name as product_name,
               a.action as agent_action, a.status as agent_status
        ORDER BY
            CASE i.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
            i.created_at DESC
        LIMIT $limit
        """

        results = mgr.execute_query(query, params)
        return [dict(r) for r in results]


@router.get("/{incident_id}")
def get_incident(incident_id: str):
    """
    Get detailed information about a specific incident.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i:Incident {id: $id})
        OPTIONAL MATCH (i)-[:HANDLED_BY]->(a:AgentExecution)
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               i.created_at as created_at, i.resolved_at as resolved_at,
               i.resolution as resolution,
               p.id as product_id, p.name as product_name,
               collect({
                   agent: a.agent_type,
                   action: a.action,
                   status: a.status,
                   timestamp: a.created_at
               }) as agent_executions
        """

        results = mgr.execute_query(query, {"id": incident_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        return dict(results[0])


@router.post("")
def create_incident(incident: IncidentCreate):
    """
    Create a new incident for a product.
    """
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct {id: $product_id})
        CREATE (i:Incident {
            id: $incident_id,
            type: $type,
            severity: $severity,
            description: $description,
            status: 'open',
            created_at: datetime()
        })
        CREATE (p)-[:HAS_INCIDENT]->(i)
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.status as status, i.description as description,
               i.created_at as created_at,
               p.id as product_id, p.name as product_name
        """

        params = incident.model_dump()
        params["incident_id"] = incident_id

        results = mgr.execute_query(query, params)
        if not results:
            raise HTTPException(status_code=404, detail=f"Product {incident.product_id} not found")
        return dict(results[0])


@router.post("/{incident_id}/handle")
def handle_incident(incident_id: str, severity: str = "medium"):
    """
    Trigger AI agent to handle an incident.
    """
    try:
        agent = build_healing_agent()
        result = agent.invoke(
            {
                "incident_id": incident_id,
                "severity": severity,
                "recommendation": "",
                "action": "",
                "status": ""
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )

        return {
            "incident_id": incident_id,
            "action": result.get("action", "analyzed"),
            "recommendation": result.get("recommendation", ""),
            "status": result.get("status", "completed")
        }
    except Exception as e:
        return {
            "incident_id": incident_id,
            "action": "error",
            "recommendation": str(e),
            "status": "failed"
        }


@router.patch("/{incident_id}")
def update_incident(incident_id: str, update: IncidentUpdate):
    """
    Update an incident status or details.
    """
    with Neo4jManager() as mgr:
        set_clauses = []
        params = {"id": incident_id}

        if update.status:
            set_clauses.append("i.status = $status")
            params["status"] = update.status
            if update.status == "resolved":
                set_clauses.append("i.resolved_at = datetime()")

        if update.severity:
            set_clauses.append("i.severity = $severity")
            params["severity"] = update.severity

        if update.description:
            set_clauses.append("i.description = $description")
            params["description"] = update.description

        if update.resolution:
            set_clauses.append("i.resolution = $resolution")
            params["resolution"] = update.resolution

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No update fields provided")

        query = f"""
        MATCH (i:Incident {{id: $id}})
        SET {', '.join(set_clauses)}
        RETURN i.id as id, i.status as status, i.severity as severity,
               i.description as description, i.resolution as resolution
        """

        results = mgr.execute_query(query, params)
        if not results:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        return dict(results[0])


@router.get("/stats/summary")
def incident_stats():
    """
    Get incident statistics summary.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (i:Incident)
        WITH
            count(CASE WHEN i.status = 'open' THEN 1 END) as open_count,
            count(CASE WHEN i.status = 'resolved' THEN 1 END) as resolved_count,
            count(CASE WHEN i.status = 'investigating' THEN 1 END) as investigating_count,
            count(CASE WHEN i.severity = 'critical' AND i.status = 'open' THEN 1 END) as critical_open,
            count(CASE WHEN i.severity = 'high' AND i.status = 'open' THEN 1 END) as high_open,
            count(*) as total
        RETURN open_count, resolved_count, investigating_count,
               critical_open, high_open, total
        """

        results = mgr.execute_query(query, {})
        if results:
            return dict(results[0])
        return {
            "open_count": 0,
            "resolved_count": 0,
            "investigating_count": 0,
            "critical_open": 0,
            "high_open": 0,
            "total": 0
        }
