import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator
from src.enforcement.engine import EnforcementEngine
import csv
from src.utils.config import Config

def main():
    print("🛡️ Feature 2: Data Contracts Enforcement")
    cfg = Config()
    
    validator = ContractValidator("DP001")
    engine = EnforcementEngine()
    
    # Load Bad Data
    data = []
    with open(f"{cfg.data_dir}/bad/customers_bad.csv", 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
        
    print(f"Validating {len(data)} records...")
    report = validator.validate_batch(data)

    print(f"Result: {report['result']}")
    print(f"Action: {report['action']}")
    print(f"Invalid Records: {len(report['invalid_data'])}")

    # Execute Action
    engine.execute(report['action'], [], data, {})

if __name__ == "__main__":
    main()