"""Critical process detector.

Identifies critical processes and verifies proper handling:
- Password reset (requires trusted colleague)
- Lost/stolen devices
- VIP support
- Virus/malware incidents
- Data privacy incidents

Scoring:
- PASS: Critical process followed correctly
- -35: Critical process failure (non-password)
- FAIL: Password process failure (automatic fail - score becomes 0)
- N/A: No critical process involved
"""

import re

from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult


class CriticalProcessDetector:
    """Detect critical processes and verify compliance."""

    CRITERION_ID = "critical_process_followed"

    # Critical process types with detection patterns
    CRITICAL_PROCESSES = {
        "password_reset": {
            "description": "Password Reset",
            "patterns": [
                r"password\s*reset",
                r"reset\s*password",
                r"pwd\s*reset",
                r"lan\s*password",
                r"ad\s*password",
                r"network\s*password",
            ],
            "subcategory_match": ["password reset", "password"],
            "auto_fail_on_violation": True,  # Password violations = automatic 0
        },
        "lost_stolen": {
            "description": "Lost/Stolen Device",
            "patterns": [
                r"\blost\b.*\b(device|laptop|phone|mobile|tablet)\b",
                r"\bstolen\b.*\b(device|laptop|phone|mobile|tablet)\b",
                r"\bmissing\b.*\b(device|laptop|phone|mobile)\b",
                r"\b(device|laptop|phone|mobile)\b.*\b(lost|stolen|missing)\b",
            ],
            "subcategory_match": ["lost", "stolen"],
            "auto_fail_on_violation": False,
        },
        "vip": {
            "description": "VIP/Executive Support",
            "patterns": [
                r"\bvip\b",
                r"\bexecutive\b",
                r"\bc-suite\b",
                r"\bsenior\s*leadership\b",
            ],
            "priority_requirement": ["1", "2"],  # VIP should be high priority
            "auto_fail_on_violation": False,
        },
        "virus_malware": {
            "description": "Virus/Malware Incident",
            "patterns": [
                r"\bvirus\b",
                r"\bmalware\b",
                r"\bransomware\b",
                r"\binfected\b",
                r"\bsuspicious\s*(file|email|activity)\b",
            ],
            "subcategory_match": ["virus", "malware", "security"],
            "auto_fail_on_violation": False,
        },
        "data_privacy": {
            "description": "Data Privacy/Security Incident",
            "patterns": [
                r"data\s*privacy",
                r"security\s*incident",
                r"data\s*breach",
                r"unauthorized\s*access",
                r"pii\s*(exposure|leak)",
                r"gdpr",
            ],
            "auto_fail_on_violation": False,
        },
        "account_lockout": {
            "description": "Account Lockout",
            "patterns": [
                r"account\s*(locked|lockout|disabled)",
                r"locked\s*out",
                r"disable[d]?\s*account",
            ],
            "subcategory_match": ["account", "lockout"],
            "auto_fail_on_violation": False,
        },
    }

    # Password reset specific compliance patterns
    PASSWORD_COMPLIANCE = {
        "trusted_colleague": [
            r"trusted\s*colleague",
            r"trusted\s*contact",
            r"manager",
            r"supervisor",
            r"sent\s*(to|via)\s*manager",
            r"shared\s*with\s*manager",
            r"cc[:\s]*manager",
        ],
        "password_delivery": [
            r"(new\s*)?password\s*(sent|shared|provided)",
            r"temporary\s*password",
            r"reset\s*link",
            r"password\s*generator",
            r"norton\s*password",
        ],
        "change_instruction": [
            r"change\s*(the\s*)?password",
            r"update\s*(the\s*)?password",
            r"reset\s*after",
            r"change\s*after\s*\d+\s*hours",
        ],
    }

    def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate critical process compliance."""
        detected = self._detect_critical_processes(ticket)

        if not detected:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="N/A",
                evidence="No critical process indicators found",
                reasoning="Ticket does not involve a critical process",
                coaching=None,
            )

        # Check each detected process for compliance
        for process_type in detected:
            result = self._verify_process_compliance(ticket, process_type)
            if not result.passed:
                return result

        # All processes passed
        process_names = [
            self.CRITICAL_PROCESSES[p]["description"] for p in detected
        ]
        return RuleResult(
            criterion_id=self.CRITERION_ID,
            passed=True,
            score="PASS",
            evidence=f"Critical process(es): {', '.join(process_names)}",
            reasoning="All critical process requirements were followed correctly",
            coaching=None,
        )

    def _detect_critical_processes(self, ticket: ServiceNowTicket) -> list[str]:
        """Detect which critical processes apply to this ticket."""
        detected = []

        # Combine all text fields for pattern matching
        full_text = " ".join(
            [
                ticket.short_description,
                ticket.description,
                ticket.work_notes,
                ticket.close_notes,
                ticket.subcategory,
            ]
        ).lower()

        for process_type, config in self.CRITICAL_PROCESSES.items():
            # Check subcategory match first (most reliable)
            if "subcategory_match" in config:
                subcategory_lower = ticket.subcategory.lower()
                if any(
                    match in subcategory_lower
                    for match in config["subcategory_match"]
                ):
                    detected.append(process_type)
                    continue

            # Check patterns in text
            for pattern in config["patterns"]:
                if re.search(pattern, full_text, re.IGNORECASE):
                    detected.append(process_type)
                    break

        return list(set(detected))  # Remove duplicates

    def _verify_process_compliance(
        self, ticket: ServiceNowTicket, process_type: str
    ) -> RuleResult:
        """Verify specific process was followed correctly."""
        config = self.CRITICAL_PROCESSES[process_type]

        if process_type == "password_reset":
            return self._verify_password_reset(ticket)
        elif process_type == "vip":
            return self._verify_vip_handling(ticket, config)
        elif process_type == "lost_stolen":
            return self._verify_lost_stolen(ticket)
        elif process_type == "virus_malware":
            return self._verify_security_incident(ticket, "virus_malware")
        elif process_type == "data_privacy":
            return self._verify_security_incident(ticket, "data_privacy")
        else:
            # For other process types, just verify documentation exists
            return self._verify_documentation(ticket, process_type, config)

    def _verify_password_reset(self, ticket: ServiceNowTicket) -> RuleResult:
        """Verify password reset process compliance.

        Password reset requires:
        1. Trusted colleague documented (password NOT sent to affected user directly)
        2. Secure password delivery method
        3. Instruction to change password provided
        """
        full_text = " ".join(
            [ticket.description, ticket.work_notes, ticket.close_notes]
        ).lower()

        compliance = {}
        for element, patterns in self.PASSWORD_COMPLIANCE.items():
            compliance[element] = any(
                re.search(p, full_text, re.IGNORECASE) for p in patterns
            )

        # Check for trusted colleague (critical)
        has_trusted = compliance["trusted_colleague"]
        has_delivery = compliance["password_delivery"]
        has_instruction = compliance["change_instruction"]

        # Evidence extraction
        evidence = self._extract_password_evidence(ticket)

        if has_trusted and (has_delivery or has_instruction):
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=evidence,
                reasoning="Password reset process followed: "
                "trusted colleague documented, secure delivery method used",
                coaching=None,
            )
        elif has_trusted:
            # Trusted colleague but missing some documentation
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=evidence,
                reasoning="Password reset with trusted colleague documented",
                coaching="Consider also documenting password change instructions",
            )
        elif has_delivery or has_instruction:
            # Has some password process but missing trusted colleague
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="FAIL",
                evidence=evidence,
                reasoning="Password reset without trusted colleague documentation - "
                "password may have been sent directly to affected user",
                coaching="CRITICAL: Never send password directly to affected user. "
                "Always use a trusted colleague (manager, supervisor) as intermediary",
            )
        else:
            # No password process documentation
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="FAIL",
                evidence="No password reset process documentation found",
                reasoning="Password reset detected but no process documentation",
                coaching="Document password reset process: "
                "1) Use trusted colleague for password delivery, "
                "2) Never send to affected user directly, "
                "3) Instruct user to change password",
            )

    def _verify_vip_handling(
        self, ticket: ServiceNowTicket, config: dict
    ) -> RuleResult:
        """Verify VIP ticket is handled with appropriate priority."""
        priority_req = config.get("priority_requirement", ["1", "2"])

        if ticket.priority in priority_req:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=f"VIP ticket with priority {ticket.priority}",
                reasoning="VIP ticket handled with appropriate priority level",
                coaching=None,
            )
        else:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-35",
                evidence=f"VIP ticket with priority {ticket.priority}",
                reasoning=f"VIP ticket should have priority {'/'.join(priority_req)}, "
                f"but has priority {ticket.priority}",
                coaching="Set appropriate priority for VIP/executive support tickets",
            )

    def _verify_lost_stolen(self, ticket: ServiceNowTicket) -> RuleResult:
        """Verify lost/stolen device handling."""
        full_text = " ".join(
            [ticket.description, ticket.work_notes, ticket.close_notes]
        ).lower()

        # Check for required escalation/documentation
        escalation_patterns = [
            r"escalat",
            r"security\s*team",
            r"infosec",
            r"remote\s*wipe",
            r"disabled?\s*(device|account)",
            r"locked?\s*(device|account)",
        ]

        has_escalation = any(
            re.search(p, full_text, re.IGNORECASE) for p in escalation_patterns
        )

        if has_escalation:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence="Lost/stolen device with security response documented",
                reasoning="Lost/stolen device handled with appropriate escalation",
                coaching=None,
            )
        else:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-35",
                evidence="Lost/stolen device incident",
                reasoning="Lost/stolen device requires security escalation "
                "but none documented",
                coaching="For lost/stolen devices: "
                "1) Disable device/account immediately, "
                "2) Escalate to security team, "
                "3) Consider remote wipe if applicable",
            )

    def _verify_security_incident(
        self, ticket: ServiceNowTicket, incident_type: str
    ) -> RuleResult:
        """Verify security incident handling (virus, malware, data privacy)."""
        full_text = " ".join(
            [ticket.description, ticket.work_notes, ticket.close_notes]
        ).lower()

        # Check for required actions
        security_actions = [
            r"escalat",
            r"security\s*team",
            r"infosec",
            r"isolated?",
            r"quarantine",
            r"disconnect",
            r"scan",
            r"report",
        ]

        has_action = any(
            re.search(p, full_text, re.IGNORECASE) for p in security_actions
        )

        incident_name = self.CRITICAL_PROCESSES[incident_type]["description"]

        if has_action:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=f"{incident_name} with security response documented",
                reasoning=f"{incident_name} handled with appropriate security measures",
                coaching=None,
            )
        else:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-35",
                evidence=f"{incident_name} incident",
                reasoning=f"{incident_name} requires security response but none documented",
                coaching=f"For {incident_name.lower()}: "
                "1) Isolate affected system, "
                "2) Escalate to security team, "
                "3) Document all actions taken",
            )

    def _verify_documentation(
        self, ticket: ServiceNowTicket, process_type: str, config: dict
    ) -> RuleResult:
        """Generic verification that process was documented."""
        # If we detected a process, assume it was handled unless
        # resolution notes indicate otherwise
        if ticket.close_notes and len(ticket.close_notes) > 20:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=True,
                score="PASS",
                evidence=f"{config['description']} with resolution documented",
                reasoning=f"{config['description']} handled and documented",
                coaching=None,
            )
        else:
            return RuleResult(
                criterion_id=self.CRITERION_ID,
                passed=False,
                score="-35",
                evidence=f"{config['description']} with minimal documentation",
                reasoning=f"{config['description']} requires detailed documentation",
                coaching="Document all actions taken for critical processes",
            )

    def _extract_password_evidence(self, ticket: ServiceNowTicket) -> str:
        """Extract password-related evidence from ticket."""
        full_text = f"{ticket.description}\n{ticket.work_notes}\n{ticket.close_notes}"
        lines = full_text.split("\n")

        password_lines = []
        for line in lines:
            line_lower = line.lower()
            if any(
                kw in line_lower
                for kw in [
                    "password",
                    "trusted",
                    "manager",
                    "colleague",
                    "reset",
                    "sent",
                    "shared",
                ]
            ):
                password_lines.append(line.strip())

        if password_lines:
            evidence = " | ".join(password_lines[:3])
            if len(evidence) > 200:
                return evidence[:197] + "..."
            return evidence

        return "No password process documentation found"
