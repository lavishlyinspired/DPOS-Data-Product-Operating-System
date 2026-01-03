import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.qa_agent import QAAgent

def main():
    print("👮 Feature 7: AI Data Steward")
    agent = QAAgent()
    
    question = "Who owns the customer profiles product?"
    print(f"User Question: '{question}'")
    print("-" * 30)
    
    answer = agent.ask(question)
    print(f"Steward Answer: {answer}")

if __name__ == "__main__":
    main()