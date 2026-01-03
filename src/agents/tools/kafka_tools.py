from langchain_core.tools import tool
from src.kafka import Producer
import json


@tool
def send_kafka_message(topic: str, message: str) -> str:
    """Send a message to a Kafka topic. Args: topic, message_json."""
    try:
        Producer().send(topic, json.loads(message))
        return f"Sent to {topic}"
    except Exception as e:
        return str(e)


# Export the tool for convenience
kafka_tool = send_kafka_message
