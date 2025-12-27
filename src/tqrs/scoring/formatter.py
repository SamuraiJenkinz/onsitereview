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

    def generate_path_to_passing(
        self,
        criterion_scores: list[CriterionScore],
        total_score: int,
        max_score: int = 70,
        pass_threshold: float = 0.90,
        validation_deduction: int = 0,
        critical_process_deduction: int = 0,
    ) -> list[dict]:
        """Generate actionable recommendations to reach passing score.

        Like credit score improvement tips, this analyzes what specific
        actions would have the highest impact on reaching the 90% threshold.

        Args:
            criterion_scores: List of criterion scores
            total_score: Current total score
            max_score: Maximum possible score (default 70)
            pass_threshold: Passing percentage (default 0.90 = 90%)
            validation_deduction: Points deducted for validation (-15 or 0)
            critical_process_deduction: Points deducted for critical process (-35 or 0)

        Returns:
            List of improvement recommendations with impact analysis
        """
        passing_score = int(max_score * pass_threshold)  # 63 points
        current_percentage = (total_score / max_score * 100) if max_score > 0 else 0
        points_needed = max(0, passing_score - total_score)

        # If already passing, return congratulatory message
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

        # 1. Check for deduction recoveries first (highest impact)
        if critical_process_deduction < 0:
            recovery = abs(critical_process_deduction)
            new_score = running_score + recovery
            new_pct = (new_score / max_score * 100)
            recommendations.append({
                "action": "Follow critical process procedures (password reset via trusted colleague, VIP priority, security escalation for lost devices)",
                "points_recoverable": recovery,
                "projected_score": new_score,
                "projected_percentage": round(new_pct, 1),
                "priority": "critical",
                "category": "critical_process",
                "details": "Critical process violations result in -35 point deduction. Ensure password resets go through a trusted colleague (manager/supervisor), never directly to the affected user.",
            })
            running_score = new_score

        if validation_deduction < 0:
            recovery = abs(validation_deduction)
            new_score = running_score + recovery
            new_pct = (new_score / max_score * 100)
            recommendations.append({
                "action": "Document caller validation (OKTA Push MFA, or verify Employee ID + Full Name + Location)",
                "points_recoverable": recovery,
                "projected_score": new_score,
                "projected_percentage": round(new_pct, 1),
                "priority": "high",
                "category": "validation",
                "details": "Incomplete validation documentation results in -15 point deduction. For phone calls, document OKTA verification or at least 2 of: Employee ID, Full Name, Office Location.",
            })
            running_score = new_score

        # 2. Analyze each criterion for improvement opportunities
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

        # 3. Generate specific recommendations for each criterion
        for opp in improvement_opportunities:
            # Calculate impact if this criterion was maximized
            recovery = opp["points_lost"]
            new_score = running_score + recovery
            new_pct = (new_score / max_score * 100)

            # Generate specific action based on criterion
            action, details = self._get_criterion_improvement_action(opp)

            # Determine priority
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

        # 4. Add summary recommendation
        if recommendations:
            # Calculate which recommendations are needed to pass
            cumulative_score = total_score
            actions_to_pass = []
            for rec in recommendations:
                if cumulative_score >= passing_score:
                    break
                cumulative_score += rec["points_recoverable"]
                actions_to_pass.append(rec["category"])

            # Add a summary at the beginning
            summary = {
                "action": f"To reach passing (90%), focus on these {len(actions_to_pass)} area(s): {', '.join(self._format_category_names(actions_to_pass))}",
                "points_recoverable": points_needed,
                "projected_score": passing_score,
                "projected_percentage": 90.0,
                "priority": "summary",
                "category": "summary",
                "details": f"Current score: {total_score}/70 ({current_percentage:.1f}%). Need {points_needed} more points to pass.",
            }
            recommendations.insert(0, summary)

        return recommendations

    def _get_criterion_improvement_action(self, opp: dict) -> tuple[str, str]:
        """Generate specific improvement action based on criterion type."""
        criterion_id = opp["criterion_id"]
        coaching = opp.get("coaching") or ""

        actions = {
            "accurate_description": (
                "Improve description completeness and clarity",
                "Include: (1) Contact info & working location, (2) Error messages/screenshots, (3) Usernames for account issues, (4) Domain\\Username for AD password resets, (5) Clear issue statement. " + (coaching if coaching else "")
            ),
            "troubleshooting_quality": (
                "Document troubleshooting steps with outcomes",
                "Record each troubleshooting step taken (restart, reset, clear cache, etc.) and the result of each action. Show logical progression from initial diagnosis to resolution. " + (coaching if coaching else "")
            ),
            "resolution_notes": (
                "Provide complete resolution documentation",
                "Include ALL THREE elements: (1) Summary of what was done to resolve, (2) Confirmation issue is resolved, (3) User agreed to close the ticket. " + (coaching if coaching else "")
            ),
            "customer_service_quality": (
                "Enhance communication quality and professionalism",
                "Demonstrate: Professional tone, empathy for the user's situation, clear explanations of actions taken, proper greeting/closing, and expectation setting. " + (coaching if coaching else "")
            ),
            "spelling_grammar": (
                "Proofread for spelling and grammar",
                "Review all text for spelling errors, grammar mistakes, and punctuation. Use spellcheck before submitting. " + (coaching if coaching else "")
            ),
            "short_description_format": (
                "Use correct 4-part short description format",
                "Format: [LoB] - [Location] - [App] - [Brief Description]. Example: 'MARSH - Sydney - VDI - Unable to connect to virtual desktop'. " + (coaching if coaching else "")
            ),
            "category_selection": (
                "Select the correct category",
                "Choose the category that best matches the type of issue being reported. " + (coaching if coaching else "")
            ),
            "subcategory_selection": (
                "Select the correct subcategory",
                "Choose the subcategory that most specifically describes the issue within the selected category. " + (coaching if coaching else "")
            ),
            "service_selection": (
                "Select the affected business service",
                "Identify and select the business service impacted by this incident. " + (coaching if coaching else "")
            ),
            "ci_selection": (
                "Select the configuration item (CI)",
                "Identify the specific CI (device, application, system) affected by the issue. " + (coaching if coaching else "")
            ),
        }

        if criterion_id in actions:
            return actions[criterion_id]

        # Default action based on coaching
        return (
            f"Improve {opp['criterion_name'].lower()}",
            coaching if coaching else f"Review scoring criteria for {opp['criterion_name']} and address gaps."
        )

    def _format_category_names(self, categories: list[str]) -> list[str]:
        """Format category IDs into readable names."""
        name_map = {
            "critical_process": "Critical Process",
            "validation": "Validation",
            "accurate_description": "Description",
            "troubleshooting_quality": "Troubleshooting",
            "resolution_notes": "Resolution Notes",
            "customer_service_quality": "Customer Service",
            "spelling_grammar": "Spelling/Grammar",
            "short_description_format": "Short Description",
            "category_selection": "Category",
            "subcategory_selection": "Subcategory",
            "service_selection": "Service",
            "ci_selection": "CI",
        }
        return [name_map.get(cat, cat) for cat in categories]
