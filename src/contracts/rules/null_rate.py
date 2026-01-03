from .base import RuleEngine
from typing import Dict, Any, List


class NullRateRule(RuleEngine):
    """
    Batch-level null rate validation.
    """

    def validate_batch(self, batch: List[Dict[str, Any]]) -> bool:
        threshold = self.config.get("threshold", 0.0)
        field = self.field

        if not field or not batch:
            return True

        null_count = sum(
            1 for row in batch
            if field not in row or row[field] in (None, "")
        )

        null_rate = null_count / len(batch)
        return null_rate <= threshold

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Row-level check is neutral.
        Batch enforcement happens separately.
        """
        return True

    def get_error_message(self) -> str:
        return (
            f"Field '{self.field}' exceeds allowed null rate "
            f"({self.config.get('threshold') * 100}%)."
        )
