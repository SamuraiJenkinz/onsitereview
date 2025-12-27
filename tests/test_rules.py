"""Tests for the rules engine."""

import json
from pathlib import Path

import pytest

from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.parser.servicenow import ServiceNowParser
from tqrs.rules import RulesEvaluator
from tqrs.rules.category import CategoryValidator
from tqrs.rules.critical_process import CriticalProcessDetector
from tqrs.rules.short_description import ShortDescriptionValidator
from tqrs.rules.validation import ValidationDetector


# --- Fixtures ---


@pytest.fixture
def sample_tickets():
    """Load prototype sample tickets."""
    path = Path(__file__).parent.parent / "prototype_samples.json"
    with open(path) as f:
        data = json.load(f)
    parser = ServiceNowParser()
    return parser.parse_json(data)


@pytest.fixture
def short_desc_validator():
    """Create ShortDescriptionValidator instance."""
    return ShortDescriptionValidator()


@pytest.fixture
def validation_detector():
    """Create ValidationDetector instance."""
    return ValidationDetector()


@pytest.fixture
def critical_process_detector():
    """Create CriticalProcessDetector instance."""
    return CriticalProcessDetector()


@pytest.fixture
def category_validator():
    """Create CategoryValidator instance."""
    return CategoryValidator()


@pytest.fixture
def rules_evaluator():
    """Create RulesEvaluator instance."""
    return RulesEvaluator()


def create_ticket(**kwargs) -> ServiceNowTicket:
    """Create a ticket with specified fields, filling in defaults."""
    defaults = {
        "number": "INC0000001",
        "sys_id": "abc123",
        "opened_at": "2025-12-10T10:00:00",
        "caller_id": "user123",
        "opened_by": "agent123",
        "assigned_to": "agent123",
        "category": "software",
        "subcategory": "reset_restart",
        "contact_type": "phone",
        "priority": "3",
        "impact": "3",
        "urgency": "3",
        "short_description": "Test - Location - App - Brief description",
        "description": "Test description",
        "state": "7",
        "incident_state": "7",
        "company": "company123",
        "location": "location123",
        "assignment_group": "group123",
    }
    defaults.update(kwargs)
    return ServiceNowTicket(**defaults)


# --- Short Description Validator Tests ---


class TestShortDescriptionValidator:
    """Tests for ShortDescriptionValidator."""

    def test_valid_4part_format_spaces(self, short_desc_validator):
        """Test valid 4-part format with ' - ' separators."""
        ticket = create_ticket(
            short_description="MMC - Wollongong - AD - Password reset"
        )
        result = short_desc_validator.validate(ticket)

        assert result.passed is True
        assert result.score == 8
        assert result.max_score == 8

    def test_valid_4part_format_hyphens(self, short_desc_validator):
        """Test valid 4-part format with '-' separators."""
        ticket = create_ticket(
            short_description="Marsh-Mumbai-LAN-Need password reset of LAN"
        )
        result = short_desc_validator.validate(ticket)

        assert result.passed is True
        assert result.score == 8

    def test_compound_lob_mmc_ncl(self, short_desc_validator):
        """Test MMC-NCL compound LoB handling."""
        ticket = create_ticket(
            short_description="MMC-NCL Bangalore-VDI-error message"
        )
        result = short_desc_validator.validate(ticket)

        assert result.passed is True
        assert result.score == 8

    def test_missing_lob(self, short_desc_validator):
        """Test detection of missing LoB."""
        ticket = create_ticket(short_description="- Location - App - Brief")
        result = short_desc_validator.validate(ticket)

        assert result.score < 8
        assert "LoB" in result.reasoning or "Missing" in result.reasoning

    def test_missing_location(self, short_desc_validator):
        """Test detection of missing location."""
        ticket = create_ticket(short_description="MARSH - - App - Brief")
        result = short_desc_validator.validate(ticket)

        assert result.score < 8

    def test_missing_app(self, short_desc_validator):
        """Test detection of missing application."""
        ticket = create_ticket(short_description="MARSH - Location - - Brief")
        result = short_desc_validator.validate(ticket)

        assert result.score < 8

    def test_missing_brief(self, short_desc_validator):
        """Test detection of missing brief description."""
        ticket = create_ticket(short_description="MARSH - Location - App")
        result = short_desc_validator.validate(ticket)

        assert result.score < 8
        assert "brief" in result.reasoning.lower()

    def test_empty_short_description(self, short_desc_validator):
        """Test handling of empty short description."""
        ticket = create_ticket(short_description="")
        result = short_desc_validator.validate(ticket)

        assert result.passed is False
        assert result.score == 0
        assert result.coaching is not None

    def test_score_calculation_one_issue(self, short_desc_validator):
        """Test score of 6 for 1 issue."""
        # Missing brief = 1 issue
        ticket = create_ticket(short_description="MARSH - Mumbai - VDI")
        result = short_desc_validator.validate(ticket)

        assert result.score == 6

    def test_known_lob_patterns(self, short_desc_validator):
        """Test recognition of various LoB patterns."""
        lob_tests = [
            ("MARSH - Location - App - Brief", True),
            ("MERCER - Location - App - Brief", True),
            ("MMC - Location - App - Brief", True),
            ("GC - Location - App - Brief", True),
            ("OW - Location - App - Brief", True),
        ]

        for short_desc, should_pass in lob_tests:
            ticket = create_ticket(short_description=short_desc)
            result = short_desc_validator.validate(ticket)
            assert result.passed == should_pass, f"Failed for: {short_desc}"


