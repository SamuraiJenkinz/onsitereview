"""TQRS Scoring Engine.

Combines rules engine and LLM evaluation results into final 70-point scores.
"""

from tqrs.scoring.batch import (
    BatchProgress,
    BatchResult,
    BatchTicketEvaluator,
    evaluate_tickets,
    evaluate_tickets_async,
)
from tqrs.scoring.calculator import ScoringCalculator, ScoringResult
from tqrs.scoring.evaluator import TicketEvaluator
from tqrs.scoring.formatter import ResultFormatter
from tqrs.scoring.templates import (
    CUSTOMER_SERVICE_CRITERIA,
    INCIDENT_HANDLING_CRITERIA,
    INCIDENT_LOGGING_CRITERIA,
    TEMPLATE_CRITERIA,
    TemplateCriterion,
    get_criterion_by_id,
    get_deduction_criteria,
    get_scoring_criteria,
    get_template_criteria,
    get_template_max_score,
)

__all__ = [
    # Calculator
    "ScoringCalculator",
    "ScoringResult",
    # Evaluator
    "TicketEvaluator",
    # Batch
    "BatchTicketEvaluator",
    "BatchProgress",
    "BatchResult",
    "evaluate_tickets",
    "evaluate_tickets_async",
    # Formatter
    "ResultFormatter",
    # Templates
    "TemplateCriterion",
    "INCIDENT_LOGGING_CRITERIA",
    "INCIDENT_HANDLING_CRITERIA",
    "CUSTOMER_SERVICE_CRITERIA",
    "TEMPLATE_CRITERIA",
    "get_template_max_score",
    "get_template_criteria",
    "get_scoring_criteria",
    "get_deduction_criteria",
    "get_criterion_by_id",
]
