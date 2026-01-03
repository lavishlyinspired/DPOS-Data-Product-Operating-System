"""
DPOS Configuration Management
Centralized configuration with environment-specific settings and validation.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with validation."""

    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="", description="Neo4j password")
    neo4j_database: Optional[str] = Field(default=None, description="Neo4j database name")
    neo4j_max_connection_pool_size: int = Field(default=50, description="Max pool size")
    neo4j_connection_timeout: int = Field(default=30, description="Connection timeout in seconds")

    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:9092", description="Kafka servers")

    # LLM - Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3", description="Ollama model name")

    # LLM - OpenAI (alternative)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")

    # LLM - Anthropic (alternative)
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-opus-20240229", description="Anthropic model")

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="CHANGE_THIS_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32",
        description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="Token expiry")

    # API Key (for service-to-service)
    api_key: Optional[str] = Field(default=None, description="API key for service auth")

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=100, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=20, description="Rate limit burst")

    # CORS
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated CORS origins"
    )

    # File Upload
    max_upload_size_mb: int = Field(default=50, description="Max upload size in MB")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = Field(default=None, description="OTEL endpoint")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ['development', 'staging', 'production', 'test']
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function
settings = get_settings()
