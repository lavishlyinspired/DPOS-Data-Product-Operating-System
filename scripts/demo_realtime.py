import sys, os, time, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kafka import KafkaConsumer
from src.enforcement.streaming_enforcer import StreamingEnforcer
from src.metrics.collector import MetricsCollector
from src.utils.config import app_config
from src.graph.manager import Neo4jManager
from src.kafka.producer import DPOSProducer

def main():
    print("🌊 Starting DPOS Real-Time Processing Engine...")
    print(f"   Connecting to Kafka: {app_config.kafka_servers}")
    
    # Initialize Components
    enforcer = StreamingEnforcer()
    metrics = MetricsCollector()
    producer = DPOSProducer() # Used to inject test data
    manager = Neo4jManager()

    # 1. Setup Kafka Consumer
    consumer = KafkaConsumer(
        bootstrap_servers=app_config.kafka_servers,
        group_id=app_config.kafka_group_id,
        auto_offset_reset='latest',
        value_deserializer=lambda x: x.decode('utf-8')
    )
    
    # Subscribe to all raw topics
    consumer.subscribe(pattern=f"{app_config.topic_prefix_raw}.*")
    print(f"   Subscribed to topics: {app_config.topic_prefix_raw}*")

    # 2. Background Data Injector (Simulates incoming traffic)
    print("\n📢 Starting Background Data Injector (Simulating Traffic)...")
    raw_topic = f"{app_config.topic_prefix_raw}DP001"
    
    def inject_data():
        # Good Data
        producer.publish(raw_topic, {"customer_id": "CUST9001", "email": "live@test.com", "name": "Live User", "segment": "standard"})
        # Bad Data (Will trigger SLA if sent repeatedly)
        producer.publish(raw_topic, {"customer_id": None, "email": "bad-email", "name": "Bad User", "segment": "unknown"})

    # 3. Main Loop
    print("\n🔄 Processing Loop Started (Ctrl+C to stop)...")
    
    try:
        last_flush = time.time()
        injection_count = 0
        
        while True:
            # Inject dummy data every 2 seconds
            current_time = time.time()
            if current_time - last_flush > 2:
                inject_data()
                injection_count += 1
                print(f"   [Injected] Batch #{injection_count}")
            
            # Poll Kafka
            raw_messages = consumer.poll(timeout_ms=1000)
            
            for topic_partition, messages in raw_messages.items():
                for msg in messages:
                    result = enforcer.process_message(msg.topic, msg.value.encode('utf-8'))
                    
                    if result:
                        metrics.record(result['product_id'], result['status'])

            # Flush Metrics every 10 seconds
            if current_time - last_flush > 10:
                print(f"   [System] Flushing metrics to Neo4j...")
                metrics.flush_metrics_to_graph()
                last_flush = current_time

    except KeyboardInterrupt:
        print("\n⏹️  Stopping Consumer...")
        metrics.flush_metrics_to_graph()
        consumer.close()
        manager.close()
        print("✅ Shutdown Complete.")

if __name__ == "__main__":
    main()