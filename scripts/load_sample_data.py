import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.kafka.producer import Producer
import csv
from src.utils.config import Config

def main():
    print("📤 Ingesting Sample Data to Kafka...")
    prod = Producer()
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
        good_path = f"{cfg.data_dir}/good/customers.csv"
    if not os.path.exists(bad_path):
        bad_path = f"{cfg.data_dir}/bad/customers_bad.csv"
    
    # 1. Good Data
    print("   Publishing Good Data...")
    with open(good_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod.send(f"{cfg.topic_raw_prefix}DP001", row)
            
    # 2. Bad Data
    print("   Publishing Bad Data...")
    with open(bad_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod.send(f"{cfg.topic_raw_prefix}DP001", row)
            
    print("✅ Ingestion Complete.")

if __name__ == "__main__":
    main()