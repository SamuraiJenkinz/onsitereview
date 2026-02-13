"""onsitereview Scoring Engine - Onsite Support Review (90 points)."""

from onsitereview.scoring.batch import (
    BatchProgress,
    BatchResult,
    BatchTicketEvaluator,
    evaluate_tickets,
    evaluate_tickets_async,
)
from onsitereview.scoring.calculator import ScoringCalculator, ScoringResult
from onsitereview.scoring.evaluator import TicketEvaluator
from onsitereview.scoring.formatter import ResultFormatter
from onsitereview.scoring.templates import (
    ONSITE_REVIEW_CRITERIA,
    TemplateCriterion,
    get_criteria,
    get_criterion_by_id,
    get_max_score,
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
    "ONSITE_REVIEW_CRITERIA",
    "get_max_score",
    "get_criteria",
    "get_criterion_by_id",
]
