"""Base classes and types for rules engine."""

from typing import Protocol

from pydantic import BaseModel, Field

from tqrs.models.ticket import ServiceNowTicket


class RuleResult(BaseModel):
    """Result from a single rule evaluation."""

    criterion_id: str = Field(..., description="Unique criterion identifier")
    passed: bool = Field(..., description="Whether the rule check passed")
    score: int | str = Field(
        ..., description="Numeric score or PASS/FAIL/-15/-35/N/A"
    )
    max_score: int | None = Field(
        None, description="Maximum possible score (None for PASS/FAIL criteria)"
    )
    evidence: str = Field(..., description="Quote or data supporting the result")
    reasoning: str = Field(..., description="Explanation of the evaluation")
    coaching: str | None = Field(None, description="Improvement suggestion if applicable")

    @property
    def is_deduction(self) -> bool:
        """Check if this is a deduction result (negative score like -15 or -35)."""
        if isinstance(self.score, str):
            return self.score.startswith("-")
        return self.score < 0

    @property
    def is_auto_fail(self) -> bool:
        """Check if this result triggers auto-fail."""
        return isinstance(self.score, str) and self.score.upper() == "FAIL"

    @property
    def numeric_score(self) -> int:
        """Get numeric score value (0 for PASS/FAIL/N/A, negative for deductions)."""
        if isinstance(self.score, int):
            return self.score
        if self.score.upper() in ("PASS", "N/A"):
            return 0
        if self.score.upper() == "FAIL":
            return 0  # Auto-fail handled separately
        # Handle -15, -35 etc.
        try:
            return int(self.score)
        except ValueError:
            return 0


class RuleEvaluator(Protocol):
    """Protocol for rule evaluators."""

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate a ticket and return the result."""
        ...
