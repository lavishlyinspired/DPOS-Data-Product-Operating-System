from .base import RuleEngine
from .null_rate import NullRateRule
from .pattern import PatternRule
from .enum import EnumRule

# Map rule types to classes
RULE_REGISTRY = {
    'null_rate': NullRateRule,
    'pattern': PatternRule,
    'enum': EnumRule,
    # Add others as implemented
}

def get_rule_engine(rule_type: str, config: dict) -> RuleEngine:
    engine_class = RULE_REGISTRY.get(rule_type)
    if not engine_class:
        raise ValueError(f"Unknown rule type: {rule_type}")
    return engine_class(config)