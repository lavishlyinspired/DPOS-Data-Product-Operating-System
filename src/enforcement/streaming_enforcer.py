from src.contracts.validator import ContractValidator
from src.kafka.producer import DPOSProducer
from src.graph.manager import Neo4jManager
from src.utils.config import app_config
import json

class StreamingEnforcer:
    def __init__(self):
        self.manager = Neo4jManager()
        self.producer = DPOSProducer()
        # Cache validators to avoid reloading rules for every message
        self.validators_cache = {}

    def _get_product_id_from_topic(self, topic_name: str):
        """
        Maps 'dpos.raw.DP001' -> 'DP001'
        Uses graph to verify mapping exists.
        """
        prefix = app_config.topic_prefix_raw
        if topic_name.startswith(prefix):
            product_id = topic_name.replace(prefix, "")
            # Verify product exists
            query = "MATCH (p:DataProduct {id: $id}) RETURN p.id"
            res = self.manager.execute_query(query, {"id": product_id})
            if res:
                return product_id
        return None

    def process_message(self, topic: str, message_value: bytes):
        product_id = self._get_product_id_from_topic(topic)
        if not product_id:
            print(f"❌ Unknown topic format or product: {topic}")
            return

        try:
            data = json.loads(message_value)
        except Exception:
            print(f"❌ Invalid JSON format for topic {topic}")
            return

        # Get Validator (Lazy Load)
        if product_id not in self.validators_cache:
            self.validators_cache[product_id] = ContractValidator(product_id)
        
        validator = self.validators_cache[product_id]

        # Validate single record (Batch wrapper adapted)
        result = validator.validate_batch([data])
        
        action = result['action']
        
        if action == "passed":
            self.producer.publish_valid(product_id, data)
        else:
            # Extract first violation reason for DLQ
            violation_reason = "Validation Failed"
            if result['invalid_data']:
                violation_reason = result['invalid_data'][0].get('message', 'Unknown Rule')
            
            self.producer.publish_dlq(product_id, data, violation_reason)
            
            # Return violation info for metrics collection
            return {
                "product_id": product_id,
                "status": "failed",
                "action": action
            }

        return {"product_id": product_id, "status": "passed", "action": action}