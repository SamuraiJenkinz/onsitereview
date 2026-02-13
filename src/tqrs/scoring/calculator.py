"""Scoring calculator for TQRS - Onsite Support Review (90 points)."""

from dataclasses import dataclass

from tqrs.models.evaluation import PerformanceBand
from tqrs.rules.base import RuleResult


@dataclass
class ScoringResult:
    """Result of score calculation."""

    total_score: int
    max_score: int
    band: PerformanceBand
    passed: bool


class ScoringCalculator:
    """Calculate final scores from rule and LLM evaluation results.

    90-point system, no deductions, no auto-fail.
    Pass threshold: 81/90 (90%).
    """

    MAX_SCORE = 90
    PASS_THRESHOLD = 81  # 90% of 90

    def calculate_score(
        self,
        rule_results: list[RuleResult],
        llm_results: list[RuleResult],
    ) -> ScoringResult:
        """Calculate final score from combined rule and LLM results.

        Simply sums all positive scores. No deductions, no auto-fail.
        """
        all_results = rule_results + llm_results
        total_score = sum(r.score for r in all_results)

        # Cap at max score
        total_score = min(total_score, self.MAX_SCORE)

        percentage = (total_score / self.MAX_SCORE) * 100 if self.MAX_SCORE > 0 else 0
        band = PerformanceBand.from_percentage(percentage)
        passed = total_score >= self.PASS_THRESHOLD

        return ScoringResult(
            total_score=total_score,
            max_score=self.MAX_SCORE,
            band=band,
            passed=passed,
        )

    def calculate_percentage(self, score: int) -> float:
        """Calculate percentage from score."""
        if self.MAX_SCORE == 0:
            return 0.0
        return round((score / self.MAX_SCORE) * 100, 1)

    def get_band(self, percentage: float) -> PerformanceBand:
        """Get performance band from percentage."""
        return PerformanceBand.from_percentage(percentage)

    def passed(self, percentage: float) -> bool:
        """Check if percentage meets pass threshold."""
        return percentage >= 90.0
