import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lineage.impact import ImpactAnalyzer

def main():
    print("📉 Feature 4: Real-Time Lineage & Impact")
    analyzer = ImpactAnalyzer()
    
    # Simulate Failure on DP001
    print("Analyzing failure of DP001 (Customer Profiles)...")
    impact = analyzer.analyze_failure("DP001")
    
    print(f"Affected Products: {len(impact['affected_products'])}")
    for p in impact['affected_products']:
        print(f"   - {p['name']}")
        
    print(f"Affected Pipelines: {len(impact['affected_pipelines'])}")

if __name__ == "__main__":
    main()