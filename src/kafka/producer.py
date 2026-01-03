import json
import logging
from typing import Any, Dict, Optional

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None

from src.utils.config import app_config

logger = logging.getLogger("DPOSProducer")


class DPOSProducer:
    """
    Kafka producer wrapper with test-safe disable mode.
    """

    def __init__(self, enabled: Optional[bool] = None):
        """
        enabled:
          - True  -> real Kafka
          - False -> mock / no-op (tests, local dev)
          - None  -> read from config
        """
        self.enabled = (
            enabled
            if enabled is not None
            else getattr(app_config, "kafka_enabled", True)
        )

        self.producer = None

        if self.enabled:
            if KafkaProducer is None:
                raise RuntimeError("kafka-python not installed but kafka_enabled=True")

            self.producer = KafkaProducer(
                bootstrap_servers=app_config.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            logger.info("Kafka producer initialized")
        else:
            logger.info("Kafka producer running in MOCK mode")

    # -------------------------------------------------
    # Core send
    # -------------------------------------------------

    def send(self, topic: str, data: Dict[str, Any]):
        if not self.enabled:
            logger.info(f"[MOCK KAFKA] topic={topic} payload={data}")
            return

        self.producer.send(topic, value=data)
        self.producer.flush(timeout=1.0)

    # -------------------------------------------------
    # Backward-compatible aliases
    # -------------------------------------------------

    def publish(self, topic: str, data: Dict[str, Any]):
        self.send(topic, data)

    def publish_valid(self, product_id: str, data: Dict[str, Any]):
        """
        Publish valid records to product-specific topic.
        Example: dpos.valid.DP001
        """
        topic = f"{app_config.topic_prefix_valid}{product_id}"
        self.send(topic, data)

    def publish_dlq(self, product_id: str, data: Dict[str, Any], reason: str):
        """
        Publish invalid records to DLQ.
        """
        payload = {
            "original_data": data,
            "product_id": product_id,
            "reason": reason,
        }
        self.send(app_config.topic_dlq, payload)

    # -------------------------------------------------
    # Cleanup
    # -------------------------------------------------

    def close(self):
        if self.producer:
            self.producer.close()
