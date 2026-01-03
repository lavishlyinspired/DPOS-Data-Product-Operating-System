import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metrics.collector import MetricsCollector
from src.metrics.alerting import AlertingEngine

def main():
    print("📊 Feature: Metrics & Alerting")
    collector = MetricsCollector()
    alerting = AlertingEngine()
    
    product_id = "DP001"
    
    # Simulate High Error Rate (5% breach)
    print(f"Recording Error Rate 5.0% for {product_id}...")
    collector.record(product_id, "error_rate", 5.0)
    
    # Check Alerting
    print("Checking SLAs...")
    alerting.check_sla_breach(product_id, 5.0)
    print("🚨 Incident created in Neo4j if threshold breached.")

if __name__ == "__main__":
    main()