"""Base classes and types for rules engine."""

from typing import Protocol

from pydantic import BaseModel, Field

from tqrs.models.ticket import ServiceNowTicket


class RuleResult(BaseModel):
    """Result from a single rule or LLM evaluation."""

    criterion_id: str = Field(..., description="Unique criterion identifier")
    passed: bool = Field(..., description="Whether the rule check passed")
    score: int = Field(..., description="Numeric score awarded")
    max_score: int = Field(..., description="Maximum possible score")
    evidence: str = Field(..., description="Quote or data supporting the result")
    reasoning: str = Field(..., description="Explanation of the evaluation")
    coaching: str | None = Field(None, description="Improvement suggestion if applicable")


class RuleEvaluator(Protocol):
    """Protocol for rule evaluators."""

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate a ticket and return the result."""
        ...
