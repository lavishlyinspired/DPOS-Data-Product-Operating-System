import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.governance.policy_resolver import PolicyResolver
from src.graph.manager import Neo4jManager

def main():
    print("⚖️ Feature 6: Federated Governance")
    
    # Check Email Rule for DP001
    mgr = Neo4jManager()
    base_q = "MATCH (c:Contract {id: 'con_dp001'})-[:HAS_RULE]->(r:Rule {field: 'email'}) RETURN r"
    base_rule = mgr.execute_query(base_q)[0]['r']
    print(f"Base Rule Severity: {base_rule['severity']}")
    
    # Resolve with Policy
    resolver = PolicyResolver()
    resolved = resolver.resolve_policies("DP001", [base_rule])
    
    email_rule = next(r for r in resolved if r['field'] == 'email')
    print(f"Effective Severity (After Policy): {email_rule['severity']}")
    print("(Policy 'pol_cust_dom' overrides severity to 'critical')")

if __name__ == "__main__":
    main()