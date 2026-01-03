import sys, os, csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator
from src.enforcement.engine import EnforcementEngine

DATA_DIR = "data"
PRODUCT_ID = "DP001"


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_load(csv_path: str):
    print(f"\n[LOAD] Loading file: {csv_path}")

    data = load_csv(csv_path)
    print(f"Records read: {len(data)}")

    validator = ContractValidator(PRODUCT_ID)
    report = validator.validate_batch(data)

    print("\n[VALIDATION] Result")
    print(f"Result : {report['result']}")
    print(f"Action : {report['action']}")
    print(f"Valid  : {len(report['valid_data'])}")
    print(f"Invalid: {len(report['invalid_data'])}")

    engine = EnforcementEngine()
    engine.enforce(PRODUCT_ID, report)


if __name__ == "__main__":
    run_load(os.path.join(DATA_DIR, "good", "customers.csv"))
    run_load(os.path.join(DATA_DIR, "bad", "customers_bad.csv"))
