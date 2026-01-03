from langchain_core.tools import tool
from src.contracts.validator import ContractValidator


@tool
def trigger_validation(product_id: str) -> str:
    """Validate a data product by ID."""
    try:
        v = ContractValidator(product_id)
        # Mock validation on empty list
        r = v.validate_batch([])
        return f"Validation Triggered for {product_id}: {r.result}"
    except Exception as e:
        return str(e)


# Export the tool for convenience
validation_tool = trigger_validation