"""Result formatting utilities for TQRS scoring."""

from tqrs.models.evaluation import CriterionScore, TemplateType
from tqrs.rules.base import RuleResult
from tqrs.scoring.templates import (
    get_criterion_by_id,
    get_template_criteria,
)


class ResultFormatter:
    """Format rule and LLM results for display and export."""

    # Thresholds for categorizing scores
    STRENGTH_THRESHOLD = 0.9  # 90% of max points = strength
    IMPROVEMENT_THRESHOLD = 0.7  # Below 70% = improvement area

    def to_criterion_scores(
        self,
        rule_results: list[RuleResult],
        llm_results: list[RuleResult],
        template: TemplateType,
    ) -> list[CriterionScore]:
        """Convert RuleResults to CriterionScores for display."""
        all_results = {r.criterion_id: r for r in rule_results}
        all_results.update({r.criterion_id: r for r in llm_results})

        criterion_scores = []
        template_criteria = get_template_criteria(template)

        for criterion in template_criteria:
            if criterion.criterion_id not in all_results:
                continue

            result = all_results[criterion.criterion_id]

            # Handle PASS/FAIL/N/A scores
            if isinstance(result.score, str):
                score_str = result.score.upper()
                if score_str in ("PASS", "N/A"):
                    points_awarded = criterion.max_points  # Full points for PASS/N/A
                elif score_str == "FAIL":
                    points_awarded = 0
                else:
                    # Handle "-15", "-35" etc.
                    try:
                        points_awarded = max(0, int(result.score))
                    except ValueError:
                        points_awarded = 0
            else:
                points_awarded = max(0, result.score)

            criterion_scores.append(
                CriterionScore(
                    criterion_id=criterion.criterion_id,
                    criterion_name=criterion.criterion_name,
                    max_points=criterion.max_points,
                    points_awarded=points_awarded,
                    evidence=result.evidence,
                    reasoning=result.reasoning,
                    coaching=result.coaching,
                )
            )

        return criterion_scores

    def collect_strengths(
        self,
        results: list[RuleResult],
        template: TemplateType,
    ) -> list[str]:
        """Extract strength statements from high-scoring criteria."""
        strengths = []

        for result in results:
            criterion = get_criterion_by_id(template, result.criterion_id)
            if not criterion:
                continue

            # Skip deduction criteria for strengths
            if criterion.is_deduction:
                # PASS is a strength for deduction criteria
                if isinstance(result.score, str) and result.score.upper() == "PASS":
                    strengths.append(f"{criterion.criterion_name}: Process followed correctly")
                continue

            # Skip if max_score is 0
            if criterion.max_points == 0:
                continue

            # Calculate percentage for this criterion
            if isinstance(result.score, str):
                try:
                    score_val = int(result.score)
                except ValueError:
                    continue
            else:
                score_val = result.score

            percentage = (score_val / criterion.max_points) if criterion.max_points > 0 else 0

            if percentage >= self.STRENGTH_THRESHOLD:
                strength_text = f"{criterion.criterion_name}: {result.reasoning}"
                strengths.append(strength_text)

        return strengths[:5]  # Limit to top 5 strengths

    def collect_improvements(
        self,
        results: list[RuleResult],
        template: TemplateType,
    ) -> list[str]:
        """Extract improvement areas from low-scoring criteria."""
        improvements = []

        for result in results:
            criterion = get_criterion_by_id(template, result.criterion_id)
            if not criterion:
                continue

            # Handle deduction criteria
            if criterion.is_deduction:
                if isinstance(result.score, str):
                    score_str = result.score.upper()
                    if score_str == "-15":
                        improvements.append(
                            f"{criterion.criterion_name}: Documentation needs improvement"
                        )
                    elif score_str == "-35":
                        improvements.append(
                            f"{criterion.criterion_name}: Critical process not followed"
                        )
                    elif score_str == "FAIL":
                        improvements.append(
                            f"{criterion.criterion_name}: Process failure - requires immediate attention"
                        )
                continue

            # Skip if max_score is 0
            if criterion.max_points == 0:
                continue

            # Calculate percentage for this criterion
            if isinstance(result.score, str):
                try:
                    score_val = int(result.score)
                except ValueError:
                    continue
            else:
                score_val = result.score

            percentage = (score_val / criterion.max_points) if criterion.max_points > 0 else 1.0

            if percentage < self.IMPROVEMENT_THRESHOLD:
                if result.coaching:
                    improvement_text = f"{criterion.criterion_name}: {result.coaching}"
                else:
                    improvement_text = f"{criterion.criterion_name}: Needs improvement - scored {score_val}/{criterion.max_points}"
                improvements.append(improvement_text)

        return improvements[:5]  # Limit to top 5 improvements

    def get_coaching_recommendations(
        self,
        results: list[RuleResult],
        template: TemplateType,
    ) -> list[str]:
        """Collect all coaching recommendations from results."""
        recommendations = []

        for result in results:
            if result.coaching:
                criterion = get_criterion_by_id(template, result.criterion_id)
                criterion_name = criterion.criterion_name if criterion else result.criterion_id
                recommendations.append(f"[{criterion_name}] {result.coaching}")

        return recommendations

    def format_score_breakdown(
        self,
        criterion_scores: list[CriterionScore],
    ) -> str:
        """Format scores as a text breakdown."""
        lines = []
        for cs in criterion_scores:
            status = "✓" if cs.is_perfect else "○"
            lines.append(
                f"{status} {cs.criterion_name}: {cs.points_awarded}/{cs.max_points} ({cs.percentage}%)"
            )
        return "\n".join(lines)

    def format_summary(
        self,
        total_score: int,
        max_score: int,
        passed: bool,
        auto_fail: bool,
        auto_fail_reason: str | None = None,
    ) -> str:
        """Format evaluation summary as text."""
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        status = "PASS" if passed else "FAIL"

        if auto_fail:
            return f"Score: AUTO-FAIL - {auto_fail_reason}"

        return f"Score: {total_score}/{max_score} ({percentage:.1f}%) - {status}"
