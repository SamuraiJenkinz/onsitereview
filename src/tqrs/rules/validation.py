"""Validation pattern detector.

Detects validation documentation in ticket descriptions including:
- OKTA Push MFA validation
- Phone validation (employee ID, name, location)
- Guest chat validation

Scoring:
- PASS: Validation completed and properly documented
- -15: Validation done but documentation incomplete
- N/A: Contact type doesn't require validation (self-service, OKTA-verified)
- FAIL: Validation not performed
"""

import re

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult


class ValidationDetector:
    """Detect validation patterns in ticket description."""

    CRITERION_ID = "validation_performed"

    # OKTA validation patterns
    OKTA_PATTERNS = [
        r"okta\s*(push|mfa)",
        r"validated\s*(by|via)[:\s]*okta",
        r"okta\s*verif(y|ied|ication)",
        r"mfa\s*push",
        r"okta\s*app",
    ]

    # Phone validation patterns (employee verification)
    PHONE_VALIDATION_PATTERNS = [
        r"validated\s*(by)?[:\s]*(employee\s*id|emp\s*id|full\s*name|name)",
        r"(name|employee\s*id|emp\s*id|location)\s*(verified|confirmed|validated)",
        r"verified\s*(via|by|using)[:\s]*(phone|call|employee)",
        r"confirm(ed)?\s*(caller|identity|user)",
        r"validation\s*:?\s*(yes|y|complete|done|passed)",
    ]

    # Guest chat patterns
    GUEST_CHAT_PATTERNS = [
        r"guest\s*chat",
        r"guest\s*validation",
        r"chat\s*validation",
        r"guest\s*verified",
    ]

    # Required validation elements for phone calls
    VALIDATION_ELEMENTS = {
        "name": [
            r"(full\s*)?name",
            r"first\s*and\s*last\s*name",
            r"colleague\s*name",
        ],
        "employee_id": [
            r"employee\s*id",
            r"emp\s*id",
            r"employee\s*number",
            r"id[:\s]*\d{5,}",  # ID followed by numbers
        ],
        "location": [
            r"(office\s*)?location",
            r"workday\s*location",
            r"site\s*location",
            r"working\s*(from\s*home|remotely)",
        ],
    }

    # Contact types that don't require validation
    NO_VALIDATION_REQUIRED = {"self-service", "web", "system", "auto"}

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate validation compliance based on contact type."""
        contact_type = ticket.contact_type.lower().strip()

        # Self-service and automated tickets don't require validation
        if contact_type in self.NO_VALIDATION_REQUIRED:
            return self._no_validation_required(contact_type)

        if contact_type == "phone":
            return self._evaluate_phone_validation(ticket)
        elif contact_type == "chat":
            return self._evaluate_chat_validation(ticket)
        elif contact_type == "email":
            return self._evaluate_email_validation(ticket)
        else:
            # Unknown contact type - check for any validation
            return self._evaluate_unknown_contact(ticket, contact_type)

    def _evaluate_phone_validation(self, ticket: ServiceNowTicket) -> RuleResult:
        """Phone calls require full validation documented.

        Phone validation should include:
        - OKTA Push/MFA verification, OR
        - Employee ID + Name + Location verification
        """
        desc = ticket.description.lower()
        full_text = f"{ticket.description} {ticket.work_notes}".lower()

        # Check for OKTA validation (highest confidence)
        if self._has_okta_validation(desc):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="OKTA Push/MFA validation documented",
                coaching=None,
            )

        # Check for phone validation elements
        elements = self._check_validation_elements(full_text)
        elements_found = [k for k, v in elements.items() if v]

        if len(elements_found) >= 2:
            # At least 2 elements documented - PASS
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning=f"Phone validation documented with: {', '.join(elements_found)}",
                coaching=None,
            )
        elif len(elements_found) == 1:
            # Only 1 element - incomplete documentation (-15)
            missing = [k for k in elements.keys() if k not in elements_found]
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-15",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning=f"Incomplete validation: only {elements_found[0]} documented",
                coaching=f"Document additional validation elements: {', '.join(missing)}",
            )

        # Check for general validation mention
        if self._has_general_validation_mention(full_text):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-15",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="Validation mentioned but details not documented",
                coaching="Document specific validation method: OKTA Push, Employee ID, "
                "Full Name, and/or Location verification",
            )

        # No validation found
        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=False,
            score="FAIL",
            evidence="No validation documentation found in description or work notes",
            reasoning="Phone contact requires caller validation but none was documented",
            coaching="Always document caller validation: Use OKTA Push MFA or verify "
            "Employee ID, Full Name, and Office Location",
        )

    def _evaluate_chat_validation(self, ticket: ServiceNowTicket) -> RuleResult:
        """Chat validation - check for OKTA or guest validation."""
        desc = ticket.description.lower()

        # OKTA-verified chat doesn't need additional validation
        if self._has_okta_validation(desc):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="OKTA validation confirmed via chat",
                coaching=None,
            )

        # Guest chat validation
        if self._has_guest_chat_validation(desc):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="Guest chat validation documented",
                coaching=None,
            )

        # Check for phone validation elements (also acceptable)
        elements = self._check_validation_elements(desc)
        if sum(elements.values()) >= 2:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="Chat validation with identity verification documented",
                coaching=None,
            )

        # Check for any validation mention
        if self._has_general_validation_mention(desc):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-15",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning="Validation mentioned but not fully documented",
                coaching="Specify validation method used for chat session",
            )

        # No validation - for chat this may be acceptable in some cases
        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=False,
            score="-15",
            evidence="No validation documentation found",
            reasoning="Chat contact should have validation documented",
            coaching="Document validation method: OKTA verification or guest chat validation",
        )

    def _evaluate_email_validation(self, ticket: ServiceNowTicket) -> RuleResult:
        """Email validation - usually sender domain is sufficient."""
        desc = ticket.description.lower()

        # Email from verified domain is typically acceptable
        if "email" in ticket.contact_type.lower():
            # Check if any validation mentioned
            if self._has_okta_validation(desc) or self._has_general_validation_mention(
                desc
            ):
                return RuleResult(
                    criterion_id=self.CRITERION_ID,
                    passed=True,
                    score="PASS",
                    evidence=self._extract_validation_evidence(ticket.description),
                    reasoning="Email contact with validation documented",
                    coaching=None,
                )

            # Email typically doesn't require explicit validation for basic requests
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="N/A",
                evidence="Email contact type",
                reasoning="Email from verified domain - explicit validation not required",
                coaching=None,
            )

        return self._no_validation_required("email")

    def _evaluate_unknown_contact(
        self, ticket: ServiceNowTicket, contact_type: str
    ) -> RuleResult:
        """Handle unknown contact types."""
        desc = ticket.description.lower()

        # If any validation is documented, it's a PASS
        if self._has_okta_validation(desc):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning=f"OKTA validation documented for {contact_type} contact",
                coaching=None,
            )

        elements = self._check_validation_elements(desc)
        if sum(elements.values()) >= 2:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=self._extract_validation_evidence(ticket.description),
                reasoning=f"Identity validation documented for {contact_type} contact",
                coaching=None,
            )

        # Unknown contact type without validation
        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=True,
            score="N/A",
            evidence=f"Contact type: {contact_type}",
            reasoning=f"Unknown contact type '{contact_type}' - validation not assessed",
            coaching=None,
        )

    def _no_validation_required(self, contact_type: str) -> RuleResult:
        """Return N/A result for contact types that don't need validation."""
        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=True,
            score="N/A",
            evidence=f"Contact type: {contact_type}",
            reasoning=f"Contact type '{contact_type}' does not require caller validation",
            coaching=None,
        )

    def _has_okta_validation(self, text: str) -> bool:
        """Check for OKTA validation mention."""
        for pattern in self.OKTA_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_guest_chat_validation(self, text: str) -> bool:
        """Check for guest chat validation mention."""
        for pattern in self.GUEST_CHAT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_general_validation_mention(self, text: str) -> bool:
        """Check for any validation-related keywords."""
        validation_keywords = [
            r"\bvalidat(ed|ion|e)\b",
            r"\bverif(y|ied|ication)\b",
            r"\bconfirm(ed)?\s*(identity|caller)\b",
            r"\bidentity\s*check\b",
        ]
        for pattern in validation_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _check_validation_elements(self, text: str) -> dict[str, bool]:
        """Check which validation elements are documented."""
        results = {}
        for element, patterns in self.VALIDATION_ELEMENTS.items():
            results[element] = any(
                re.search(p, text, re.IGNORECASE) for p in patterns
            )
        return results

    def _extract_validation_evidence(self, description: str) -> str:
        """Extract the validation-relevant portion of description."""
        lines = description.split("\n")

        # Find lines mentioning validation
        validation_lines = []
        for line in lines:
            line_lower = line.lower()
            if any(
                kw in line_lower
                for kw in ["validat", "verif", "okta", "mfa", "employee id", "confirm"]
            ):
                validation_lines.append(line.strip())

        if validation_lines:
            # Return first 2 validation-related lines
            evidence = " | ".join(validation_lines[:2])
            if len(evidence) > 200:
                return evidence[:197] + "..."
            return evidence

        # No specific validation lines, return first line
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 100:
                return first_line[:97] + "..."
            return first_line

        return "No description available"
