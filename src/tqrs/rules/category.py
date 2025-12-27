"""Category and subcategory validator.

Basic validation of category selections against known taxonomy.
Full accuracy assessment requires LLM evaluation (Phase 3).

Scoring:
- 10 points: Category/subcategory exists in taxonomy
- 5 points: Category exists but subcategory may be better choice
- 0 points: Unknown category (requires manual review)
"""

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult


class CategoryValidator:
    """Validate category and subcategory selections."""

    CATEGORY_CRITERION_ID = "category_selection"
    SUBCATEGORY_CRITERION_ID = "subcategory_selection"
    MAX_SCORE = 10

    # Known valid categories with their subcategories
    # This is based on typical ServiceNow ITSM taxonomies
    CATEGORY_MAPPING = {
        "software": [
            "reset_restart",
            "installation",
            "configuration",
            "update",
            "error",
            "performance",
            "access",
            "license",
            "compatibility",
            "functionality",
        ],
        "hardware": [
            "laptop",
            "desktop",
            "monitor",
            "keyboard",
            "mouse",
            "peripherals",
            "printer",
            "docking station",
            "mobile device",
            "headset",
            "webcam",
            "replacement",
            "repair",
        ],
        "inquiry": [
            "password reset",
            "account access",
            "general",
            "information",
            "how to",
            "request",
            "status",
            "guidance",
        ],
        "network": [
            "connectivity",
            "vpn",
            "wifi",
            "wired",
            "internet",
            "dns",
            "firewall",
            "bandwidth",
            "latency",
        ],
        "email": [
            "outlook",
            "access",
            "configuration",
            "calendar",
            "attachments",
            "sync",
            "mobile",
            "rules",
            "spam",
        ],
        "security": [
            "virus",
            "malware",
            "phishing",
            "account lockout",
            "mfa",
            "encryption",
            "data loss",
            "suspicious activity",
        ],
        "access": [
            "account",
            "permissions",
            "shared drive",
            "application",
            "vpn",
            "remote",
            "new user",
            "termination",
        ],
        "telephony": [
            "desk phone",
            "softphone",
            "voicemail",
            "conference",
            "headset",
            "mobile",
        ],
        "printing": [
            "printer",
            "scanner",
            "paper jam",
            "toner",
            "configuration",
            "network printer",
        ],
        "application": [
            "sap",
            "workday",
            "servicenow",
            "sharepoint",
            "teams",
            "zoom",
            "office",
            "custom",
            "error",
            "access",
        ],
    }

    # Category aliases (common variations)
    CATEGORY_ALIASES = {
        "hw": "hardware",
        "sw": "software",
        "net": "network",
        "nw": "network",
        "sec": "security",
        "app": "application",
    }

    def evaluate_category(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate category selection."""
        category = ticket.category.lower().strip()

        if not category:
            return RuleResult(
                criterion_id=self.CATEGORY_CRITERION_ID,
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="No category selected",
                reasoning="Category is empty or missing",
                coaching="Always select an appropriate category for the incident",
            )

        # Check aliases
        normalized = self.CATEGORY_ALIASES.get(category, category)

        # Check if category exists
        if normalized in self.CATEGORY_MAPPING:
            return RuleResult(
                criterion_id=self.CATEGORY_CRITERION_ID,
                passed=True,
                score=self.MAX_SCORE,
                max_score=self.MAX_SCORE,
                evidence=f'Category: "{ticket.category}"',
                reasoning="Category exists in ServiceNow taxonomy",
                coaching=None,
            )

        # Check for partial match
        for valid_cat in self.CATEGORY_MAPPING.keys():
            if category in valid_cat or valid_cat in category:
                return RuleResult(
                    criterion_id=self.CATEGORY_CRITERION_ID,
                    passed=True,
                    score=self.MAX_SCORE - 2,  # 8 points for close match
                    max_score=self.MAX_SCORE,
                    evidence=f'Category: "{ticket.category}" (similar to "{valid_cat}")',
                    reasoning=f"Category similar to known category '{valid_cat}'",
                    coaching=f"Consider using standard category '{valid_cat}'",
                )

        # Unknown category - rules can't assess, defer to LLM
        return RuleResult(
            criterion_id=self.CATEGORY_CRITERION_ID,
            passed=True,
            score=self.MAX_SCORE,  # Assume correct, LLM will adjust if needed
            max_score=self.MAX_SCORE,
            evidence=f'Category: "{ticket.category}" (not in standard taxonomy)',
            reasoning="Category not in standard list - may be valid custom category",
            coaching=None,
        )

    def evaluate_subcategory(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate subcategory selection."""
        category = ticket.category.lower().strip()
        subcategory = ticket.subcategory.lower().strip()

        if not subcategory:
            return RuleResult(
                criterion_id=self.SUBCATEGORY_CRITERION_ID,
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="No subcategory selected",
                reasoning="Subcategory is empty or missing",
                coaching="Always select an appropriate subcategory for the incident",
            )

        # Normalize category
        normalized_cat = self.CATEGORY_ALIASES.get(category, category)

        # Check if category-subcategory pair is valid
        if normalized_cat in self.CATEGORY_MAPPING:
            valid_subs = self.CATEGORY_MAPPING[normalized_cat]

            # Exact match
            if subcategory in valid_subs:
                return RuleResult(
                    criterion_id=self.SUBCATEGORY_CRITERION_ID,
                    passed=True,
                    score=self.MAX_SCORE,
                    max_score=self.MAX_SCORE,
                    evidence=f'Subcategory: "{ticket.subcategory}" under "{ticket.category}"',
                    reasoning="Subcategory matches category and exists in taxonomy",
                    coaching=None,
                )

            # Partial match
            for valid_sub in valid_subs:
                if subcategory in valid_sub or valid_sub in subcategory:
                    return RuleResult(
                        criterion_id=self.SUBCATEGORY_CRITERION_ID,
                        passed=True,
                        score=self.MAX_SCORE - 2,  # 8 points
                        max_score=self.MAX_SCORE,
                        evidence=f'Subcategory: "{ticket.subcategory}" (similar to "{valid_sub}")',
                        reasoning=f"Subcategory similar to '{valid_sub}'",
                        coaching=f"Consider using standard subcategory '{valid_sub}'",
                    )

            # Subcategory not in list for this category
            return RuleResult(
                criterion_id=self.SUBCATEGORY_CRITERION_ID,
                passed=True,
                score=self.MAX_SCORE - 5,  # 5 points - may be wrong
                max_score=self.MAX_SCORE,
                evidence=f'Subcategory: "{ticket.subcategory}" under "{ticket.category}"',
                reasoning=f"Subcategory '{subcategory}' not in expected list for '{category}'",
                coaching=f"Review subcategory options for '{category}' category: {', '.join(valid_subs[:5])}...",
            )

        # Category not in mapping, so we can't validate subcategory
        return RuleResult(
            criterion_id=self.SUBCATEGORY_CRITERION_ID,
            passed=True,
            score=self.MAX_SCORE,  # Assume correct
            max_score=self.MAX_SCORE,
            evidence=f'Subcategory: "{ticket.subcategory}" under "{ticket.category}"',
            reasoning="Cannot validate - category not in standard taxonomy",
            coaching=None,
        )

    def evaluate_service(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate service selection (basic validation only).

        Full service accuracy requires LLM evaluation.
        """
        service = ticket.business_service

        if not service:
            return RuleResult(
                criterion_id="service_selection",
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="No service selected",
                reasoning="Business service is empty or missing",
                coaching="Select the appropriate business service for the incident",
            )

        # Service is a sys_id reference - can't validate without lookup
        # Assume it's valid, LLM will assess if description matches
        return RuleResult(
            criterion_id="service_selection",
            passed=True,
            score=self.MAX_SCORE,
            max_score=self.MAX_SCORE,
            evidence=f"Service reference: {service[:20]}..." if len(service) > 20 else f"Service: {service}",
            reasoning="Service reference present - accuracy to be verified",
            coaching=None,
        )

    def evaluate_ci(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate configuration item selection (basic validation only).

        Full CI accuracy requires LLM evaluation.
        """
        ci = ticket.cmdb_ci

        if not ci:
            return RuleResult(
                criterion_id="ci_selection",
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="No configuration item selected",
                reasoning="Configuration item is empty or missing",
                coaching="Select the appropriate configuration item for the incident",
            )

        # CI is a sys_id reference - can't validate without lookup
        return RuleResult(
            criterion_id="ci_selection",
            passed=True,
            score=self.MAX_SCORE,
            max_score=self.MAX_SCORE,
            evidence=f"CI reference: {ci[:20]}..." if len(ci) > 20 else f"CI: {ci}",
            reasoning="Configuration item reference present - accuracy to be verified",
            coaching=None,
        )
