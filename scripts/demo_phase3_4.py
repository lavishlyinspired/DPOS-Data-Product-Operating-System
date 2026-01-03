import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator
from src.lineage.impact import ImpactAnalyzer
from src.graph.manager import Neo4jManager

def main():
    print("\n" + "="*60)
    print("🚀 PHASE 3 & 4: Governance & Lineage Demo")
    print("="*60 + "\n")

    # 1. GOVERNANCE DEMO
    print("--- Part 1: Governance (Policy Override) ---")
    
    # We will use DP001 (Customer Profiles). 
    # Base Contract: Email Null Rate is Error.
    # Policy Override (Customer Domain): Email Null Rate becomes CRITICAL.
    
    validator = ContractValidator("DP001")
    
    # Find the email rule
    email_rule = next((r for r in validator.rules if r.get('field') == 'email' and r.get('type') == 'null_rate'), None)
    
    if email_rule:
        print(f"✅ Contract Rule Loaded for Email:")
        print(f"   - Type: {email_rule['type']}")
        print(f"   - Base Severity: error")
        print(f"   - *Effective Severity (Policy Applied): {email_rule['severity']}")
        print(
            f"   - *Effective Enforcement: "
            f"{email_rule.get('enforcement_mode', 'standard')}"
        )

        print("   (Note: Severity changed due to 'pol_cust_pii' policy)")
    else:
        print("❌ Email rule not found.")

    # 2. LINEAGE DEMO
    print("\n--- Part 2: Lineage & Impact Analysis ---")
    
    analyzer = ImpactAnalyzer()
    
    # Scenario: What if 'customer_profiles' (DP001) fails?
    print(f"🔍 Simulating FAILURE on Product: DP001 (customer_profiles)...")
    
    impact = analyzer.analyze_failure_impact("DP001")
    
    print(f"\n📊 IMPACT REPORT:")
    print(f"   - Direct Consumers: {len(impact['downstream_consumers'])}")
    for cons in impact['downstream_consumers']:
        status = "CRITICAL" if cons['is_critical'] else "Standard"
        print(f"     -> {cons['consumer_name']} (ID: {cons['consumer_id']}) [{status}]")
        
    print(f"\n   - Affected Pipelines: {len(impact['affected_pipelines'])}")
    for pipe in impact['affected_pipelines']:
        pipe_name = (
            pipe.get("name")
            or pipe.get("pipeline_name")
            or pipe.get("id")
            or pipe.get("pipeline_id")
            or "unknown_pipeline"
        )

        pipe_status = pipe.get("status", "affected")

        print(f"     -> {pipe_name} (Status: {pipe_status})")

        
    print(f"\n   - Affected Users (Consumers): {impact['affected_users_count']}")
    
    print("\n✅ Phase 3 & 4 Complete.")

if __name__ == "__main__":
    # Ensure Dependencies are met (run load_policies.py and load_pipelines.py first)
    print("👉 Please run 'python scripts/load_policies.py' and 'python scripts/load_pipelines.py' before this demo.")
    main()