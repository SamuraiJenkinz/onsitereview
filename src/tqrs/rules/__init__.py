"""Rules engine for deterministic ticket evaluation.

This module provides rule-based evaluation for ~40% of ticket scoring criteria
that can be assessed without LLM calls, including:
- Short description format validation
- Validation pattern detection (OKTA, phone, chat)
- Critical process detection and compliance
- Category/subcategory validation
"""

from tqrs.rules.base import RuleEvaluator, RuleResult
from tqrs.rules.evaluator import RulesEvaluator

__all__ = [
    "RuleEvaluator",
    "RuleResult",
    "RulesEvaluator",
]
