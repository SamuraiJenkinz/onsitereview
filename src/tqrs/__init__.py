"""TQRS - Ticket Quality Review System.

AI-powered ServiceNow ticket quality review automation.
"""

__version__ = "0.1.0"

# Core models
# LLM evaluation
from tqrs.llm.client import OpenAIClient
from tqrs.llm.evaluator import LLMEvaluator
from tqrs.models.evaluation import (
    BatchEvaluationSummary,
    CriterionScore,
    EvaluationResult,
    PerformanceBand,
    TemplateType,
)
from tqrs.models.ticket import ServiceNowTicket

# Parser
from tqrs.parser.servicenow import ServiceNowParser

# Rules engine
from tqrs.rules.base import RuleResult
from tqrs.rules.evaluator import RulesEvaluator

# Scoring engine
from tqrs.scoring import (
    BatchProgress,
    BatchResult,
    BatchTicketEvaluator,
    ResultFormatter,
    ScoringCalculator,
    ScoringResult,
    TicketEvaluator,
    evaluate_tickets,
    evaluate_tickets_async,
)

__all__ = [
    # Version
    "__version__",
    # Models
    "ServiceNowTicket",
    "EvaluationResult",
    "CriterionScore",
    "PerformanceBand",
    "TemplateType",
    "BatchEvaluationSummary",
    # Parser
    "ServiceNowParser",
    # Rules
    "RuleResult",
    "RulesEvaluator",
    # LLM
    "OpenAIClient",
    "LLMEvaluator",
    # Scoring
    "ScoringCalculator",
    "ScoringResult",
    "TicketEvaluator",
    "BatchTicketEvaluator",
    "BatchProgress",
    "BatchResult",
    "ResultFormatter",
    "evaluate_tickets",
    "evaluate_tickets_async",
]
