"""Tests for the scoring engine module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tqrs.models.evaluation import (
    CriterionScore,
    EvaluationResult,
    PerformanceBand,
    TemplateType,
)
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult
from tqrs.scoring import (
    BatchProgress,
    BatchTicketEvaluator,
    ResultFormatter,
    ScoringCalculator,
    ScoringResult,
    TicketEvaluator,
    get_criterion_by_id,
    get_deduction_criteria,
    get_scoring_criteria,
    get_template_criteria,
    get_template_max_score,
)
from tqrs.scoring.templates import (
    CUSTOMER_SERVICE_CRITERIA,
    INCIDENT_HANDLING_CRITERIA,
    INCIDENT_LOGGING_CRITERIA,
    TemplateCriterion,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ticket() -> ServiceNowTicket:
    """Create a sample ticket for testing."""
    return ServiceNowTicket(
        number="INC1234567",
        sys_id="abc123",
        opened_at=datetime(2025, 12, 10, 4, 26, 0),
        resolved_at=datetime(2025, 12, 10, 4, 41, 0),
        closed_at=datetime(2025, 12, 15, 5, 0, 0),
        caller_id="caller123",
        opened_by="agent123",
        assigned_to="agent123",
        resolved_by="agent123",
        closed_by="agent123",
        short_description="MMC-NCL Bangalore-VDI-error message",
        description=(
            "Validated by: Okta Push MFA & Full Name\n\n"
            "Contact Number: 1234567890\n"
            "Working remotely: Y\n\n"
            "Issue/Request: Colleague is getting error message"
        ),
        close_notes="VDI reset, colleague confirmed working",
        category="software",
        subcategory="reset_restart",
        contact_type="phone",
        state="7",
        incident_state="7",
        priority="5",
        impact="3",
        urgency="3",
        company="company123",
        location="location123",
        assignment_group="group123",
    )


@pytest.fixture
def perfect_rule_results() -> list[RuleResult]:
    """Create perfect rule results for testing."""
    return [
        RuleResult(
            criterion_id="critical_process_followed",
            passed=True,
            score="PASS",
            max_score=None,
            evidence="Password reset followed correct process",
            reasoning="All steps completed correctly",
        ),
        RuleResult(
            criterion_id="validation_performed",
            passed=True,
            score="PASS",
            max_score=None,
            evidence="OKTA Push MFA verified",
            reasoning="Validation documented correctly",
        ),
        RuleResult(
            criterion_id="correct_category",
            passed=True,
            score=10,
            max_score=10,
            evidence="Category: software",
            reasoning="Correct category for VDI issue",
        ),
        RuleResult(
            criterion_id="correct_subcategory",
            passed=True,
            score=10,
            max_score=10,
            evidence="Subcategory: reset_restart",
            reasoning="Correct subcategory",
        ),
        RuleResult(
            criterion_id="short_description_format",
            passed=True,
            score=8,
            max_score=8,
            evidence="MMC-NCL Bangalore-VDI-error message",
            reasoning="4-part format followed",
        ),
    ]


@pytest.fixture
def perfect_llm_results() -> list[RuleResult]:
    """Create perfect LLM results for testing."""
    return [
        RuleResult(
            criterion_id="accurate_description",
            passed=True,
            score=20,
            max_score=20,
            evidence="Clear issue description with context",
            reasoning="All required elements present",
        ),
        RuleResult(
            criterion_id="spelling_grammar",
            passed=True,
            score=2,
            max_score=2,
            evidence="No errors found",
            reasoning="Perfect spelling and grammar",
        ),
    ]


# ============================================================================
# Template Tests
# ============================================================================


class TestTemplates:
    """Tests for template criterion mappings."""

    def test_incident_logging_max_score(self):
        """Incident Logging template should sum to 70 points."""
        max_score = get_template_max_score(TemplateType.INCIDENT_LOGGING)
        assert max_score == 70

    def test_incident_handling_max_score(self):
        """Incident Handling template should sum to 70 points."""
        max_score = get_template_max_score(TemplateType.INCIDENT_HANDLING)
        assert max_score == 70

    def test_customer_service_max_score(self):
        """Customer Service template should sum to 70 points."""
        max_score = get_template_max_score(TemplateType.CUSTOMER_SERVICE)
        assert max_score == 70

    def test_incident_logging_criteria_count(self):
        """Incident Logging should have 9 criteria."""
        criteria = get_template_criteria(TemplateType.INCIDENT_LOGGING)
        assert len(criteria) == 9

    def test_incident_handling_criteria_count(self):
        """Incident Handling should have 8 criteria."""
        criteria = get_template_criteria(TemplateType.INCIDENT_HANDLING)
        assert len(criteria) == 8

    def test_customer_service_criteria_count(self):
        """Customer Service should have 9 criteria."""
        criteria = get_template_criteria(TemplateType.CUSTOMER_SERVICE)
        assert len(criteria) == 9

    def test_deduction_criteria_present(self):
        """All templates should have 2 deduction criteria."""
        for template in TemplateType:
            deductions = get_deduction_criteria(template)
            assert len(deductions) == 2
            assert any(d.criterion_id == "critical_process_followed" for d in deductions)
            assert any(d.criterion_id == "validation_performed" for d in deductions)

    def test_scoring_criteria_excludes_deductions(self):
        """Scoring criteria should exclude deductions."""
        for template in TemplateType:
            scoring = get_scoring_criteria(template)
            deductions = get_deduction_criteria(template)
            all_criteria = get_template_criteria(template)

            assert len(scoring) + len(deductions) == len(all_criteria)
            for criterion in scoring:
                assert not criterion.is_deduction

    def test_get_criterion_by_id(self):
        """Should find criterion by ID."""
        criterion = get_criterion_by_id(
            TemplateType.INCIDENT_LOGGING, "correct_category"
        )
        assert criterion is not None
        assert criterion.criterion_name == "Category"
        assert criterion.max_points == 10

    def test_get_criterion_by_id_not_found(self):
        """Should return None for unknown criterion."""
        criterion = get_criterion_by_id(
            TemplateType.INCIDENT_LOGGING, "nonexistent"
        )
        assert criterion is None

    def test_template_criterion_dataclass(self):
        """TemplateCriterion should have correct fields."""
        criterion = TemplateCriterion(
            criterion_id="test",
            criterion_name="Test Criterion",
            max_points=10,
            source="rules",
            required=True,
            is_deduction=False,
        )
        assert criterion.criterion_id == "test"
        assert criterion.max_points == 10
        assert criterion.source == "rules"


# ============================================================================
# Calculator Tests
# ============================================================================


class TestScoringCalculator:
    """Tests for the scoring calculator."""

    def test_perfect_score(self, perfect_rule_results, perfect_llm_results):
        """Perfect results should give 70/70."""
        calculator = ScoringCalculator()
        # Add more results to reach 70 points
        extended_rules = perfect_rule_results + [
            RuleResult(
                criterion_id="correct_service",
                passed=True,
                score=10,
                max_score=10,
                evidence="Correct service",
                reasoning="Service matched",
            ),
            RuleResult(
                criterion_id="correct_ci",
                passed=True,
                score=10,
                max_score=10,
                evidence="Correct CI",
                reasoning="CI matched",
            ),
        ]

        result = calculator.calculate_score(
            extended_rules, perfect_llm_results, TemplateType.INCIDENT_LOGGING
        )

        assert result.final_score == 70
        assert result.auto_fail is False
        assert result.passed is True
        assert result.band == PerformanceBand.BLUE

    def test_validation_deduction(self):
        """Validation -15 should reduce score."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="validation_performed",
                passed=False,
                score="-15",
                max_score=None,
                evidence="Validation not documented",
                reasoning="Documentation missing",
            ),
            RuleResult(
                criterion_id="critical_process_followed",
                passed=True,
                score="PASS",
                max_score=None,
                evidence="Process followed",
                reasoning="OK",
            ),
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=10,
                max_score=10,
                evidence="Category correct",
                reasoning="OK",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert result.base_score == 10
        assert result.validation_deduction == -15
        assert result.final_score == 0  # 10 - 15 = -5, capped at 0

    def test_critical_process_deduction(self):
        """Critical process -35 should reduce score."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="critical_process_followed",
                passed=False,
                score="-35",
                max_score=None,
                evidence="Process not followed",
                reasoning="Escalation missed",
            ),
            RuleResult(
                criterion_id="validation_performed",
                passed=True,
                score="PASS",
                max_score=None,
                evidence="Validated",
                reasoning="OK",
            ),
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=10,
                max_score=10,
                evidence="Category correct",
                reasoning="OK",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert result.base_score == 10
        assert result.critical_process_deduction == -35
        assert result.final_score == 0  # 10 - 35 = -25, capped at 0

    def test_validation_auto_fail(self):
        """Validation FAIL should trigger auto-fail."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="validation_performed",
                passed=False,
                score="FAIL",
                max_score=None,
                evidence="Identity not verified",
                reasoning="Security violation",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert result.auto_fail is True
        assert result.final_score == 0
        assert result.passed is False
        assert result.band == PerformanceBand.PURPLE

    def test_critical_process_auto_fail(self):
        """Critical process FAIL should trigger auto-fail."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="critical_process_followed",
                passed=False,
                score="FAIL",
                max_score=None,
                evidence="Password process violated",
                reasoning="Security incident",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert result.auto_fail is True
        assert result.auto_fail_reason is not None
        assert "password" in result.auto_fail_reason.lower()

    def test_score_capped_at_zero(self):
        """Score should never go below 0."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="validation_performed",
                passed=False,
                score="-15",
                max_score=None,
                evidence="Not documented",
                reasoning="Missing",
            ),
            RuleResult(
                criterion_id="critical_process_followed",
                passed=False,
                score="-35",
                max_score=None,
                evidence="Not followed",
                reasoning="Missing",
            ),
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=5,
                max_score=10,
                evidence="Partial",
                reasoning="Acceptable",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        # 5 - 15 - 35 = -45, but capped at 0
        assert result.final_score == 0
        assert result.final_score >= 0

    def test_na_score_handling(self):
        """N/A scores should not affect base score."""
        calculator = ScoringCalculator()

        rule_results = [
            RuleResult(
                criterion_id="critical_process_followed",
                passed=True,
                score="N/A",
                max_score=None,
                evidence="No critical process",
                reasoning="Not applicable",
            ),
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=10,
                max_score=10,
                evidence="Correct",
                reasoning="OK",
            ),
        ]

        result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert result.base_score == 10

    def test_performance_bands(self):
        """Performance bands should be assigned correctly."""
        calculator = ScoringCalculator()

        # Test BLUE (>= 95%)
        assert calculator.get_band(95.0) == PerformanceBand.BLUE
        assert calculator.get_band(100.0) == PerformanceBand.BLUE

        # Test GREEN (>= 90%)
        assert calculator.get_band(90.0) == PerformanceBand.GREEN
        assert calculator.get_band(94.9) == PerformanceBand.GREEN

        # Test YELLOW (>= 75%)
        assert calculator.get_band(75.0) == PerformanceBand.YELLOW
        assert calculator.get_band(89.9) == PerformanceBand.YELLOW

        # Test RED (>= 50%)
        assert calculator.get_band(50.0) == PerformanceBand.RED
        assert calculator.get_band(74.9) == PerformanceBand.RED

        # Test PURPLE (< 50%)
        assert calculator.get_band(49.9) == PerformanceBand.PURPLE
        assert calculator.get_band(0.0) == PerformanceBand.PURPLE

    def test_pass_threshold(self):
        """Pass threshold should be 90%."""
        calculator = ScoringCalculator()

        assert calculator.passed(90.0) is True
        assert calculator.passed(89.9) is False
        assert calculator.passed(100.0) is True
        assert calculator.passed(63 / 70 * 100) is True  # Exactly 63/70


