"""Opened For field validator for onsite support review."""

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult


class OpenedForValidator:
    """Validate the Opened For field is populated.

    Criterion 5: Opened For (10 points)
    - 10 points: Field populated with a valid ServiceNow profile
    - 0 points: Field empty or missing
    """

    CRITERION_ID = "opened_for_correct"
    MAX_SCORE = 10

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Check if opened_for field is populated.

        Args:
            ticket: The ticket to evaluate

        Returns:
            RuleResult with 10 (populated) or 0 (empty)
        """
        value = ticket.opened_for.strip() if ticket.opened_for else ""
        populated = len(value) > 0

        if populated:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score=self.MAX_SCORE,
                max_score=self.MAX_SCORE,
                evidence=f"Opened For field set to: {value}",
                reasoning="Opened For field is populated with a ServiceNow profile reference.",
            )

        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=False,
            score=0,
            max_score=self.MAX_SCORE,
            evidence="Opened For field is empty",
            reasoning="The Opened For field must identify the affected colleague.",
            coaching="Set the Opened For field to the affected colleague's ServiceNow profile.",
        )
