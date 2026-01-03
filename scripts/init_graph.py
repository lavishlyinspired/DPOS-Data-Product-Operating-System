import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.graph.schema import init_constraints


def init_incident_schema(mgr: Neo4jManager):
    queries = [
        """
        CREATE CONSTRAINT incident_id IF NOT EXISTS
        FOR (i:Incident)
        REQUIRE i.id IS UNIQUE
        """,
        """
        CREATE INDEX incident_severity IF NOT EXISTS
        FOR (i:Incident) ON (i.severity)
        """,
        """
        CREATE INDEX incident_status IF NOT EXISTS
        FOR (i:Incident) ON (i.status)
        """
    ]

    for q in queries:
        mgr.execute_query(q)


def init_validation_schema(mgr: Neo4jManager):
    queries = [
        """
        CREATE CONSTRAINT validation_id IF NOT EXISTS
        FOR (v:ValidationReport)
        REQUIRE v.id IS UNIQUE
        """,
        """
        CREATE INDEX validation_product IF NOT EXISTS
        FOR (v:ValidationReport) ON (v.product_id)
        """
    ]

    for q in queries:
        mgr.execute_query(q)


def init_metric_schema(mgr: Neo4jManager):
    queries = [
        """
        CREATE INDEX metric_type IF NOT EXISTS
        FOR (m:Metric) ON (m.type)
        """,
        """
        CREATE INDEX metric_product IF NOT EXISTS
        FOR (m:Metric) ON (m.product_id)
        """
    ]

    for q in queries:
        mgr.execute_query(q)
def init_constraints(mgr):
    mgr.execute_query(
        "CREATE CONSTRAINT incident_id IF NOT EXISTS "
        "FOR (i:Incident) REQUIRE i.id IS UNIQUE"
    )

    mgr.execute_query(
        "CREATE CONSTRAINT agent_exec_id IF NOT EXISTS "
        "FOR (a:AgentExecution) REQUIRE a.id IS UNIQUE"
    )


def main():
    mgr = Neo4jManager()

    # Existing base constraints
    init_constraints(mgr)

    # New schemas required by enforcement & agents
    init_incident_schema(mgr)
    init_validation_schema(mgr)
    init_metric_schema(mgr)

    print("✅ Graph Initialized (constraints, incidents, metrics)")


if __name__ == "__main__":
    main()
