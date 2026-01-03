import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator

def main():
    print("🧪 Contract Test: DP001")

    validator = ContractValidator("DP001")

    test_batch = [
        # ✅ valid
        {"customer_id": "C001", "email": "good@test.com", "name": "Alice"},
        # ❌ null_rate violation
        {"customer_id": None, "email": "bad@test.com", "name": "Bob"},
        # ❌ pattern violation
        {"customer_id": "C003", "email": "not-an-email", "name": "Charlie"},
    ]

    result = validator.validate_batch(test_batch)

    print("\n📊 Test Result")
    print(f"Result     : {result['result']}")
    print(f"Action     : {result['action']}")
    print(f"Valid Rows : {len(result['valid_data'])}")
    print(f"Invalid Rows: {len(result['invalid_data'])}")

    print("\n❌ Invalid Records")
    for row in result["invalid_data"]:
        print(row)

if __name__ == "__main__":
    main()
