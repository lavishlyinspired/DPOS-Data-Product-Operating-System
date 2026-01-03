import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.healing_agent import HealingAgent

def main():
    print("🤖 Feature 5: Self-Healing Data Pipelines")
    agent = HealingAgent()
    
    # Create a mock incident
    print("Simulating incident: Pipeline 'pipe_dp001' failure")
    response = agent.diagnose_and_heal("INC_001")
    
    print("Agent Recommendation:")
    print(response)

if __name__ == "__main__":
    main()