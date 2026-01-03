import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import individual loaders (Absolute imports, no dots)
from load_domains import load_domains
from load_products import load_products
from load_schemas import load_schemas
from load_contracts import load_contracts
from load_slas import load_slas
from load_policies import load_policies
from load_ports import load_ports
from load_pipelines import load_pipelines
from load_users import load_users
from load_tags import load_tags
from load_lineage import load_lineage
from src.utils.config import Config

def main():
    print("🚀 DPOS: Complete Data Load Sequence")
    print("="*40)
    
    load_domains()
    load_products()
    load_schemas()
    load_contracts()
    load_slas()
    load_policies()
    load_ports()
    load_pipelines()
    load_users()
    load_tags()
    load_lineage()
    
    print("="*40)
    print("✅ All Data Loaded Successfully")

if __name__ == "__main__":
    main()