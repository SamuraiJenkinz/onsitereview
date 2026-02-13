"""Result formatting utilities for onsitereview scoring - Onsite Support Review."""

from onsitereview.models.evaluation import CriterionScore
from onsitereview.rules.base import RuleResult
from onsitereview.scoring.templates import get_criteria, get_criterion_by_id


class ResultFormatter:
    """Format rule and LLM results for display and export."""

    STRENGTH_THRESHOLD = 0.9  # 90% of max points = strength
    IMPROVEMENT_THRESHOLD = 0.7  # Below 70% = improvement area

    def to_criterion_scores(
        self,
        rule_results: list[RuleResult],
        llm_results: list[RuleResult],
    ) -> list[CriterionScore]:
        """Convert RuleResults to CriterionScores for display."""
        all_results = {r.criterion_id: r for r in rule_results}
        all_results.update({r.criterion_id: r for r in llm_results})

        criterion_scores = []

        for criterion in get_criteria():
            if criterion.criterion_id not in all_results:
                continue

            result = all_results[criterion.criterion_id]
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
    ) -> list[str]:
        """Extract strength statements from high-scoring criteria."""
        strengths = []

        for result in results:
            criterion = get_criterion_by_id(result.criterion_id)
            if not criterion or criterion.max_points == 0:
                continue

            percentage = result.score / criterion.max_points

            if percentage >= self.STRENGTH_THRESHOLD:
                strength_text = f"{criterion.criterion_name}: {result.reasoning}"
                strengths.append(strength_text)

        return strengths[:5]

    def collect_improvements(
        self,
        results: list[RuleResult],
    ) -> list[str]:
        """Extract improvement areas from low-scoring criteria."""
        improvements = []

        for result in results:
            criterion = get_criterion_by_id(result.criterion_id)
            if not criterion or criterion.max_points == 0:
                continue

            percentage = result.score / criterion.max_points

            if percentage < self.IMPROVEMENT_THRESHOLD:
                if result.coaching:
                    improvement_text = f"{criterion.criterion_name}: {result.coaching}"
                else:
                    improvement_text = f"{criterion.criterion_name}: Needs improvement - scored {result.score}/{criterion.max_points}"
                improvements.append(improvement_text)

        return improvements[:5]

    def get_coaching_recommendations(
        self,
        results: list[RuleResult],
    ) -> list[str]:
        """Collect all coaching recommendations from results."""
        recommendations = []

        for result in results:
            if result.coaching:
                criterion = get_criterion_by_id(result.criterion_id)
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
    ) -> str:
        """Format evaluation summary as text."""
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        status = "PASS" if passed else "FAIL"
        return f"Score: {total_score}/{max_score} ({percentage:.1f}%) - {status}"

    def generate_path_to_passing(
        self,
        criterion_scores: list[CriterionScore],
        total_score: int,
        max_score: int = 90,
        pass_threshold: float = 0.90,
    ) -> list[dict]:
        """Generate actionable recommendations to reach passing score.

        Args:
            criterion_scores: List of criterion scores
            total_score: Current total score
            max_score: Maximum possible score (default 90)
            pass_threshold: Passing percentage (default 0.90 = 90%)

        Returns:
            List of improvement recommendations with impact analysis
        """
        passing_score = int(max_score * pass_threshold)  # 81 points
        current_percentage = (total_score / max_score * 100) if max_score > 0 else 0
        points_needed = max(0, passing_score - total_score)

        if total_score >= passing_score:
            return [{
                "action": "Congratulations! This ticket meets the passing threshold.",
                "points_recoverable": 0,
                "projected_score": total_score,
                "projected_percentage": current_percentage,
                "priority": "none",
                "category": "success",
            }]

        recommendations = []
        running_score = total_score

        # Analyze each criterion for improvement opportunities
        improvement_opportunities = []

        for cs in criterion_scores:
            points_lost = cs.max_points - cs.points_awarded
            if points_lost > 0:
                improvement_opportunities.append({
                    "criterion_id": cs.criterion_id,
                    "criterion_name": cs.criterion_name,
                    "current_score": cs.points_awarded,
                    "max_score": cs.max_points,
                    "points_lost": points_lost,
                    "percentage": cs.percentage,
                    "coaching": cs.coaching,
                    "reasoning": cs.reasoning,
                })

        # Sort by points lost (highest impact first)
        improvement_opportunities.sort(key=lambda x: x["points_lost"], reverse=True)

        for opp in improvement_opportunities:
            recovery = opp["points_lost"]
            new_score = running_score + recovery
            new_pct = (new_score / max_score * 100)

            action, details = self._get_criterion_improvement_action(opp)

            if recovery >= 10:
                priority = "high"
            elif recovery >= 5:
                priority = "medium"
            else:
                priority = "low"

            recommendations.append({
                "action": action,
                "points_recoverable": recovery,
                "projected_score": new_score,
                "projected_percentage": round(new_pct, 1),
                "priority": priority,
                "category": opp["criterion_id"],
                "details": details,
                "current": f"{opp['current_score']}/{opp['max_score']} ({opp['percentage']}%)",
            })

            running_score = new_score

        if recommendations:
            cumulative_score = total_score
            actions_to_pass = []
            for rec in recommendations:
                if cumulative_score >= passing_score:
                    break
                cumulative_score += rec["points_recoverable"]
                actions_to_pass.append(rec["category"])

            summary = {
                "action": f"To reach passing (90%), focus on these {len(actions_to_pass)} area(s): {', '.join(self._format_category_names(actions_to_pass))}",
                "points_recoverable": points_needed,
                "projected_score": passing_score,
                "projected_percentage": 90.0,
                "priority": "summary",
                "category": "summary",
                "details": f"Current score: {total_score}/90 ({current_percentage:.1f}%). Need {points_needed} more points to pass.",
            }
            recommendations.insert(0, summary)

        return recommendations

    def _get_criterion_improvement_action(self, opp: dict) -> tuple[str, str]:
        """Generate specific improvement action based on criterion type."""
        criterion_id = opp["criterion_id"]
        coaching = opp.get("coaching") or ""

        actions = {
            "correct_category": (
                "Select the correct category for the incident",
                "Choose the category that best matches the type of issue. " + coaching,
            ),
            "correct_subcategory": (
                "Select the correct subcategory",
                "Choose the subcategory that most specifically describes the issue. " + coaching,
            ),
            "correct_service": (
                "Select the affected business service",
                "Identify and select the business service impacted by this incident. " + coaching,
            ),
            "correct_ci": (
                "Select the correct configuration item (CI)",
                "Identify the specific CI (device, application, system) affected. " + coaching,
            ),
            "opened_for_correct": (
                "Set the Opened For field",
                "Set the Opened For field to the affected colleague's ServiceNow profile. " + coaching,
            ),
            "incident_notes": (
                "Improve incident documentation quality",
                "Include: contact info, working location, clear issue statement, troubleshooting steps in work notes. " + coaching,
            ),
            "incident_handling": (
                "Ensure correct incident handling",
                "Resolve at first contact when possible, or route to the correct resolver group. " + coaching,
            ),
            "resolution_notes": (
                "Provide complete resolution documentation",
                "Include: summary of resolution steps AND confirmation that the colleague verified the fix. " + coaching,
            ),
        }

        if criterion_id in actions:
            return actions[criterion_id]

        return (
            f"Improve {opp['criterion_name'].lower()}",
            coaching if coaching else f"Review scoring criteria for {opp['criterion_name']} and address gaps.",
        )

    def _format_category_names(self, categories: list[str]) -> list[str]:
        """Format category IDs into readable names."""
        name_map = {
            "correct_category": "Category",
            "correct_subcategory": "Subcategory",
            "correct_service": "Service",
            "correct_ci": "Configuration Item",
            "opened_for_correct": "Opened For",
            "incident_notes": "Incident Notes",
            "incident_handling": "Incident Handling",
            "resolution_notes": "Resolution Notes",
        }
        return [name_map.get(cat, cat) for cat in categories]
