import re
from .base import RuleEngine
from typing import Dict, Any

class PatternRule(RuleEngine):
    def validate(self, data: Dict[str, Any]) -> bool:
        pattern = self.config.get('pattern')
        if not self.field or self.field not in data:
            return True # Skip if field missing (handled by NullRate) or no target
            
        value = str(data[self.field])
        if re.match(pattern, value):
            return True
        return False

    def get_error_message(self) -> str:
        return f"Field '{self.field}' does not match pattern {self.config.get('pattern')}."