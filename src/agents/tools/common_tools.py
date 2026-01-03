"""
Common Tools for DPOS Agents
Shared tool implementations used across multiple agents.
"""
from typing import List
from langchain_core.tools import tool
from datetime import datetime, UTC
import uuid

from src.graph.manager import Neo4jManager


@tool
def get_incident_details(incident_id: str) -> dict:
    """Fetch incident details from Neo4j."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (i:Incident {id: $id})
        OPTIONAL MATCH (p:DataProduct)-[:HAS_INCIDENT]->(i)
        RETURN i.id as id, i.type as type, i.severity as severity,
               i.description as description, i.status as status,
               p.id as product_id, p.name as product_name
        """
        res = mgr.execute_query(q, {"id": incident_id})
        if res:
            return dict(res[0])
        return {"error": f"Incident {incident_id} not found"}


@tool
def get_product_health(product_id: str) -> dict:
    """Get health status and metrics for a data product."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (p:DataProduct {id: $id})
        OPTIONAL MATCH (p)-[:HAS_INCIDENT]->(i:Incident {status: 'open'})
        OPTIONAL MATCH (p)-[:HAS_METRIC]->(m:Metric)
        WITH p, count(DISTINCT i) as open_incidents,
             avg(CASE WHEN m.type = 'quality_score' THEN m.value END) as avg_quality
        RETURN p.id as id, p.name as name, p.status as status,
               open_incidents, coalesce(avg_quality, 100) as quality_score
        """
        res = mgr.execute_query(q, {"id": product_id})
        if res:
            record = dict(res[0])
            health = "healthy" if record.get("open_incidents", 0) == 0 else "degraded"
            return {**record, "health": health}
        return {"error": f"Product {product_id} not found"}


@tool
def get_downstream_impact(product_id: str) -> dict:
    """Analyze downstream impact of a product failure."""
    with Neo4jManager() as mgr:
        # Get downstream consumers
        consumers_q = """
        MATCH (p:DataProduct {id: $id})<-[:CONSUMES_FROM]-(consumer:DataProduct)
        RETURN consumer.id as id, consumer.name as name, consumer.status as status
        """
        consumers = mgr.execute_query(consumers_q, {"id": product_id})

        # Get affected pipelines
        pipelines_q = """
        MATCH (p:DataProduct {id: $id})<-[:READS_FROM|WRITES_TO]-(pipe:Pipeline)
        RETURN pipe.id as id, pipe.name as name, pipe.status as status
        """
        pipelines = mgr.execute_query(pipelines_q, {"id": product_id})

        # Get affected users
        users_q = """
        MATCH (p:DataProduct {id: $id})<-[:CONSUMES]-(u:User)
        RETURN count(u) as count
        """
        users = mgr.execute_query(users_q, {"id": product_id})

        return {
            "product_id": product_id,
            "downstream_consumers": [dict(c) for c in consumers],
            "affected_pipelines": [dict(p) for p in pipelines],
            "affected_users": users[0]["count"] if users else 0
        }


@tool
def check_pipeline_fallback(product_id: str) -> dict:
    """Check if a fallback source is available for a product's pipeline."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (p:DataProduct {id: $id})<-[:WRITES_TO]-(pipe:Pipeline)
        WHERE pipe.has_fallback = true
        RETURN pipe.id as pipeline_id, pipe.name as pipeline_name,
               pipe.fallback_source as fallback_source
        """
        res = mgr.execute_query(q, {"id": product_id})
        if res:
            return {"has_fallback": True, "fallbacks": [dict(r) for r in res]}
        return {"has_fallback": False, "fallbacks": []}


@tool
def activate_fallback(pipeline_id: str) -> dict:
    """Activate fallback source for a pipeline."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (p:Pipeline {id: $id})
        SET p.using_fallback = true, p.fallback_activated_at = datetime()
        RETURN p.id as id, p.fallback_source as source
        """
        res = mgr.execute_query(q, {"id": pipeline_id})
        if res:
            return {"success": True, "message": f"Fallback activated: {res[0]['source']}"}
        return {"success": False, "message": "Pipeline not found"}


@tool
def search_products(query: str) -> List[dict]:
    """Search for data products by name or description."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (p:DataProduct)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
        RETURN p.id as id, p.name as name, p.description as description,
               p.status as status, p.type as type
        LIMIT 10
        """
        res = mgr.execute_query(q, {"query": query})
        return [dict(r) for r in res]


@tool
def get_contract_rules(product_id: str) -> List[dict]:
    """Get active contract rules for a product."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (p:DataProduct {id: $id})-[:HAS_CONTRACT]->(c:Contract)-[:HAS_RULE]->(r:Rule)
        WHERE c.is_active = true AND r.enabled = true
        RETURN r.id as id, r.name as name, r.type as type,
               r.field as field, r.severity as severity
        """
        res = mgr.execute_query(q, {"id": product_id})
        return [dict(r) for r in res]


@tool
def record_agent_execution(incident_id: str, agent_name: str, outcome: str) -> dict:
    """Record an agent execution in Neo4j."""
    with Neo4jManager() as mgr:
        exec_id = f"AG_{uuid.uuid4().hex[:8]}"
        q = """
        MATCH (i:Incident {id: $iid})
        MERGE (a:AgentExecution {id: $aid})
        SET a.agent = $agent, a.outcome = $outcome, a.created_at = datetime()
        MERGE (i)-[:HANDLED_BY]->(a)
        RETURN a.id as id
        """
        mgr.execute_query(q, {
            "iid": incident_id,
            "aid": exec_id,
            "agent": agent_name,
            "outcome": outcome
        })
        return {"execution_id": exec_id, "recorded": True}


@tool
def update_incident_status(incident_id: str, status: str, resolution: str = None) -> dict:
    """Update incident status in Neo4j."""
    with Neo4jManager() as mgr:
        q = """
        MATCH (i:Incident {id: $id})
        SET i.status = $status, i.updated_at = datetime()
        """
        if resolution:
            q = """
            MATCH (i:Incident {id: $id})
            SET i.status = $status, i.resolution = $resolution, i.updated_at = datetime()
            """
        mgr.execute_query(q, {"id": incident_id, "status": status, "resolution": resolution})
        return {"updated": True, "status": status}
