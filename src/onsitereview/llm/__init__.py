"""LLM evaluation module for onsitereview - Onsite Support Review."""

from onsitereview.llm.batch import BatchLLMEvaluator, BatchProgress, BatchResult, TicketEvaluationResult
from onsitereview.llm.client import (
    LLMAPIError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
    OpenAIClient,
    TokenUsage,
)
from onsitereview.llm.evaluator import LLMEvaluator
from onsitereview.llm.schemas import (
    CriterionEvaluation,
    FieldCorrectnessEvaluation,
    IncidentHandlingEvaluation,
    IncidentNotesEvaluation,
    ResolutionNotesEvaluation,
)

__all__ = [
    # Client
    "OpenAIClient",
    "TokenUsage",
    "LLMError",
    "LLMAPIError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMValidationError",
    # Evaluator
    "LLMEvaluator",
    # Batch
    "BatchLLMEvaluator",
    "BatchProgress",
    "BatchResult",
    "TicketEvaluationResult",
    # Schemas
    "CriterionEvaluation",
    "FieldCorrectnessEvaluation",
    "IncidentNotesEvaluation",
    "IncidentHandlingEvaluation",
    "ResolutionNotesEvaluation",
]
