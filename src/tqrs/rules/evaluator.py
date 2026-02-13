"""Rules evaluator for onsite support review.

Single evaluation path: Opened For field presence check.
"""

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult
from tqrs.rules.opened_for import OpenedForValidator


class RulesEvaluator:
    """Orchestrate rule-based evaluations for onsite review."""

    def __init__(self) -> None:
        self.opened_for_validator = OpenedForValidator()

    def evaluate(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Run all rule evaluations.

        Args:
            ticket: The ticket to evaluate

        Returns:
            List containing the Opened For RuleResult
        """
        return [self.opened_for_validator.evaluate(ticket)]

    def get_rule_scores(self, ticket: ServiceNowTicket) -> dict[str, RuleResult]:
        """Get results keyed by criterion_id.

        Args:
            ticket: The ticket to evaluate

        Returns:
            Dictionary mapping criterion_id to RuleResult
        """
        results = self.evaluate(ticket)
        return {r.criterion_id: r for r in results}
