from abc import ABC, abstractmethod
from typing import Any, Dict

class RuleEngine(ABC):
    def __init__(self, rule_config: Dict[str, Any]):
        self.config = rule_config
        self.field = rule_config.get('field')
        self.severity = rule_config.get('severity', 'error')

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Returns True if valid, False if invalid.
        """
        pass

    @abstractmethod
    def get_error_message(self) -> str:
        pass