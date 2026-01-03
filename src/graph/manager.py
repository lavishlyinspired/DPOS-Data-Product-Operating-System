"""
DPOS Neo4j Database Manager
Enhanced with connection pooling, timeouts, retry logic, and circuit breaker.
"""
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from src.models import *
from src.core.config import settings
from src.core.logging import get_logger
from src.core.resilience import retry, neo4j_circuit, CircuitOpenError
from typing import Optional, List, Dict, Any
import threading

logger = get_logger(__name__)


class Neo4jManager:
    """
    Neo4j database manager with proper session handling.
    Implements connection pooling, timeouts, and resilience patterns.
    """

    _instance: Optional['Neo4jManager'] = None
    _lock = threading.Lock()
    _driver = None

    def __new__(cls):
        """Singleton pattern for connection pooling."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the database connection."""
        self.uri = settings.neo4j_uri
        self.database = settings.neo4j_database
        self.user = settings.neo4j_username
        self.password = settings.neo4j_password

        if not self.password:
            logger.warning("Neo4j password not set, using empty password")
            self.password = ""

        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_timeout=settings.neo4j_connection_timeout,
                connection_acquisition_timeout=30,
                max_transaction_retry_time=30.0
            )
            logger.info(
                "Neo4j driver initialized",
                extra={
                    "uri": self.uri,
                    "database": self.database,
                    "pool_size": settings.neo4j_max_connection_pool_size
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}", exc_info=True)
            raise

    @property
    def driver(self):
        """Get the Neo4j driver instance."""
        if self._driver is None:
            self._initialize()
        return self._driver

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context exit - don't close singleton driver."""
        return False

    def close(self):
        """Close the driver (only call on application shutdown)."""
        if self._driver:
            self._driver.close()
            self._driver = None
            Neo4jManager._instance = None
            logger.info("Neo4j driver closed")

    def verify_connectivity(self) -> bool:
        """Verify database connectivity."""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            return False

    def _is_write_query(self, query: str) -> bool:
        """Determine if query is a write operation."""
        write_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'CALL']
        query_upper = query.upper()
        return any(keyword in query_upper for keyword in write_keywords)

    @retry(max_attempts=3, initial_delay=0.5, retryable_exceptions=(ServiceUnavailable, SessionExpired))
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Execute a Cypher query with retry logic.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        try:
            # Use circuit breaker
            return neo4j_circuit.call(self._execute_query_internal, query, parameters)
        except CircuitOpenError:
            logger.error("Neo4j circuit breaker is open, query rejected")
            raise ServiceUnavailable("Database temporarily unavailable")

    def _execute_query_internal(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Internal query execution."""
        parameters = parameters or {}

        if self._is_write_query(query):
            with self.driver.session(database=self.database) as session:
                result = session.execute_write(
                    lambda tx: [dict(record) for record in tx.run(query, parameters)]
                )
                return result
        else:
            with self.driver.session(database=self.database) as session:
                result = session.execute_read(
                    lambda tx: [dict(record) for record in tx.run(query, parameters)]
                )
                return result

    # Backwards compatibility alias
    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Alias for execute_query (backwards compatibility)."""
        return self.execute_query(query, parameters)

    def execute_query_single(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """Execute query and return single result or None."""
        results = self.execute_query(query, parameters)
        return results[0] if results else None

    def init_schema(self):
        """Initialize database schema with constraints and indexes."""
        queries = [
            # Constraints
            "CREATE CONSTRAINT domain_id IF NOT EXISTS FOR (d:Domain) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:DataProduct) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT schema_id IF NOT EXISTS FOR (s:Schema) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT field_id IF NOT EXISTS FOR (f:Field) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT sla_id IF NOT EXISTS FOR (s:SLA) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT output_port_id IF NOT EXISTS FOR (op:OutputPort) REQUIRE op.id IS UNIQUE",
            "CREATE CONSTRAINT input_port_id IF NOT EXISTS FOR (ip:InputPort) REQUIRE ip.id IS UNIQUE",
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT pipeline_id IF NOT EXISTS FOR (p:Pipeline) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE",

            # Indexes for common queries
            "CREATE INDEX product_name IF NOT EXISTS FOR (p:DataProduct) ON (p.name)",
            "CREATE INDEX product_status IF NOT EXISTS FOR (p:DataProduct) ON (p.status)",
            "CREATE INDEX field_name IF NOT EXISTS FOR (f:Field) ON (f.name)",
            "CREATE INDEX incident_status IF NOT EXISTS FOR (i:Incident) ON (i.status)",
            "CREATE INDEX incident_severity IF NOT EXISTS FOR (i:Incident) ON (i.severity)",
            "CREATE INDEX contract_active IF NOT EXISTS FOR (c:Contract) ON (c.is_active)",
            "CREATE INDEX domain_name IF NOT EXISTS FOR (d:Domain) ON (d.name)",
        ]

        success_count = 0
        for q in queries:
            try:
                self.execute_query(q)
                success_count += 1
            except Exception as e:
                logger.warning(f"Schema query failed (may already exist): {e}")

        logger.info(f"Schema initialized: {success_count}/{len(queries)} queries succeeded")

    def create_domain(self, domain: Domain):
        """Create or update a domain."""
        query = """
        MERGE (d:Domain {id: $id})
        SET d += $props
        RETURN d
        """
        self.execute_query(query, {"id": domain.id, "props": domain.model_dump()})
        logger.debug(f"Domain created/updated: {domain.id}")

    def create_product(self, product: DataProduct):
        """Create or update a data product."""
        query = """
        MATCH (d:Domain {id: $domain_id})
        MERGE (p:DataProduct {id: $id})
        SET p += $props
        MERGE (p)-[:IN_DOMAIN]->(d)
        RETURN p
        """
        self.execute_query(query, {
            "domain_id": product.domain_id,
            "id": product.id,
            "props": product.model_dump()
        })
        logger.debug(f"Product created/updated: {product.id}")

    def create_schema(self, schema_def: Schema):
        """Create or update a schema with fields."""
        # Create Schema Node
        query = """
        MATCH (p:DataProduct {id: $product_id})
        MERGE (s:Schema {id: $id})
        SET s += $props
        MERGE (p)-[:HAS_SCHEMA]->(s)
        RETURN s
        """
        self.execute_query(query, {
            "product_id": schema_def.product_id,
            "id": schema_def.id,
            "props": schema_def.model_dump(exclude={"fields"})
        })

        # Create Fields
        for field in schema_def.fields:
            f_query = """
            MATCH (s:Schema {id: $schema_id})
            MERGE (f:Field {id: $id})
            SET f += $props
            MERGE (s)-[:HAS_FIELD]->(f)
            """
            self.execute_query(f_query, {
                "schema_id": schema_def.id,
                "id": field.id,
                "props": field.model_dump()
            })

        logger.debug(f"Schema created/updated: {schema_def.id} with {len(schema_def.fields)} fields")

    def create_contract(self, contract: Contract, sla: SLA):
        """Create or update a contract with rules and SLA."""
        # Create Contract
        query = """
        MATCH (p:DataProduct {id: $product_id})
        MERGE (c:Contract {id: $id})
        SET c += $props
        MERGE (p)-[:HAS_CONTRACT]->(c)
        RETURN c
        """
        self.execute_query(query, {
            "product_id": contract.product_id,
            "id": contract.id,
            "props": contract.model_dump(exclude={"rules"})
        })

        # Create Rules
        for rule in contract.rules:
            r_query = """
            MATCH (c:Contract {id: $contract_id})
            MERGE (r:Rule {id: $id})
            SET r += $props
            MERGE (c)-[:HAS_RULE]->(r)
            """
            self.execute_query(r_query, {
                "contract_id": contract.id,
                "id": rule.id,
                "props": rule.model_dump()
            })

        # Create SLA
        sla_query = """
        MATCH (c:Contract {id: $contract_id})
        MERGE (s:SLA {id: $id})
        SET s += $props
        MERGE (c)-[:HAS_SLA]->(s)
        """
        self.execute_query(sla_query, {
            "contract_id": contract.id,
            "id": sla.id,
            "props": sla.model_dump()
        })

        logger.debug(f"Contract created/updated: {contract.id} with {len(contract.rules)} rules")

    def create_port(self, port_type: str, product_id: str, port_data: dict):
        """Create an input or output port."""
        label = "InputPort" if port_type == 'input' else "OutputPort"
        query = f"""
        MATCH (p:DataProduct {{id: $product_id}})
        MERGE (port:{label} {{id: $id}})
        SET port += $props
        MERGE (p)-[:HAS_{label.upper()}]->(port)
        """
        self.execute_query(query, {
            "product_id": product_id,
            "id": port_data['id'],
            "props": port_data
        })

    def create_user(self, user_data: dict):
        """Create or update a user."""
        query = """
        MERGE (u:User {id: $id})
        SET u += $props
        """
        self.execute_query(query, {"id": user_data['id'], "props": user_data})

    def create_pipeline(self, pipeline_data: dict):
        """Create or update a pipeline."""
        query = """
        MERGE (p:Pipeline {id: $id})
        SET p += $props
        """
        self.execute_query(query, {"id": pipeline_data['id'], "props": pipeline_data})

    def create_tag(self, tag_data: dict):
        """Create or update a tag."""
        query = """
        MERGE (t:Tag {name: $name})
        SET t += $props
        """
        self.execute_query(query, {"name": tag_data['name'], "props": tag_data})

    def create_lineage(self, upstream_id: str, downstream_id: str):
        """Create lineage relationship between products."""
        query = """
        MATCH (up:DataProduct {id: $up_id})
        MATCH (down:DataProduct {id: $down_id})
        MERGE (down)-[:CONSUMES_FROM]->(up)
        """
        self.execute_query(query, {"up_id": upstream_id, "down_id": downstream_id})

    def create_incident(self, incident_data: dict):
        """Create an incident linked to a product."""
        query = """
        MATCH (p:DataProduct {id: $product_id})
        MERGE (i:Incident {id: $id})
        SET i += $props
        MERGE (p)-[:HAS_INCIDENT]->(i)
        RETURN i
        """
        self.execute_query(query, {
            "product_id": incident_data.get("product_id"),
            "id": incident_data["id"],
            "props": incident_data
        })
        logger.info(f"Incident created: {incident_data['id']}")

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Get a product by ID."""
        query = """
        MATCH (p:DataProduct {id: $id})
        OPTIONAL MATCH (p)-[:IN_DOMAIN]->(d:Domain)
        RETURN p {.*, domain_name: d.name} as product
        """
        result = self.execute_query_single(query, {"id": product_id})
        return result.get("product") if result else None

    def get_downstream_products(self, product_id: str, depth: int = 3) -> List[Dict]:
        """Get downstream products that consume from this product."""
        query = """
        MATCH (p:DataProduct {id: $id})
        MATCH (downstream:DataProduct)-[:CONSUMES_FROM*1..$depth]->(p)
        RETURN DISTINCT downstream {.*} as product,
               length(shortestPath((downstream)-[:CONSUMES_FROM*]->(p))) as distance
        ORDER BY distance
        """
        return self.execute_query(query, {"id": product_id, "depth": depth})

    def get_upstream_products(self, product_id: str, depth: int = 3) -> List[Dict]:
        """Get upstream products that this product consumes from."""
        query = """
        MATCH (p:DataProduct {id: $id})
        MATCH (p)-[:CONSUMES_FROM*1..$depth]->(upstream:DataProduct)
        RETURN DISTINCT upstream {.*} as product,
               length(shortestPath((p)-[:CONSUMES_FROM*]->(upstream))) as distance
        ORDER BY distance
        """
        return self.execute_query(query, {"id": product_id, "depth": depth})
