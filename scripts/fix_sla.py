import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.manager import Neo4jManager
import json

def main():
    mgr = Neo4jManager()
    
    # 1. Delete existing SLA link for DP001 (Clean Slate)
    print("🗑️  Cleaning up old SLA data for DP001...")
    mgr.execute_query("""
        MATCH (p:DataProduct {id: 'DP001'})-[r:HAS_SLA]->(s:SLA)
        DELETE r, s
    """)
    
    # 2. Reload Data from JSON
    print("📥 Reloading SLA from file...")
    path = "../data/slas/slas.json"
    
    with open(path, 'r') as f:
        slas = json.load(f)
        
    if isinstance(slas, list):
        for sla in slas:
            # Only load DP001 SLA for this fix
            if sla.get('product_id') == 'DP001':
                q = """
                MATCH (p:DataProduct {id: $pid})
                MERGE (s:SLA {id: $id})
                ON CREATE SET s += $props
                ON MATCH SET s += $props
                MERGE (p)-[:HAS_SLA]->(s)
                """
                mgr.execute_query(q, {
                    "pid": sla['product_id'], 
                    "id": sla['id'], 
                    "props": sla
                })
                print(f"   ✅ SLA {sla['id']} linked to DP001 with threshold={sla['max_error_rate']}")
                
    print("✅ SLA Fix Complete. Please restart the demo.")

if __name__ == "__main__":
    main()