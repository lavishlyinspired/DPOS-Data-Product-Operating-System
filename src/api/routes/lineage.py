from fastapi import APIRouter
from src.lineage.engine import LineageEngine

router = APIRouter()

@router.get("/{product_id}/upstream")
def get_upstream(product_id: str):
    le = LineageEngine()
    return le.get_upstream(product_id)

@router.get("/{product_id}/impact")
def get_impact(product_id: str):
    from src.lineage.impact import ImpactAnalyzer
    return ImpactAnalyzer().analyze_failure(product_id)