# --- Validation Detector Tests ---


class TestValidationDetector:
    """Tests for ValidationDetector."""

    def test_okta_push_validation(self, validation_detector):
        """Test detection of OKTA Push MFA validation."""
        ticket = create_ticket(
            description="Validated by: Okta Push MFA & Full Name\n\nIssue details..."
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_okta_mfa_validation(self, validation_detector):
        """Test detection of OKTA MFA validation."""
        ticket = create_ticket(
            description="Validated by: OKTA MFA-N\nEmployee ID- 1251419"
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_employee_id_validation(self, validation_detector):
        """Test detection of Employee ID + name validation."""
        ticket = create_ticket(
            description="Validated by Employee ID, full name and Office location."
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_phone_missing_validation_fail(self, validation_detector):
        """Test FAIL for phone call without validation."""
        ticket = create_ticket(
            contact_type="phone",
            description="User called about VDI issue. Fixed by restart.",
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is False
        assert result.score == "FAIL"
        assert "validation" in result.coaching.lower()

    def test_phone_partial_validation_deduction(self, validation_detector):
        """Test -15 deduction for partial validation."""
        ticket = create_ticket(
            contact_type="phone",
            description="Validated by name only. Fixed the issue.",
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is False
        assert result.score == "-15"

    def test_self_service_no_validation_required(self, validation_detector):
        """Test N/A for self-service contact."""
        ticket = create_ticket(
            contact_type="self-service",
            description="User submitted request via portal.",
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "N/A"

    def test_email_validation_not_required(self, validation_detector):
        """Test email contact typically doesn't require validation."""
        ticket = create_ticket(
            contact_type="email", description="User sent email about issue."
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "N/A"

    def test_chat_with_okta(self, validation_detector):
        """Test chat with OKTA validation passes."""
        ticket = create_ticket(
            contact_type="chat",
            description="User contacted via chat. OKTA MFA verified.",
        )
        result = validation_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"


# --- Critical Process Detector Tests ---


class TestCriticalProcessDetector:
    """Tests for CriticalProcessDetector."""

    def test_no_critical_process(self, critical_process_detector):
        """Test N/A for non-critical process ticket."""
        ticket = create_ticket(
            subcategory="reset_restart",
            description="VDI not loading. Reset and fixed.",
            close_notes="Restarted VDI, issue resolved.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "N/A"

    def test_password_reset_with_trusted_colleague(self, critical_process_detector):
        """Test PASS for password reset with trusted colleague."""
        ticket = create_ticket(
            subcategory="password reset",
            description="User needs password reset.",
            close_notes="Shared password with Trusted Colleague via email.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_password_reset_with_manager(self, critical_process_detector):
        """Test PASS for password reset with manager."""
        ticket = create_ticket(
            subcategory="password reset",
            description="Password reset requested.",
            close_notes="New password sent to manager for delivery.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_password_reset_without_trusted_colleague(self, critical_process_detector):
        """Test FAIL for password reset without trusted colleague."""
        ticket = create_ticket(
            subcategory="password reset",
            description="User forgot password.",
            close_notes="Reset password and gave to user.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is False
        assert result.score == "FAIL"
        assert result.is_auto_fail is True

    def test_password_detection_from_description(self, critical_process_detector):
        """Test password reset detection from description."""
        ticket = create_ticket(
            subcategory="general",
            short_description="Marsh - Mumbai - LAN - Need password reset",
            description="User needs LAN password reset.",
            close_notes="Password reset with trusted colleague assistance.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_vip_correct_priority(self, critical_process_detector):
        """Test VIP ticket with correct priority passes."""
        ticket = create_ticket(
            priority="2",
            description="VIP executive having issues with laptop.",
            close_notes="Resolved laptop issue for executive.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is True
        assert result.score == "PASS"

    def test_vip_wrong_priority(self, critical_process_detector):
        """Test VIP ticket with wrong priority gets deduction."""
        ticket = create_ticket(
            priority="5",
            description="VIP executive having issues with laptop.",
            close_notes="Resolved issue.",
        )
        result = critical_process_detector.evaluate(ticket)

        assert result.passed is False
        assert result.score == "-35"


# --- Category Validator Tests ---


class TestCategoryValidator:
    """Tests for CategoryValidator."""

    def test_valid_category(self, category_validator):
        """Test valid category recognition."""
        ticket = create_ticket(category="software")
        result = category_validator.evaluate_category(ticket)

        assert result.passed is True
        assert result.score == 10

    def test_valid_subcategory(self, category_validator):
        """Test valid subcategory recognition."""
        ticket = create_ticket(category="software", subcategory="reset_restart")
        result = category_validator.evaluate_subcategory(ticket)

        assert result.passed is True
        assert result.score == 10

    def test_inquiry_password_reset(self, category_validator):
        """Test inquiry > password reset combination."""
        ticket = create_ticket(category="inquiry", subcategory="password reset")
        cat_result = category_validator.evaluate_category(ticket)
        sub_result = category_validator.evaluate_subcategory(ticket)

        assert cat_result.score == 10
        assert sub_result.score == 10

    def test_invalid_subcategory_for_category(self, category_validator):
        """Test subcategory not in category's list."""
        ticket = create_ticket(category="hardware", subcategory="password reset")
        result = category_validator.evaluate_subcategory(ticket)

        assert result.passed is True  # Rules assume valid, LLM verifies
        assert result.score == 5  # Reduced score

    def test_empty_category(self, category_validator):
        """Test empty category handling."""
        ticket = create_ticket(category="")
        result = category_validator.evaluate_category(ticket)

        assert result.passed is False
        assert result.score == 0

    def test_empty_subcategory(self, category_validator):
        """Test empty subcategory handling."""
        ticket = create_ticket(subcategory="")
        result = category_validator.evaluate_subcategory(ticket)

        assert result.passed is False
        assert result.score == 0

    def test_service_present(self, category_validator):
        """Test service reference present."""
        ticket = create_ticket(business_service="service_sys_id_123")
        result = category_validator.evaluate_service(ticket)

        assert result.passed is True
        assert result.score == 10

    def test_ci_present(self, category_validator):
        """Test CI reference present."""
        ticket = create_ticket(cmdb_ci="ci_sys_id_123")
        result = category_validator.evaluate_ci(ticket)

        assert result.passed is True
        assert result.score == 10


# --- Rules Evaluator Orchestrator Tests ---


class TestRulesEvaluator:
    """Tests for RulesEvaluator orchestration."""

    def test_incident_logging_evaluates_all_rules(self, rules_evaluator):
        """Test Incident Logging template evaluates correct rules."""
        ticket = create_ticket(
            short_description="MARSH - Mumbai - VDI - Issue description",
            description="Validated by: OKTA Push MFA",
        )
        results = rules_evaluator.evaluate(ticket, TemplateType.INCIDENT_LOGGING)

        # Should have: critical_process, validation, short_desc, category,
        # subcategory, service, ci
        assert len(results) == 7

        criterion_ids = {r.criterion_id for r in results}
        assert "critical_process_followed" in criterion_ids
        assert "validation_performed" in criterion_ids
        assert "short_description_format" in criterion_ids
        assert "category_selection" in criterion_ids
        assert "subcategory_selection" in criterion_ids

    def test_incident_handling_evaluates_rules(self, rules_evaluator):
        """Test Incident Handling template evaluates correct rules."""
        ticket = create_ticket(description="Validated by OKTA Push")
        results = rules_evaluator.evaluate(ticket, TemplateType.INCIDENT_HANDLING)

        # Should have: critical_process, validation, short_desc, category, subcategory
        assert len(results) == 5

    def test_customer_service_evaluates_rules(self, rules_evaluator):
        """Test Customer Service template evaluates correct rules."""
        ticket = create_ticket(description="Validated by OKTA Push")
        results = rules_evaluator.evaluate(ticket, TemplateType.CUSTOMER_SERVICE)

        # Should have: critical_process, validation, short_desc
        assert len(results) == 3

    def test_get_rule_scores_dict(self, rules_evaluator):
        """Test get_rule_scores returns dict keyed by criterion_id."""
        ticket = create_ticket(description="Validated by OKTA Push")
        scores = rules_evaluator.get_rule_scores(ticket, TemplateType.INCIDENT_LOGGING)

        assert isinstance(scores, dict)
        assert "short_description_format" in scores
        assert scores["short_description_format"].criterion_id == "short_description_format"

    def test_get_deductions_none(self, rules_evaluator):
        """Test get_deductions with no deductions."""
        ticket = create_ticket(
            description="Validated by OKTA Push",
            subcategory="reset_restart",
        )
        val_ded, cp_ded, auto_fail, reason = rules_evaluator.get_deductions(
            ticket, TemplateType.INCIDENT_LOGGING
        )

        assert val_ded == 0
        assert cp_ded == 0
        assert auto_fail is False
        assert reason is None

    def test_get_deductions_validation(self, rules_evaluator):
        """Test get_deductions with validation deduction."""
        ticket = create_ticket(
            contact_type="phone",
            description="Validated by name only",
            subcategory="reset_restart",
        )
        val_ded, cp_ded, auto_fail, _ = rules_evaluator.get_deductions(
            ticket, TemplateType.INCIDENT_LOGGING
        )

        assert val_ded == -15
        assert cp_ded == 0

    def test_summarize(self, rules_evaluator):
        """Test summarize returns correct structure."""
        ticket = create_ticket(description="Validated by OKTA Push")
        summary = rules_evaluator.summarize(ticket, TemplateType.INCIDENT_LOGGING)

        assert "template" in summary
        assert "ticket_number" in summary
        assert "rules_evaluated" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "base_score" in summary
        assert "validation_deduction" in summary
        assert "critical_process_deduction" in summary
        assert "auto_fail" in summary
        assert "coaching_needed" in summary


# --- Prototype Sample Tests ---


class TestPrototypeSamples:
    """Test against the prototype sample tickets."""

    def test_inc8924218_vdi_reset(self, sample_tickets, rules_evaluator):
        """Test INC8924218 - VDI reset ticket."""
        ticket = next(t for t in sample_tickets if t.number == "INC8924218")
        summary = rules_evaluator.summarize(ticket, TemplateType.INCIDENT_LOGGING)

        # Should pass all rules
        assert summary["failed"] == 0
        assert summary["auto_fail"] is False
        assert summary["validation_deduction"] == 0
        assert summary["critical_process_deduction"] == 0

    def test_inc8924339_password_reset(self, sample_tickets, rules_evaluator):
        """Test INC8924339 - Password reset ticket."""
        ticket = next(t for t in sample_tickets if t.number == "INC8924339")
        summary = rules_evaluator.summarize(ticket, TemplateType.INCIDENT_LOGGING)

        # Should pass - has trusted colleague documented
        assert summary["failed"] == 0
        assert summary["auto_fail"] is False

    def test_inc8923651_password_reset(self, sample_tickets, rules_evaluator):
        """Test INC8923651 - Password reset ticket."""
        ticket = next(t for t in sample_tickets if t.number == "INC8923651")
        summary = rules_evaluator.summarize(ticket, TemplateType.INCIDENT_LOGGING)

        # Should pass all rules
        assert summary["failed"] == 0
        assert summary["auto_fail"] is False

    def test_all_samples_pass_validation(self, sample_tickets, validation_detector):
        """Verify all sample tickets pass validation check."""
        for ticket in sample_tickets:
            result = validation_detector.evaluate(ticket)
            assert result.passed is True, f"{ticket.number} failed validation"
            assert result.score == "PASS", f"{ticket.number} didn't get PASS"

    def test_all_samples_pass_short_desc(self, sample_tickets, short_desc_validator):
        """Verify all sample tickets pass short description check."""
        for ticket in sample_tickets:
            result = short_desc_validator.validate(ticket)
            assert result.passed is True, f"{ticket.number} failed short desc"
            assert result.score == 8, f"{ticket.number} got {result.score}/8"
