import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.marketplace.semantic_search import SemanticMarketplace

def main():
    print("🛒 Feature 3: Semantic Marketplace")
    market = SemanticMarketplace()
    
    # Index
    market.index_product("DP001")
    market.index_product("DP003")
    
    # Search
    query = "order history"
    print(f"Searching for: '{query}'")
    results = market.search(query)
    
    for r in results:
        print(f"   - {r['name']} (Score: {r['score']:.2f})")

if __name__ == "__main__":
    main()