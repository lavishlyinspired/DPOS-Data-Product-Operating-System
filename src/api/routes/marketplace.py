from fastapi import APIRouter, Query
from src.marketplace.semantic_search import SemanticMarketplace

router = APIRouter()

@router.get("/search")
def search(q: str = Query(...)):
    return SemanticMarketplace().search(q)