# ============================================================================
# Formatter Tests
# ============================================================================


class TestResultFormatter:
    """Tests for result formatting."""

    def test_to_criterion_scores(self, perfect_rule_results, perfect_llm_results):
        """Should convert RuleResults to CriterionScores."""
        formatter = ResultFormatter()

        scores = formatter.to_criterion_scores(
            perfect_rule_results,
            perfect_llm_results,
            TemplateType.INCIDENT_LOGGING,
        )

        assert len(scores) > 0
        for score in scores:
            assert isinstance(score, CriterionScore)
            assert score.points_awarded >= 0

    def test_collect_strengths(self, perfect_rule_results):
        """Should identify high-scoring criteria as strengths."""
        formatter = ResultFormatter()

        strengths = formatter.collect_strengths(
            perfect_rule_results, TemplateType.INCIDENT_LOGGING
        )

        assert len(strengths) > 0
        # Perfect scores should be identified as strengths
        assert any("Category" in s for s in strengths)

    def test_collect_improvements(self):
        """Should identify low-scoring criteria for improvement."""
        formatter = ResultFormatter()

        results = [
            RuleResult(
                criterion_id="correct_category",
                passed=False,
                score=0,
                max_score=10,
                evidence="Wrong category",
                reasoning="Should be software",
                coaching="Use software category for VDI issues",
            ),
        ]

        improvements = formatter.collect_improvements(
            results, TemplateType.INCIDENT_LOGGING
        )

        assert len(improvements) > 0
        assert any("Category" in i for i in improvements)

    def test_collect_improvements_for_deductions(self):
        """Should identify deductions as improvement areas."""
        formatter = ResultFormatter()

        results = [
            RuleResult(
                criterion_id="validation_performed",
                passed=False,
                score="-15",
                max_score=None,
                evidence="Not documented",
                reasoning="Validation missing from description",
            ),
        ]

        improvements = formatter.collect_improvements(
            results, TemplateType.INCIDENT_LOGGING
        )

        assert len(improvements) > 0
        assert any("Validation" in i for i in improvements)

    def test_get_coaching_recommendations(self):
        """Should collect coaching recommendations."""
        formatter = ResultFormatter()

        results = [
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=5,
                max_score=10,
                evidence="Partial match",
                reasoning="Better category available",
                coaching="Consider using 'software' for VDI issues",
            ),
            RuleResult(
                criterion_id="short_description_format",
                passed=True,
                score=6,
                max_score=8,
                evidence="3 parts",
                reasoning="Missing one part",
                coaching="Include application name in short description",
            ),
        ]

        recommendations = formatter.get_coaching_recommendations(
            results, TemplateType.INCIDENT_LOGGING
        )

        assert len(recommendations) == 2
        assert any("VDI" in r for r in recommendations)

    def test_format_summary(self):
        """Should format evaluation summary."""
        formatter = ResultFormatter()

        summary = formatter.format_summary(
            total_score=65,
            max_score=70,
            passed=True,
            auto_fail=False,
        )

        assert "65/70" in summary
        assert "PASS" in summary

    def test_format_summary_auto_fail(self):
        """Should format auto-fail summary."""
        formatter = ResultFormatter()

        summary = formatter.format_summary(
            total_score=0,
            max_score=70,
            passed=False,
            auto_fail=True,
            auto_fail_reason="Validation not performed",
        )

        assert "AUTO-FAIL" in summary
        assert "Validation" in summary


