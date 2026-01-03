import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.graph.manager import Neo4jManager

PIPELINES = [
    {"id": "pipe_dp001", "name": "Cust Sync", "type": "batch", "reads_from": "in_dp001_crm", "writes_to": "DP001"},
    {"id": "pipe_dp003", "name": "Order Stream", "type": "streaming", "reads_from": "in_dp003_chk", "writes_to": "DP003"},
]

LINEAGE_EDGES = [
    {"up": "DP001", "down": "DP003"}, # Orders use Customer Data
    {"up": "DP002", "down": "DP003"}, # Orders use Transaction Data
]

def main():
    print("🔌 Loading Pipelines & Lineage...")
    manager = Neo4jManager()
    
    try:
        # Create Pipeline Nodes
        for p in PIPELINES:
            manager.execute_query("""
                MERGE (pip:Pipeline {id: $id})
                SET pip += $props
            """, {"id": p['id'], "props": p})
            
            # Link Reads (Input Port)
            manager.execute_query("""
                MATCH (pip:Pipeline {id: $pid}), (ip:InputPort {id: $iid})
                MERGE (pip)-[:READS_FROM]->(ip)
            """, {"pid": p['id'], "iid": p['reads_from']})
            
            # Link Writes (Data Product)
            manager.execute_query("""
                MATCH (pip:Pipeline {id: $pid}), (dp:DataProduct {id: $did})
                MERGE (pip)-[:WRITES_TO]->(dp)
            """, {"pid": p['id'], "did": p['writes_to']})
            
        # Create Lineage Edges
        for edge in LINEAGE_EDGES:
            manager.execute_query("""
                MATCH (up:DataProduct {id: $up}), (down:DataProduct {id: $down})
                MERGE (down)-[:CONSUMES_FROM]->(up)
            """, {"up": edge['up'], "down": edge['down']})
            
        print("✅ Pipelines & Lineage Loaded.")
    finally:
        manager.close()

if __name__ == "__main__":
    main()