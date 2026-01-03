"""
Contracts API Routes
Endpoints for managing data contracts.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from src.graph.manager import Neo4jManager
from src.contracts.validator import ContractValidator


router = APIRouter()


class RuleCreate(BaseModel):
    """Schema for creating a rule."""
    id: str
    name: str
    type: str
    field: Optional[str] = None
    condition: Optional[str] = None
    expected_value: Optional[str] = None


class ContractCreate(BaseModel):
    """Schema for creating a contract."""
    id: str
    name: str
    description: Optional[str] = None
    version: Optional[str] = "1.0.0"
    product_id: str
    rules: Optional[List[RuleCreate]] = None


@router.get("")
def list_contracts():
    """
    List all contracts.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct)-[:HAS_CONTRACT]->(c:Contract)
        OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
        WITH c, p, count(r) as rule_count
        RETURN c.id as id, c.name as name, c.description as description,
               c.version as version, c.is_active as is_active,
               c.created_at as created_at,
               p.id as product_id, p.name as product_name,
               rule_count
        ORDER BY c.name
        """

        results = mgr.execute_query(query, {})
        return [dict(r) for r in results]


@router.get("/{contract_id}")
def get_contract(contract_id: str):
    """
    Get detailed information about a specific contract.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct)-[:HAS_CONTRACT]->(c:Contract {id: $id})
        OPTIONAL MATCH (c)-[:HAS_RULE]->(r:Rule)
        OPTIONAL MATCH (c)-[:HAS_SLA]->(s:SLA)
        WITH c, p, collect(DISTINCT {
            id: r.id,
            name: r.name,
            type: r.type,
            field: r.field,
            condition: r.condition,
            expected_value: r.expected_value
        }) as rules,
        collect(DISTINCT {
            id: s.id,
            name: s.name,
            target_value: s.target_value
        }) as slas
        RETURN c.id as id, c.name as name, c.description as description,
               c.version as version, c.is_active as is_active,
               c.created_at as created_at,
               p.id as product_id, p.name as product_name,
               rules, slas
        """

        results = mgr.execute_query(query, {"id": contract_id})
        if not results:
            raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
        return dict(results[0])


@router.get("/{contract_id}/rules")
def get_contract_rules(contract_id: str):
    """
    Get all rules for a contract.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (c:Contract {id: $id})-[:HAS_RULE]->(r:Rule)
        RETURN r.id as id, r.name as name, r.type as type,
               r.field as field, r.condition as condition,
               r.expected_value as expected_value,
               r.error_message as error_message
        ORDER BY r.name
        """

        results = mgr.execute_query(query, {"id": contract_id})
        return [dict(r) for r in results]


@router.post("")
def create_contract(contract: ContractCreate):
    """
    Create a new contract for a product.
    """
    with Neo4jManager() as mgr:
        query = """
        MATCH (p:DataProduct {id: $product_id})
        CREATE (c:Contract {
            id: $id,
            name: $name,
            description: $description,
            version: $version,
            is_active: true,
            created_at: datetime()
        })
        CREATE (p)-[:HAS_CONTRACT]->(c)
        RETURN c.id as id, c.name as name, c.description as description,
               c.version as version, c.is_active as is_active,
               p.id as product_id, p.name as product_name
        """

        params = contract.model_dump()
        results = mgr.execute_query(query, params)

        if not results:
            raise HTTPException(status_code=404, detail=f"Product {contract.product_id} not found")

        # Create rules if provided
        if contract.rules:
            for rule in contract.rules:
                mgr.execute_query("""
                    MATCH (c:Contract {id: $contract_id})
                    CREATE (r:Rule {
                        id: $id,
                        name: $name,
                        type: $type,
                        field: $field,
                        condition: $condition,
                        expected_value: $expected_value
                    })
                    CREATE (c)-[:HAS_RULE]->(r)
                """, {
                    "contract_id": contract.id,
                    **rule.model_dump()
                })

        return dict(results[0])


@router.post("/{product_id}/validate")
def validate(product_id: str, data: list):
    """
    Validate data against a product's contract.
    """
    try:
        v = ContractValidator(product_id)
        report = v.validate_batch(data)
        return report
    except Exception as e:
        return {
            "product_id": product_id,
            "valid": False,
            "error": str(e),
            "violations": []
        }


@router.post("/validate")
def validate_data(data: dict):
    """
    Validate data against a specified product's contract.
    """
    product_id = data.get("product_id")
    records = data.get("records", [])

    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")

    try:
        v = ContractValidator(product_id)
        report = v.validate_batch(records)
        return report
    except Exception as e:
        return {
            "product_id": product_id,
            "valid": False,
            "error": str(e),
            "violations": []
        }
