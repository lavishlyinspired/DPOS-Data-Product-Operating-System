import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.enforcement.streaming import StreamingEnforcer
from src.kafka.producer import Producer

def main():
    print("Starting Full Demo...")
    producer = Producer()
    
    # Inject Data
    producer.send("dpos.raw.DP001", {"customer_id": "123", "email": "test@test.com"})
    producer.send("dpos.raw.DP001", {"customer_id": "456", "email": None})
    
    # Stream
    enforcer = StreamingEnforcer()
    # In a real script, this would run in a background thread. 
    # For demo, we just print readiness.
    print("Streaming enforcer ready. Monitoring dpos.raw.*")

if __name__ == "__main__":
    main()