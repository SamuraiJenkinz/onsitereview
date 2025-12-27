"""Rules evaluator orchestrator.

Combines all rule-based evaluations into a unified evaluation workflow.
Runs appropriate rules based on the selected evaluation template.
"""

from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult
from tqrs.rules.category import CategoryValidator
from tqrs.rules.critical_process import CriticalProcessDetector
from tqrs.rules.short_description import ShortDescriptionValidator
from tqrs.rules.validation import ValidationDetector


class RulesEvaluator:
    """Orchestrate all rule-based evaluations."""

    def __init__(self) -> None:
        """Initialize all rule evaluators."""
        self.short_desc_validator = ShortDescriptionValidator()
        self.validation_detector = ValidationDetector()
        self.critical_process_detector = CriticalProcessDetector()
        self.category_validator = CategoryValidator()

    def evaluate(
        self, ticket: ServiceNowTicket, template: TemplateType
    ) -> list[RuleResult]:
        """Run all applicable rules for given template.

        Args:
            ticket: The ticket to evaluate
            template: The evaluation template type

        Returns:
            List of RuleResult objects from all applicable rules
        """
        results: list[RuleResult] = []

        # Critical process and validation are always evaluated
        # These can result in deductions or auto-fail
        results.append(self.critical_process_detector.evaluate(ticket))
        results.append(self.validation_detector.evaluate(ticket))

        # Template-specific evaluations
        if template == TemplateType.INCIDENT_LOGGING:
            results.extend(self._evaluate_logging_rules(ticket))
        elif template == TemplateType.INCIDENT_HANDLING:
            results.extend(self._evaluate_handling_rules(ticket))
        elif template == TemplateType.CUSTOMER_SERVICE:
            results.extend(self._evaluate_customer_service_rules(ticket))

        return results

    def _evaluate_logging_rules(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Evaluate rules specific to Incident Logging template.

        Incident Logging focuses on documentation quality:
        - Short description format
        - Category/subcategory selection
        - Service/CI selection
        """
        results = []

        # Short description format validation
        results.append(self.short_desc_validator.validate(ticket))

        # Category validation
        results.append(self.category_validator.evaluate_category(ticket))
        results.append(self.category_validator.evaluate_subcategory(ticket))

        # Service and CI validation
        results.append(self.category_validator.evaluate_service(ticket))
        results.append(self.category_validator.evaluate_ci(ticket))

        return results

    def _evaluate_handling_rules(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Evaluate rules specific to Incident Handling template.

        Incident Handling focuses on troubleshooting and resolution.
        Most criteria require LLM assessment, but we can validate:
        - Short description format (for context)
        - Category appropriateness (basic check)
        """
        results = []

        # Basic format check (still applies)
        results.append(self.short_desc_validator.validate(ticket))

        # Category validation (basic check)
        results.append(self.category_validator.evaluate_category(ticket))
        results.append(self.category_validator.evaluate_subcategory(ticket))

        return results

    def _evaluate_customer_service_rules(
        self, ticket: ServiceNowTicket
    ) -> list[RuleResult]:
        """Evaluate rules specific to Customer Service template.

        Customer Service focuses on soft skills and interaction quality.
        Most criteria require LLM assessment of language and tone.
        Rules engine can only validate basic structure.
        """
        results = []

        # Short description format (minimal weight in this template)
        results.append(self.short_desc_validator.validate(ticket))

        return results

    def get_rule_scores(
        self, ticket: ServiceNowTicket, template: TemplateType
    ) -> dict[str, RuleResult]:
        """Get results keyed by criterion_id.

        Args:
            ticket: The ticket to evaluate
            template: The evaluation template type

        Returns:
            Dictionary mapping criterion_id to RuleResult
        """
        results = self.evaluate(ticket, template)
        return {r.criterion_id: r for r in results}

    def get_deductions(
        self, ticket: ServiceNowTicket, template: TemplateType
    ) -> tuple[int, int, bool, str | None]:
        """Calculate deductions from rule evaluations.

        Returns:
            Tuple of (validation_deduction, critical_process_deduction,
                     auto_fail, auto_fail_reason)
        """
        results = self.evaluate(ticket, template)

        validation_deduction = 0
        critical_process_deduction = 0
        auto_fail = False
        auto_fail_reason = None

        for result in results:
            # Check for auto-fail
            if result.is_auto_fail:
                auto_fail = True
                auto_fail_reason = result.reasoning
                break

            # Check for validation deduction
            if result.criterion_id == "validation_performed":
                if result.score == "-15":
                    validation_deduction = -15

            # Check for critical process deduction
            if result.criterion_id == "critical_process_followed":
                if result.score == "-35":
                    critical_process_deduction = -35
                elif result.is_auto_fail:
                    auto_fail = True
                    auto_fail_reason = result.reasoning

        return (
            validation_deduction,
            critical_process_deduction,
            auto_fail,
            auto_fail_reason,
        )

    def get_base_score(
        self, ticket: ServiceNowTicket, template: TemplateType
    ) -> int:
        """Calculate base score from rule evaluations (before deductions).

        Args:
            ticket: The ticket to evaluate
            template: The evaluation template type

        Returns:
            Total points from rule-based criteria
        """
        results = self.evaluate(ticket, template)

        total = 0
        for result in results:
            # Skip deduction/status criteria
            if result.criterion_id in (
                "validation_performed",
                "critical_process_followed",
            ):
                continue

            # Add numeric scores
            if isinstance(result.score, int) and result.score >= 0:
                total += result.score

        return total

    def summarize(
        self, ticket: ServiceNowTicket, template: TemplateType
    ) -> dict:
        """Get a summary of rule evaluation results.

        Args:
            ticket: The ticket to evaluate
            template: The evaluation template type

        Returns:
            Summary dictionary with scores and status
        """
        results = self.evaluate(ticket, template)
        deductions = self.get_deductions(ticket, template)
        base_score = self.get_base_score(ticket, template)

        # Count results by status
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        # Get criteria needing coaching
        coaching_needed = [
            {"criterion": r.criterion_id, "coaching": r.coaching}
            for r in results
            if r.coaching
        ]

        return {
            "template": template.value,
            "ticket_number": ticket.number,
            "rules_evaluated": len(results),
            "passed": passed,
            "failed": failed,
            "base_score": base_score,
            "validation_deduction": deductions[0],
            "critical_process_deduction": deductions[1],
            "auto_fail": deductions[2],
            "auto_fail_reason": deductions[3],
            "coaching_needed": coaching_needed,
        }
