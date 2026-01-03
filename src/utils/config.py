"""
Application Configuration Loader
Loads settings from config/config.yaml and .env files.
"""
import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------
# A number of loader/demo scripts import `Config` from `src.utils.config`, but
# the newer code uses `AppConfig`/`app_config`.
# Expose `Config` as a thin alias to keep those scripts working.
try:
    from src.config import Config  # type: ignore
except Exception:  # pragma: no cover
    Config = None  # type: ignore


class AppConfig:
    """
    Application configuration loaded from YAML and environment variables.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file. Defaults to config/config.yaml
        """
        if config_path is None:
            # Find the project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"

        self._config = {}
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}

        # Initialize settings
        self._init_app_settings()
        self._init_neo4j_settings()
        self._init_kafka_settings()
        self._init_ai_settings()

    def _init_app_settings(self):
        """Initialize app settings."""
        app = self._config.get("app", {})
        self.app_name = app.get("name", "DPOS")
        self.environment = app.get("environment", "development")

    def _init_neo4j_settings(self):
        """Initialize Neo4j settings."""
        neo4j = self._config.get("neo4j", {})
        self.neo4j_uri = os.getenv("NEO4J_URI", neo4j.get("uri", "bolt://localhost:7687"))
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    def _init_kafka_settings(self):
        """Initialize Kafka settings."""
        kafka = self._config.get("kafka", {})
        self.kafka_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            kafka.get("bootstrap_servers", "localhost:9092")
        )
        self.kafka_consumer_group = kafka.get("consumer_group_id", "dpos_streaming_group")
        self.topic_prefix_raw = kafka.get("topic_prefix_raw", "dpos.raw.")
        self.topic_prefix_valid = kafka.get("topic_prefix_valid", "dpos.valid.")
        self.topic_dlq = kafka.get("topic_dlq", "dpos.dlq")

        # Check if Kafka is enabled (disabled if not configured or in test mode)
        self.kafka_enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"

    def _init_ai_settings(self):
        """Initialize AI/LLM settings."""
        ai = self._config.get("ai", {})
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", ai.get("ollama_url", "http://localhost:11434"))
        self.model = ai.get("model", "llama2")
        self.embed_model = ai.get("embed_model", "nomic-embed-text")

    @property
    def enforcement_settings(self):
        """Get enforcement settings."""
        enforcement = self._config.get("enforcement", {})
        return {
            "batch_size": enforcement.get("batch_size", 100),
            "checkpoint_interval_seconds": enforcement.get("checkpoint_interval_seconds", 60),
        }

    @property
    def incident_settings(self):
        """Get incident settings."""
        incidents = self._config.get("incidents", {})
        return {
            "auto_escalate_minutes": incidents.get("auto_escalate_minutes", 15),
            "notification_channel": incidents.get("notification_channel", "#dpos-alerts"),
        }


# Global singleton instance
app_config = AppConfig()

__all__ = ["AppConfig", "app_config", "Config"]
