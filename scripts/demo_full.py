import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all demos
from .demo_discovery import main as demo_discovery
from .demo_enforcement import main as demo_enforcement
from .demo_marketplace import main as demo_marketplace
from .demo_impact import main as demo_impact

def main():
    print("🚀 DPOS: Full Feature Demo")
    print("=" * 50)
    
    demo_discovery()
    print("\n")
    demo_marketplace()
    print("\n")
    demo_enforcement()
    print("\n")
    demo_impact()
    
    print("\n" + "=" * 50)
    print("✅ Demo Complete.")

if __name__ == "__main__":
    main()