# ============================================================================
# Evaluator Tests
# ============================================================================


class TestTicketEvaluator:
    """Tests for the ticket evaluator orchestrator."""

    def test_evaluate_with_mocked_llm(self, sample_ticket):
        """Should run complete evaluation with mocked LLM."""
        # Mock the LLM evaluator
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = [
            RuleResult(
                criterion_id="accurate_description",
                passed=True,
                score=20,
                max_score=20,
                evidence="Good description",
                reasoning="Complete",
            ),
            RuleResult(
                criterion_id="spelling_grammar",
                passed=True,
                score=2,
                max_score=2,
                evidence="No errors",
                reasoning="Perfect",
            ),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        result = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_LOGGING)

        assert isinstance(result, EvaluationResult)
        assert result.ticket_number == "INC1234567"
        assert result.template == TemplateType.INCIDENT_LOGGING
        assert result.total_score <= 70
        assert result.max_score == 70

    def test_evaluate_rules_only(self, sample_ticket):
        """Should run rules-only evaluation."""
        evaluator = TicketEvaluator()
        results = evaluator.evaluate_rules_only(sample_ticket, TemplateType.INCIDENT_LOGGING)

        assert isinstance(results, list)
        assert all(isinstance(r, RuleResult) for r in results)

    def test_evaluate_llm_only_without_llm_raises(self, sample_ticket):
        """Should raise if no LLM configured for llm_only."""
        evaluator = TicketEvaluator()

        with pytest.raises(ValueError, match="No LLM evaluator"):
            evaluator.evaluate_llm_only(sample_ticket, TemplateType.INCIDENT_LOGGING)

    def test_check_auto_fail(self, sample_ticket):
        """Should check for auto-fail conditions."""
        evaluator = TicketEvaluator()
        is_auto_fail, reason = evaluator.check_auto_fail(
            sample_ticket, TemplateType.INCIDENT_LOGGING
        )

        # Sample ticket has validation, should not auto-fail
        assert is_auto_fail is False
        assert reason is None

    def test_get_raw_results(self, sample_ticket):
        """Should return raw results."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = []

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        rule_results, llm_results = evaluator.get_raw_results(
            sample_ticket, TemplateType.INCIDENT_LOGGING
        )

        assert isinstance(rule_results, list)
        assert isinstance(llm_results, list)


# ============================================================================
# Batch Evaluator Tests
# ============================================================================


class TestBatchTicketEvaluator:
    """Tests for batch ticket evaluation."""

    def test_batch_progress(self):
        """BatchProgress should track progress correctly."""
        progress = BatchProgress(total=10, completed=5)

        assert progress.percentage == 50.0
        assert progress.elapsed_seconds >= 0

    def test_batch_progress_estimated_remaining(self):
        """BatchProgress should estimate remaining time."""
        import time

        progress = BatchProgress(total=10, completed=5, start_time=time.time() - 10)

        # If 5 done in 10 seconds, remaining 5 should take ~10 seconds
        remaining = progress.estimated_remaining_seconds
        assert 8 <= remaining <= 12

    def test_evaluate_batch(self, sample_ticket):
        """Should evaluate batch of tickets."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = [
            RuleResult(
                criterion_id="accurate_description",
                passed=True,
                score=20,
                max_score=20,
                evidence="Good",
                reasoning="Complete",
            ),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets, TemplateType.INCIDENT_LOGGING)

        assert len(result.results) == 2
        assert len(result.errors) == 0
        assert result.summary.total_tickets == 2

    def test_batch_with_progress_callback(self, sample_ticket):
        """Should call progress callback."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = []

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        progress_updates = []

        def callback(progress: BatchProgress):
            progress_updates.append(progress.completed)

        tickets = [sample_ticket, sample_ticket]
        batch_evaluator.evaluate_batch(
            tickets, TemplateType.INCIDENT_LOGGING, progress_callback=callback
        )

        # Should have at least 2 updates (one per ticket + final)
        assert len(progress_updates) >= 2

    def test_batch_handles_errors(self, sample_ticket):
        """Should handle evaluation errors gracefully."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.side_effect = [
            [RuleResult(
                criterion_id="test",
                passed=True,
                score=10,
                max_score=10,
                evidence="OK",
                reasoning="OK",
            )],
            Exception("API Error"),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets, TemplateType.INCIDENT_LOGGING)

        assert len(result.results) == 1  # One success
        assert len(result.errors) == 1  # One error
        assert "API Error" in result.errors[0][1]

    def test_generate_summary(self):
        """Should generate batch summary."""
        batch_evaluator = BatchTicketEvaluator(MagicMock())

        results = [
            EvaluationResult(
                ticket_number="INC001",
                template=TemplateType.INCIDENT_LOGGING,
                total_score=70,
                max_score=70,
                criterion_scores=[],
            ),
            EvaluationResult(
                ticket_number="INC002",
                template=TemplateType.INCIDENT_LOGGING,
                total_score=60,
                max_score=70,
                criterion_scores=[],
            ),
        ]

        summary = batch_evaluator.generate_summary(results)

        assert summary.total_tickets == 2
        assert summary.passed_count == 1
        assert summary.failed_count == 1
        assert summary.average_score == 65.0
        assert PerformanceBand.BLUE.value in summary.band_distribution

    def test_generate_summary_empty(self):
        """Should handle empty results."""
        batch_evaluator = BatchTicketEvaluator(MagicMock())

        summary = batch_evaluator.generate_summary([])

        assert summary.total_tickets == 0
        assert summary.average_score == 0.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline_perfect_ticket(self, sample_ticket):
        """Full evaluation pipeline for a perfect ticket."""
        # Mock LLM with perfect responses
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = [
            RuleResult(
                criterion_id="accurate_description",
                passed=True,
                score=20,
                max_score=20,
                evidence="Complete description",
                reasoning="All elements present",
            ),
            RuleResult(
                criterion_id="spelling_grammar",
                passed=True,
                score=2,
                max_score=2,
                evidence="No errors",
                reasoning="Perfect",
            ),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        result = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_LOGGING)

        # Validate result structure
        assert result.ticket_number == sample_ticket.number
        assert result.template == TemplateType.INCIDENT_LOGGING
        assert result.max_score == 70
        assert 0 <= result.total_score <= 70
        assert len(result.criterion_scores) > 0
        assert result.evaluation_time_seconds > 0

    def test_scoring_calculator_with_evaluator(self, sample_ticket):
        """Calculator should work with evaluator results."""
        evaluator = TicketEvaluator()
        calculator = ScoringCalculator()

        rule_results = evaluator.evaluate_rules_only(sample_ticket, TemplateType.INCIDENT_LOGGING)
        scoring_result = calculator.calculate_score(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert isinstance(scoring_result, ScoringResult)
        assert scoring_result.max_score == 70

    def test_formatter_with_evaluator(self, sample_ticket):
        """Formatter should work with evaluator results."""
        evaluator = TicketEvaluator()
        formatter = ResultFormatter()

        rule_results = evaluator.evaluate_rules_only(sample_ticket, TemplateType.INCIDENT_LOGGING)
        criterion_scores = formatter.to_criterion_scores(
            rule_results, [], TemplateType.INCIDENT_LOGGING
        )

        assert isinstance(criterion_scores, list)
        for score in criterion_scores:
            assert isinstance(score, CriterionScore)
