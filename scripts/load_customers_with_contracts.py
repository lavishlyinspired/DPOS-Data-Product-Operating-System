import sys, os, csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.contracts.validator import ContractValidator
from src.enforcement.engine import EnforcementEngine
from src.config import Config

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
    cfg = Config()
    usecase = os.getenv("DPOS_USECASE", "ecommerce")
    usecase_root = os.path.join(cfg.usecase_dir, usecase)

    good_path = os.path.join(usecase_root, "good", "customers.csv")
    bad_path = os.path.join(usecase_root, "bad", "customers_bad.csv")

    # Alternative COVID file names
    if not os.path.exists(good_path):
        good_path = os.path.join(usecase_root, "good", "outreach_list.csv")
    if not os.path.exists(bad_path):
        bad_path = os.path.join(usecase_root, "bad", "outreach_list_bad.csv")

    # Backward compatible fallbacks
    if not os.path.exists(good_path):
        good_path = os.path.join(cfg.data_dir, "good", "customers.csv")
    if not os.path.exists(bad_path):
        bad_path = os.path.join(cfg.data_dir, "bad", "customers_bad.csv")

    run_load(good_path)
    run_load(bad_path)
