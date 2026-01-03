import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
from src.models import Domain, DataProduct, Schema, Field, Contract, Rule, SLA

# --- DATA DEFINITIONS ---

DOMAINS = [
    Domain(id="DOM001", name="Customer", description="Customer master data", owner="customer-team@company.com", team="Customer Platform"),
    Domain(id="DOM002", name="Order", description="Order processing", owner="order-team@company.com", team="Order Management"),
    Domain(id="DOM003", name="Inventory", description="Product catalog", owner="inventory-team@company.com", team="Supply Chain"),
]

PRODUCTS = [
    DataProduct(id="DP001", name="customer_profiles", title="Customer Profiles", description="Core identity", owner="customer-team@company.com", domain_id="DOM001", type="master"),
    DataProduct(id="DP002", name="customer_transactions", title="Transactions", description="Purchase history", owner="customer-team@company.com", domain_id="DOM001", type="event"),
    DataProduct(id="DP003", name="orders", title="Orders", description="Order records", owner="order-team@company.com", domain_id="DOM002", type="event"),
    DataProduct(id="DP004", name="shipments", title="Shipments", description="Tracking info", owner="order-team@company.com", domain_id="DOM002", type="event"),
    DataProduct(id="DP005", name="inventory_levels", title="Inventory", description="Stock qty", owner="inventory-team@company.com", domain_id="DOM003", type="state"),
    DataProduct(id="DP006", name="product_catalog", title="Catalog", description="Product master", owner="inventory-team@company.com", domain_id="DOM003", type="master"),
]

SCHEMAS = [
    Schema(
        id="schema_dp001_v1", product_id="DP001", version="1.0.0",
        fields=[
            Field(id="f_dp001_cid", name="customer_id", type="string", nullable=False, unique=True, pattern="^CUST[0-9]{6}$"),
            Field(id="f_dp001_email", name="email", type="string", nullable=False, is_pii=True, pii_type="email"),
            Field(id="f_dp001_name", name="name", type="string", nullable=False, is_pii=True, pii_type="name"),
            Field(id="f_dp001_seg", name="segment", type="string", nullable=False, allowed_values=["standard", "premium", "vip"])
        ]
    ),
    Schema(id="schema_dp002_v1", product_id="DP002", version="1.0.0", fields=[]),
    Schema(id="schema_dp003_v1", product_id="DP003", version="1.0.0", fields=[]),
    Schema(id="schema_dp004_v1", product_id="DP004", version="1.0.0", fields=[]),
    Schema(id="schema_dp005_v1", product_id="DP005", version="1.0.0", fields=[]),
    Schema(id="schema_dp006_v1", product_id="DP006", version="1.0.0", fields=[]),
]

CONTRACTS = [
    Contract(
        id="con_dp001", name="Customer Profiles Contract", product_id="DP001",
        rules=[
            Rule(id="r_dp001_01", name="Email Null Rate", type="null_rate", field="email", threshold=0.0, severity="error"),
            Rule(id="r_dp001_02", name="Customer ID Pattern", type="pattern", field="customer_id", pattern="^CUST[0-9]{6}$", severity="error")
        ]
    ),
    Contract(id="con_dp002", name="Transactions Contract", product_id="DP002", rules=[]),
    Contract(id="con_dp003", name="Orders Contract", product_id="DP003", rules=[]),
    Contract(id="con_dp004", name="Shipments Contract", product_id="DP004", rules=[]),
    Contract(id="con_dp005", name="Inventory Contract", product_id="DP005", rules=[]),
    Contract(id="con_dp006", name="Catalog Contract", product_id="DP006", rules=[]),
]

SLAS = [
    SLA(id="sla_dp001", name="Profiles SLA", product_id="DP001", freshness_seconds=86400, availability_percent=99.9, latency_p99_ms=500),
    SLA(id="sla_dp002", name="Trans SLA", product_id="DP002", freshness_seconds=3600, availability_percent=99.95, latency_p99_ms=200),
    SLA(id="sla_dp003", name="Orders SLA", product_id="DP003", freshness_seconds=300, availability_percent=99.99, latency_p99_ms=100),
    SLA(id="sla_dp004", name="Ship SLA", product_id="DP004", freshness_seconds=3600, availability_percent=99.9, latency_p99_ms=300),
    SLA(id="sla_dp005", name="Inv SLA", product_id="DP005", freshness_seconds=300, availability_percent=99.99, latency_p99_ms=50),
    SLA(id="sla_dp006", name="Prod SLA", product_id="DP006", freshness_seconds=86400, availability_percent=99.9, latency_p99_ms=500),
]

