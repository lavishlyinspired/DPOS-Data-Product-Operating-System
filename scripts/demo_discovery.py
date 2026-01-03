import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.discovery_agent import DiscoveryAgent

def main():
    print("🔍 Feature 1: Automated Discovery Agent")
    agent = DiscoveryAgent()
    
    # User query
    query = "I need customer PII data"
    print(f"Query: '{query}'")
    print("-" * 30)
    
    result = agent.discover(query)
    print(f"AI Response: {result}")

if __name__ == "__main__":
    main()