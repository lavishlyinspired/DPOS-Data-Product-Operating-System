import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    _instance = None
    
    def __new__(cls, config_path="config/config.yaml"):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            with open(config_path, 'r') as f:
                cls._instance.config = yaml.safe_load(f)
        return cls._instance


    @property
    def neo4j_uri(self): 
        return self.config.get('neo4j', {}).get('uri', 'bolt://localhost:7687')
    
    @property
    def neo4j_auth(self): 
        # Support both legacy and current env var names.
        username = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
        return (username, os.getenv("NEO4J_PASSWORD", "password"))

    @property
    def data_dir(self): 
        """Base directory for governance definitions (products/contracts/etc).

        Backward compatible:
        - Old layout:   ./data/<category>/...
        - New layout:   ./data/governance/<category>/...
        """

        configured = self.config.get('paths', {}).get('data_dir')
        if configured:
            return configured

        project_root = Path(__file__).resolve().parents[1]
        new_layout = project_root / "data" / "governance"
        if new_layout.exists():
            return str(new_layout)

        return str(project_root / "data")

    @property
    def usecase_dir(self) -> str:
        """Base directory for use-case datasets (CSV/etc)."""

        configured = self.config.get('paths', {}).get('usecase_dir')
        if configured:
            return configured

        project_root = Path(__file__).resolve().parents[1]
        new_layout = project_root / "data" / "usecase"
        if new_layout.exists():
            return str(new_layout)

        # Fallback: historically sample CSVs lived directly under ./data.
        return str(project_root / "data")
    
    @property
    def kafka_servers(self): 
        return self.config.get('kafka', {}).get('bootstrap_servers', 'localhost:9092')
    
    @property
    def kafka_group(self): 
        return self.config.get('kafka', {}).get('consumer_group', 'dpos_group')
    
    @property
    def topic_raw_prefix(self): 
        return self.config.get('kafka', {}).get('topic_raw_prefix', 'dpos.raw.')
    
    @property
    def topic_valid_prefix(self): 
        return self.config.get('kafka', {}).get('topic_valid_prefix', 'dpos.valid.')
    
    @property
    def topic_dlq(self): 
        return self.config.get('kafka', {}).get('topic_dlq', 'dpos.dlq')
    
    @property
    def ollama_url(self): 
        return self.config.get('ai', {}).get('ollama_url', 'http://localhost:11434')
    
    @property
    def ollama_model(self): 
        return self.config.get('ai', {}).get('model', 'llama2')

# Global Accessor
cfg = Config()