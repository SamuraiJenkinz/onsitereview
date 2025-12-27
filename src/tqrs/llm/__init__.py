"""LLM evaluation module for TQRS."""

from tqrs.llm.batch import BatchLLMEvaluator, BatchProgress, BatchResult, TicketEvaluationResult
from tqrs.llm.client import (
    LLMAPIError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
    OpenAIClient,
    TokenUsage,
)
from tqrs.llm.evaluator import LLMEvaluator
from tqrs.llm.schemas import (
    CriterionEvaluation,
    CustomerServiceEvaluation,
    DescriptionEvaluation,
    LLMEvaluationResponse,
    ResolutionEvaluation,
    SpellingGrammarEvaluation,
    TroubleshootingEvaluation,
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
    "DescriptionEvaluation",
    "TroubleshootingEvaluation",
    "ResolutionEvaluation",
    "CustomerServiceEvaluation",
    "SpellingGrammarEvaluation",
    "LLMEvaluationResponse",
]
