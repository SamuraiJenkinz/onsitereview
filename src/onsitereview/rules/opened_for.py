"""Opened For field validator for onsite support review."""

from onsitereview.models.ticket import ServiceNowTicket
from onsitereview.rules.base import RuleResult


class OpenedForValidator:
    """Validate the Opened For field is populated with a real colleague.

    Criterion 5: Opened For (10 points)
    - 10 points: Field populated with a valid ServiceNow profile
    - 0 points: Field empty, missing, or set to "Guest"
    """

    CRITERION_ID = "opened_for_correct"
    MAX_SCORE = 10

    # Values that indicate the field was not properly set to a real colleague
    INVALID_VALUES = {"guest"}

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Check if opened_for field is populated with a valid colleague.

        Args:
            ticket: The ticket to evaluate

        Returns:
            RuleResult with 10 (valid colleague) or 0 (empty/Guest)
        """
        value = ticket.opened_for.strip() if ticket.opened_for else ""

        if not value:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="Opened For field is empty",
                reasoning="The Opened For field must identify the affected colleague.",
                coaching="Set the Opened For field to the affected colleague's ServiceNow profile.",
            )

        if value.lower() in self.INVALID_VALUES:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence=f"Opened For field set to: {value}",
                reasoning=(
                    f"The Opened For field is set to '{value}', which is not a valid "
                    "colleague profile. It must identify the actual affected colleague."
                ),
                coaching=(
                    "Set the Opened For field to the affected colleague's ServiceNow "
                    "profile instead of using a generic 'Guest' entry."
                ),
            )

        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=True,
            score=self.MAX_SCORE,
            max_score=self.MAX_SCORE,
            evidence=f"Opened For field set to: {value}",
            reasoning="Opened For field is populated with a valid colleague reference.",
        )
