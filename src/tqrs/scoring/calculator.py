"""Scoring calculator for TQRS."""

from dataclasses import dataclass

from tqrs.models.evaluation import PerformanceBand, TemplateType
from tqrs.rules.base import RuleResult
from tqrs.scoring.templates import get_criterion_by_id


@dataclass
class ScoringResult:
    """Result of score calculation."""

    base_score: int
    validation_deduction: int
    critical_process_deduction: int
    final_score: int
    max_score: int
    auto_fail: bool
    auto_fail_reason: str | None
    band: PerformanceBand
    passed: bool


class ScoringCalculator:
    """Calculate final scores from rule and LLM evaluation results."""

    PASS_THRESHOLD_PERCENTAGE = 90.0  # 63/70 = 90%

    def __init__(self) -> None:
        """Initialize the scoring calculator."""
        self._template_max_scores = {
            TemplateType.INCIDENT_LOGGING: 70,
            TemplateType.INCIDENT_HANDLING: 70,
            TemplateType.CUSTOMER_SERVICE: 70,
        }

    def calculate_score(
        self,
        rule_results: list[RuleResult],
        llm_results: list[RuleResult],
        template: TemplateType,
    ) -> ScoringResult:
        """
        Calculate final score from combined rule and LLM results.

        Scoring algorithm:
        1. Sum all positive numeric scores from rules and LLM
        2. Apply validation deduction (-15 if documented but not properly)
        3. Apply critical process deduction (-35 for non-password failures)
        4. Cap minimum score at 0 (never negative)
        5. Auto-fail if validation FAIL or password critical process FAIL
        """
        all_results = rule_results + llm_results

        # Check for auto-fail conditions first
        auto_fail, auto_fail_reason = self.check_auto_fail(all_results)

        if auto_fail:
            return ScoringResult(
                base_score=0,
                validation_deduction=0,
                critical_process_deduction=0,
                final_score=0,
                max_score=self._template_max_scores[template],
                auto_fail=True,
                auto_fail_reason=auto_fail_reason,
                band=PerformanceBand.PURPLE,
                passed=False,
            )

        # Calculate base score from positive scoring criteria
        base_score = self._calculate_base_score(all_results, template)

        # Apply deductions
        validation_deduction, critical_process_deduction = self._get_deductions(
            all_results
        )

        # Calculate final score (capped at 0 minimum)
        final_score = max(0, base_score + validation_deduction + critical_process_deduction)

        # Determine band and pass status
        max_score = self._template_max_scores[template]
        percentage = (final_score / max_score) * 100 if max_score > 0 else 0
        band = PerformanceBand.from_percentage(percentage)
        passed = percentage >= self.PASS_THRESHOLD_PERCENTAGE

        return ScoringResult(
            base_score=base_score,
            validation_deduction=validation_deduction,
            critical_process_deduction=critical_process_deduction,
            final_score=final_score,
            max_score=max_score,
            auto_fail=False,
            auto_fail_reason=None,
            band=band,
            passed=passed,
        )

    def _calculate_base_score(
        self,
        results: list[RuleResult],
        template: TemplateType,
    ) -> int:
        """Calculate base score from positive scoring criteria only."""
        total = 0

        for result in results:
            # Skip deduction criteria
            criterion = get_criterion_by_id(template, result.criterion_id)
            if criterion and criterion.is_deduction:
                continue

            # Skip PASS/FAIL/N/A results (they don't contribute to base score)
            if isinstance(result.score, str):
                score_str = result.score.upper()
                if score_str in ("PASS", "FAIL", "N/A"):
                    continue
                # Handle string deductions like "-15"
                try:
                    score_val = int(result.score)
                    if score_val < 0:
                        continue  # Deductions handled separately
                    total += score_val
                except ValueError:
                    continue
            else:
                # Numeric scores
                if result.score >= 0:
                    total += result.score

        return total

    def _get_deductions(
        self,
        results: list[RuleResult],
    ) -> tuple[int, int]:
        """
        Extract validation and critical process deductions.

        Returns:
            Tuple of (validation_deduction, critical_process_deduction)
            Both are negative or zero.
        """
        validation_deduction = 0
        critical_process_deduction = 0

        for result in results:
            if result.criterion_id == "validation_performed":
                if isinstance(result.score, str) and result.score == "-15":
                    validation_deduction = -15
                elif isinstance(result.score, int) and result.score == -15:
                    validation_deduction = -15

            elif result.criterion_id == "critical_process_followed":
                if isinstance(result.score, str) and result.score == "-35":
                    critical_process_deduction = -35
                elif isinstance(result.score, int) and result.score == -35:
                    critical_process_deduction = -35

        return validation_deduction, critical_process_deduction

    def check_auto_fail(
        self,
        results: list[RuleResult],
    ) -> tuple[bool, str | None]:
        """
        Check for auto-fail conditions.

        Auto-fail triggers:
        1. Validation FAIL - colleague not properly validated
        2. Critical Process FAIL - password process violation

        Returns:
            Tuple of (is_auto_fail, reason)
        """
        for result in results:
            if result.is_auto_fail:
                if result.criterion_id == "validation_performed":
                    return True, "Validation not performed - colleague identity not verified"
                elif result.criterion_id == "critical_process_followed":
                    return True, "Critical password process failure - security violation"
                else:
                    return True, f"Auto-fail on criterion: {result.criterion_id}"

        return False, None

    def apply_deductions(
        self,
        base_score: int,
        rule_results: list[RuleResult],
    ) -> tuple[int, int, int]:
        """
        Apply validation and critical process deductions to base score.

        Returns:
            Tuple of (final_score, validation_deduction, critical_process_deduction)
        """
        validation_deduction, critical_process_deduction = self._get_deductions(
            rule_results
        )

        # Apply deductions and cap at 0
        final_score = max(0, base_score + validation_deduction + critical_process_deduction)

        return final_score, validation_deduction, critical_process_deduction

    def get_max_score(self, template: TemplateType) -> int:
        """Get maximum possible score for a template."""
        return self._template_max_scores[template]

    def calculate_percentage(self, score: int, template: TemplateType) -> float:
        """Calculate percentage from score."""
        max_score = self._template_max_scores[template]
        if max_score == 0:
            return 0.0
        return round((score / max_score) * 100, 1)

    def get_band(self, percentage: float) -> PerformanceBand:
        """Get performance band from percentage."""
        return PerformanceBand.from_percentage(percentage)

    def passed(self, percentage: float) -> bool:
        """Check if percentage meets pass threshold."""
        return percentage >= self.PASS_THRESHOLD_PERCENTAGE