PORTS = {
    "output": [
        {"id": "out_dp001_kafka", "product_id": "DP001", "name": "cust_kafka", "type": "kafka", "topic": "dpos.cust.valid"},
        {"id": "out_dp002_kafka", "product_id": "DP002", "name": "trans_kafka", "type": "kafka", "topic": "dpos.trans.valid"},
        {"id": "out_dp003_kafka", "product_id": "DP003", "name": "orders_kafka", "type": "kafka", "topic": "dpos.orders.valid"},
        {"id": "out_dp005_kafka", "product_id": "DP005", "name": "inv_kafka", "type": "kafka", "topic": "dpos.inv.valid"},
    ],
    "input": [
        {"id": "in_dp001_crm", "product_id": "DP001", "name": "CRM DB", "type": "database", "table_name": "customers"},
        {"id": "in_dp002_pay", "product_id": "DP002", "name": "Payments", "type": "kafka", "topic": "payments.raw"},
        {"id": "in_dp003_chk", "product_id": "DP003", "name": "Checkout", "type": "kafka", "topic": "checkout.raw"},
        {"id": "in_dp005_wms", "product_id": "DP005", "name": "WMS", "type": "database", "table_name": "stock"},
    ]
}

USERS = [
    {"id": "u001", "email": "analyst@comp.com", "name": "Analyst", "role": "consumer"},
    {"id": "u002", "email": "cust-team@comp.com", "name": "Cust Team", "role": "owner"},
]

TAGS = [
    {"name": "PII", "category": "classification", "color": "#FF0000"},
    {"name": "Critical", "category": "business", "color": "#00FF00"},
    {"name": "GDPR", "category": "compliance", "color": "#0000FF"}
]

PIPELINES = [
    {"id": "pipe_dp001", "name": "Cust Sync", "type": "batch", "status": "active"},
    {"id": "pipe_dp003", "name": "Order Stream", "type": "streaming", "status": "active"}
]

LINEAGE = [
    ("DP001", "DP003"), # Orders consume Customer Profiles
    ("DP002", "DP003"), # Orders consume Transactions
    ("DP003", "DP004"), # Shipments consume Orders
]

# --- MAIN EXECUTION ---

def main():
    print("🚀 Starting DPOS Phase 1 Initialization...")
    
    manager = Neo4jManager()
    
    try:
        # 1. Init Schema
        manager.init_schema()
        
        # 2. Load Core Data
        print("📥 Loading Domains...")
        for d in DOMAINS: manager.create_domain(d)
        
        print("📥 Loading Products...")
        for p in PRODUCTS: manager.create_product(p)
        
        print("📥 Loading Schemas & Fields...")
        for s in SCHEMAS: manager.create_schema(s)
        
        # 3. Load Governance
        print("📥 Loading Contracts & SLAs...")
        for i, c in enumerate(CONTRACTS):
            manager.create_contract(c, SLAS[i])
            
        # 4. Load Infrastructure
        print("📥 Loading Ports...")
        for port_data in PORTS['output']: manager.create_port('output', port_data['product_id'], port_data)
        for port_data in PORTS['input']: manager.create_port('input', port_data['product_id'], port_data)
        
        # 5. Load Users
        print("📥 Loading Users...")
        for u in USERS: manager.create_user(u)
        
        # 6. Load Tags
        print("📥 Loading Tags...")
        for t in TAGS: manager.create_tag(t)
        
        # 7. Load Pipelines
        print("📥 Loading Pipelines...")
        for p in PIPELINES: manager.create_pipeline(p)
        
        # 8. Load Lineage
        print("📥 Loading Lineage...")
        for up, down in LINEAGE: manager.create_lineage(up, down)
        
        print("✅ Phase 1 Complete! Graph populated with base entities.")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()

if __name__ == "__main__":
    main()