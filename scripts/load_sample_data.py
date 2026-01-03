import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.kafka.producer import Producer
import csv
from src.utils.config import Config

def main():
    print("📤 Ingesting Sample Data to Kafka...")
    prod = Producer()
    cfg = Config()
    
    # 1. Good Data
    print("   Publishing Good Data...")
    with open(f"{cfg.data_dir}/good/customers.csv", 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod.send(f"{cfg.topic_raw_prefix}DP001", row)
            
    # 2. Bad Data
    print("   Publishing Bad Data...")
    with open(f"{cfg.data_dir}/bad/customers_bad.csv", 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod.send(f"{cfg.topic_raw_prefix}DP001", row)
            
    print("✅ Ingestion Complete.")

if __name__ == "__main__":
    main()