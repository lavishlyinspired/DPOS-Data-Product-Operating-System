from .base import RuleEngine
from typing import Dict, Any

class EnumRule(RuleEngine):
    def validate(self, data: Dict[str, Any]) -> bool:
        allowed = self.config.get('allowed_values', [])
        if not self.field or self.field not in data:
            return True
            
        return data[self.field] in allowed

    def get_error_message(self) -> str:
        return f"Field '{self.field}' must be one of {self.config.get('allowed_values')}."