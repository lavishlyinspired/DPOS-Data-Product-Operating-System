import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator
from src.enforcement.engine import EnforcementEngine
from src.graph.manager import Neo4jManager

# --- SAMPLE DATA ---

# Good Data (Should Pass)
GOOD_DATA = [
    {"customer_id": "CUST000001", "email": "john@example.com", "name": "John Doe", "segment": "premium"},
    {"customer_id": "CUST000002", "email": "jane@test.co", "name": "Jane Smith", "segment": "standard"},
]

# Bad Data (Should Fail: Invalid Email Pattern, Invalid Segment, Null ID)
BAD_DATA = [
    {"customer_id": "CUST000003", "email": "bad-email", "name": "Bad Email User", "segment": "premium"}, # Bad email
    {"customer_id": "CUST000004", "email": "okay@test.com", "name": "Bad Segment User", "segment": "invalid_seg"}, # Bad enum
    {"customer_id": None, "email": "null@test.com", "name": "Null ID", "segment": "standard"}, # Null ID
    {"customer_id": "CUST000006", "email": "valid@test.com", "name": "Valid User", "segment": "vip"},
]

def main():
    print("\n" + "="*50)
    print("🚀 DPOS PHASE 2: Contracts & Enforcement Demo")
    print("="*50 + "\n")

    product_id = "DP001" # customer_profiles
    manager = Neo4jManager()
    
    try:
        # 1. Setup: Ensure Product exists (Assuming Phase 1 was run, but let's verify)
        res = manager.execute_query("MATCH (p:DataProduct {id: $id}) RETURN p", {"id": product_id})
        if not res:
            print("❌ Error: Data Product not found. Please run Phase 1 init script first.")
            return

        # Get Output Port config for demo context
        port_res = manager.execute_query("""
            MATCH (p:DataProduct {id: $id})-[:HAS_OUTPUT_PORT]->(op:OutputPort {type: 'kafka'})
            RETURN op
        """, {"id": product_id})
        
        output_port = dict(port_res[0]["op"]) if port_res else {"topic": "mock.topic"}

        # 2. Instantiate Validator
        print(f"📜 Loading Contract for: {product_id}")
        validator = ContractValidator(product_id)
        print(f"   Loaded {len(validator.rules)} rules.")

        # 3. Test Scenario A: GOOD DATA
        print("\n--- Test Case A: Valid Data Batch ---")
        result = validator.validate_batch(GOOD_DATA)
        EnforcementEngine.execute(result['action'], GOOD_DATA, [], output_port)
        print(f"   Result: {result['result']} ({result['passed']} passed, {result['failed']} failed)")

        # 4. Test Scenario B: BAD DATA (Strict Mode)
        print("\n--- Test Case B: Invalid Data Batch (Strict Enforcement) ---")
        result = validator.validate_batch(BAD_DATA)
        EnforcementEngine.execute(result['action'], [], [], output_port) # Simplified: Assume all failed for block
        print(f"   Result: {result['result']}")
        print(f"   Violations: {len(result['invalid_data'])}")

        # 5. Verify Reports in Graph
        print("\n--- Verifying Reports in Neo4j ---")
        report_res = manager.execute_query("""
            MATCH (p:DataProduct {id: $id})-[:HAS_VALIDATION]->(v:ValidationReport)
            RETURN v.id, v.result, v.timestamp
            ORDER BY v.timestamp DESC
            LIMIT 2
        """, {"id": product_id})
        
        for record in report_res:
            print(f"   📊 Report {record['v.id']}: Status={record['v.result']}, Time={record['v.timestamp']}")

        print("\n✅ Phase 2 Demo Complete.")
        print("   - Rules were loaded from Neo4j.")
        print("   - Data was validated against rules (Null, Pattern, Enum).")
        print("   - Validation Reports were written back to Neo4j.")

    except Exception as e:
        print(f"❌ Demo Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()

if __name__ == "__main__":
    main()