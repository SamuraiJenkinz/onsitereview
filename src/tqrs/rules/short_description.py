"""Short description format validator.

Validates the 4-part format: [LoB] - [Location] - [App] - [Brief Description]

Scoring:
- 8 points: All 4 parts correct and accurate
- 6 points: 1 item incorrect/missing
- 4 points: 2 items incorrect/missing
- 2 points: 3 items incorrect/missing
- 0 points: 4 items incorrect/missing
"""

import re

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult


class ShortDescriptionValidator:
    """Validate short description follows 4-part format."""

    CRITERION_ID = "short_description_format"
    MAX_SCORE = 8

    # Known Line of Business patterns
    LOB_PATTERNS = {
        "MARSH",
        "MERCER",
        "MMC",
        "MMC-NCL",
        "GC",
        "GUY CARPENTER",
        "OW",
        "OLIVER WYMAN",
    }

    # Common location patterns - major cities/offices
    LOCATION_PATTERNS = [
        r"\b(?:bangalore|mumbai|chennai|hyderabad|delhi|pune)\b",  # India
        r"\b(?:sydney|melbourne|wollongong|brisbane|perth)\b",  # Australia
        r"\b(?:london|manchester|birmingham|glasgow|edinburgh)\b",  # UK
        r"\b(?:new york|chicago|boston|atlanta|dallas|seattle|la|sf)\b",  # US
        r"\b(?:singapore|hong kong|tokyo|shanghai|beijing)\b",  # Asia
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # Generic capitalized city name
    ]

    # Common application/system names
    APP_PATTERNS = {
        "VDI",
        "LAN",
        "AD",
        "ACTIVE DIRECTORY",
        "OUTLOOK",
        "TEAMS",
        "OFFICE",
        "O365",
        "OFFICE365",
        "SHAREPOINT",
        "ONEDRIVE",
        "EMAIL",
        "LAPTOP",
        "DESKTOP",
        "MOBILE",
        "PHONE",
        "VPN",
        "CITRIX",
        "SAP",
        "SERVICENOW",
        "SNOW",
        "WORKDAY",
        "CONCUR",
        "ZOOM",
        "WEBEX",
        "NETWORK",
        "PRINTER",
        "SOFTWARE",
        "HARDWARE",
        "ACCOUNT",
        "PASSWORD",
        "MFA",
        "OKTA",
    }

    def validate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Validate short description format and return scoring result."""
        short_desc = ticket.short_description.strip()

        if not short_desc:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score=0,
                max_score=self.MAX_SCORE,
                evidence="Empty short description",
                reasoning="Short description is empty or missing",
                coaching="Always provide a short description following the format: "
                "[LoB] - [Location] - [App] - [Brief Description]",
            )

        # Parse into parts
        parts = self._parse_parts(short_desc, ticket)
        issues = self._check_parts(parts, ticket)
        score = self._calculate_score(len(issues))

        # Build result
        if not issues:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score=score,
                max_score=self.MAX_SCORE,
                evidence=f'"{short_desc}"',
                reasoning="All 4 parts present and correctly formatted: "
                f"LoB={parts['lob']}, Location={parts['location']}, "
                f"App={parts['app']}, Brief={parts['brief']}",
                coaching=None,
            )

        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=score >= 6,  # Pass if only 1 issue
            score=score,
            max_score=self.MAX_SCORE,
            evidence=f'"{short_desc}"',
            reasoning=f"Issues found: {'; '.join(issues)}",
            coaching=self._get_coaching(issues),
        )

    def _parse_parts(
        self, short_desc: str, ticket: ServiceNowTicket
    ) -> dict[str, str | None]:
        """Parse short description into 4 parts.

        Handles both " - " and "-" separators.
        Returns dict with lob, location, app, brief.
        """
        parts: dict[str, str | None] = {
            "lob": None,
            "location": None,
            "app": None,
            "brief": None,
        }

        # Try standard " - " separator first
        if " - " in short_desc:
            segments = short_desc.split(" - ")
        elif "-" in short_desc:
            segments = short_desc.split("-")
        else:
            # No separator found - entire string is brief
            parts["brief"] = short_desc
            return parts

        # Assign parts based on position
        if len(segments) >= 1:
            parts["lob"] = segments[0].strip()
        if len(segments) >= 2:
            parts["location"] = segments[1].strip()
        if len(segments) >= 3:
            parts["app"] = segments[2].strip()
        if len(segments) >= 4:
            # Join remaining parts as brief description
            parts["brief"] = " - ".join(segments[3:]).strip()
        elif len(segments) == 3:
            # Only 3 parts - no brief
            pass

        # Handle MMC-NCL as compound LoB
        if parts["lob"] and parts["location"]:
            compound = f"{parts['lob']}-{parts['location']}".upper()
            if compound in self.LOB_PATTERNS:
                # Shift parts: compound becomes LoB
                parts["lob"] = compound
                parts["location"] = parts["app"]
                parts["app"] = parts["brief"]
                parts["brief"] = None
                # Re-check if we have more parts
                if len(segments) >= 5:
                    parts["brief"] = " - ".join(segments[4:]).strip()
                elif len(segments) == 4:
                    parts["brief"] = segments[3].strip()

        return parts

    def _check_parts(
        self, parts: dict[str, str | None], ticket: ServiceNowTicket
    ) -> list[str]:
        """Check each part for issues and return list of problems."""
        issues = []

        # Check LoB
        if not parts["lob"]:
            issues.append("Missing Line of Business (LoB)")
        elif not self._is_valid_lob(parts["lob"], ticket):
            issues.append(f"Unrecognized LoB: '{parts['lob']}'")

        # Check location
        if not parts["location"]:
            issues.append("Missing location")
        elif not self._is_valid_location(parts["location"]):
            # Location validation is lenient - just check it's not empty
            if len(parts["location"]) < 2:
                issues.append(f"Invalid location: '{parts['location']}'")

        # Check application/system
        if not parts["app"]:
            issues.append("Missing application/system")
        elif not self._is_valid_app(parts["app"]):
            # App validation is lenient - just check it's not empty or too long
            if len(parts["app"]) < 1 or len(parts["app"]) > 50:
                issues.append(f"Invalid application: '{parts['app']}'")

        # Check brief description
        if not parts["brief"]:
            issues.append("Missing brief description")
        elif len(parts["brief"]) < 3:
            issues.append(f"Brief description too short: '{parts['brief']}'")

        return issues

    def _is_valid_lob(self, lob: str, ticket: ServiceNowTicket) -> bool:
        """Check if LoB matches known patterns or ticket flags."""
        lob_upper = lob.upper()

        # Check against known patterns
        if lob_upper in self.LOB_PATTERNS:
            return True

        # Check partial matches
        for pattern in self.LOB_PATTERNS:
            if lob_upper.startswith(pattern) or pattern.startswith(lob_upper):
                return True

        # Check against ticket LoB flags
        ticket_lob = ticket.get_line_of_business().upper()
        if lob_upper in ticket_lob or ticket_lob in lob_upper:
            return True

        return False

    def _is_valid_location(self, location: str) -> bool:
        """Check if location looks valid."""
        if not location or len(location) < 2:
            return False

        location_lower = location.lower()

        # Check against known location patterns
        for pattern in self.LOCATION_PATTERNS:
            if re.search(pattern, location_lower, re.IGNORECASE):
                return True

        # If it starts with capital letter and isn't a common word, accept it
        if location[0].isupper() and len(location) >= 3:
            return True

        return False

    def _is_valid_app(self, app: str) -> bool:
        """Check if application/system looks valid."""
        if not app:
            return False

        app_upper = app.upper()

        # Check against known app patterns
        if app_upper in self.APP_PATTERNS:
            return True

        # Accept any reasonable-length string
        return 1 <= len(app) <= 50

    def _calculate_score(self, issue_count: int) -> int:
        """Calculate score based on number of issues.

        - 8 points: 0 issues
        - 6 points: 1 issue
        - 4 points: 2 issues
        - 2 points: 3 issues
        - 0 points: 4+ issues
        """
        scores = {0: 8, 1: 6, 2: 4, 3: 2}
        return scores.get(issue_count, 0)

    def _get_coaching(self, issues: list[str]) -> str:
        """Generate coaching based on issues found."""
        coaching_parts = [
            "Follow the 4-part format: [LoB] - [Location] - [App] - [Brief Description]"
        ]

        if any("LoB" in issue for issue in issues):
            coaching_parts.append(
                "Use standard LoB prefixes: MARSH, MERCER, MMC, MMC-NCL, GC, OW"
            )

        if any("location" in issue.lower() for issue in issues):
            coaching_parts.append("Include the office/city location")

        if any("application" in issue.lower() for issue in issues):
            coaching_parts.append(
                "Specify the affected application/system (e.g., VDI, LAN, AD)"
            )

        if any("brief" in issue.lower() for issue in issues):
            coaching_parts.append("Provide a concise description of the issue")

        return ". ".join(coaching_parts)
