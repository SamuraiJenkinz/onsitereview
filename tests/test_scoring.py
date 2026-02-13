"""Tests for the scoring engine module - Onsite Support Review (90 points)."""

import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from onsitereview.models.evaluation import (
    CriterionScore,
    EvaluationResult,
    PerformanceBand,
    TemplateType,
)
from onsitereview.models.ticket import ServiceNowTicket
from onsitereview.rules.base import RuleResult
from onsitereview.scoring import (
    ONSITE_REVIEW_CRITERIA,
    BatchProgress,
    BatchTicketEvaluator,
    ResultFormatter,
    ScoringCalculator,
    ScoringResult,
    TicketEvaluator,
    get_criteria,
    get_criterion_by_id,
    get_max_score,
)
from onsitereview.scoring.templates import TemplateCriterion


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
        opened_for="colleague123",
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
        business_service="VDI Service",
        cmdb_ci="VDI-NCL-001",
    )


@pytest.fixture
def rule_results() -> list[RuleResult]:
    """Opened For rule result - perfect score."""
    return [
        RuleResult(
            criterion_id="opened_for_correct",
            passed=True,
            score=10,
            max_score=10,
            evidence="Opened For: colleague123",
            reasoning="Opened For field is populated",
        ),
    ]


@pytest.fixture
def llm_results() -> list[RuleResult]:
    """LLM results for 7 criteria - perfect scores."""
    return [
        RuleResult(
            criterion_id="correct_category",
            passed=True,
            score=5,
            max_score=5,
            evidence="Category: software",
            reasoning="Correct category for VDI issue",
        ),
        RuleResult(
            criterion_id="correct_subcategory",
            passed=True,
            score=5,
            max_score=5,
            evidence="Subcategory: reset_restart",
            reasoning="Correct subcategory",
        ),
        RuleResult(
            criterion_id="correct_service",
            passed=True,
            score=5,
            max_score=5,
            evidence="Service: VDI Service",
            reasoning="Correct service identified",
        ),
        RuleResult(
            criterion_id="correct_ci",
            passed=True,
            score=10,
            max_score=10,
            evidence="CI: VDI-NCL-001",
            reasoning="Correct CI identified",
        ),
        RuleResult(
            criterion_id="incident_notes",
            passed=True,
            score=20,
            max_score=20,
            evidence="Comprehensive notes with contact info and troubleshooting",
            reasoning="All required elements present",
        ),
        RuleResult(
            criterion_id="incident_handling",
            passed=True,
            score=15,
            max_score=15,
            evidence="Resolved at first contact",
            reasoning="Correct handling procedure",
        ),
        RuleResult(
            criterion_id="resolution_notes",
            passed=True,
            score=20,
            max_score=20,
            evidence="VDI reset, colleague confirmed working",
            reasoning="Complete resolution with colleague confirmation",
        ),
    ]


# ============================================================================
# Template Tests
# ============================================================================


class TestTemplates:
    """Tests for onsite support review template criteria."""

    def test_max_score_is_90(self):
        """Total max score should be 90 points."""
        assert get_max_score() == 90

    def test_criteria_count(self):
        """Should have 8 criteria."""
        criteria = get_criteria()
        assert len(criteria) == 8

    def test_criteria_ids(self):
        """Should have the correct 8 criterion IDs."""
        criteria = get_criteria()
        ids = {c.criterion_id for c in criteria}
        expected = {
            "correct_category",
            "correct_subcategory",
            "correct_service",
            "correct_ci",
            "opened_for_correct",
            "incident_notes",
            "incident_handling",
            "resolution_notes",
        }
        assert ids == expected

    def test_criteria_points(self):
        """Each criterion should have correct max points."""
        expected_points = {
            "correct_category": 5,
            "correct_subcategory": 5,
            "correct_service": 5,
            "correct_ci": 10,
            "opened_for_correct": 10,
            "incident_notes": 20,
            "incident_handling": 15,
            "resolution_notes": 20,
        }
        for criterion in get_criteria():
            assert criterion.max_points == expected_points[criterion.criterion_id]

    def test_criteria_sources(self):
        """Opened For should be rules, rest should be LLM."""
        for criterion in get_criteria():
            if criterion.criterion_id == "opened_for_correct":
                assert criterion.source == "rules"
            else:
                assert criterion.source == "llm"

    def test_get_criterion_by_id(self):
        """Should find criterion by ID."""
        criterion = get_criterion_by_id("correct_category")
        assert criterion is not None
        assert criterion.criterion_name == "Category"
        assert criterion.max_points == 5

    def test_get_criterion_by_id_not_found(self):
        """Should return None for unknown criterion."""
        assert get_criterion_by_id("nonexistent") is None

    def test_template_criterion_dataclass(self):
        """TemplateCriterion should have correct fields."""
        criterion = TemplateCriterion(
            criterion_id="test",
            criterion_name="Test Criterion",
            max_points=10,
            source="rules",
        )
        assert criterion.criterion_id == "test"
        assert criterion.max_points == 10
        assert criterion.source == "rules"
        assert criterion.required is True

    def test_onsite_review_criteria_exported(self):
        """ONSITE_REVIEW_CRITERIA should be importable."""
        assert len(ONSITE_REVIEW_CRITERIA) == 8
        assert sum(c.max_points for c in ONSITE_REVIEW_CRITERIA) == 90


# ============================================================================
# Calculator Tests
# ============================================================================


class TestScoringCalculator:
    """Tests for the scoring calculator."""

    def test_perfect_score(self, rule_results, llm_results):
        """Perfect results should give 90/90."""
        calculator = ScoringCalculator()
        result = calculator.calculate_score(rule_results, llm_results)

        assert result.total_score == 90
        assert result.max_score == 90
        assert result.passed is True
        assert result.band == PerformanceBand.BLUE

    def test_zero_score(self):
        """No results should give 0/90."""
        calculator = ScoringCalculator()
        result = calculator.calculate_score([], [])

        assert result.total_score == 0
        assert result.max_score == 90
        assert result.passed is False
        assert result.band == PerformanceBand.PURPLE

    def test_partial_score(self, rule_results):
        """Rules only should give partial score."""
        calculator = ScoringCalculator()
        partial_llm = [
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=5,
                max_score=5,
                evidence="Correct",
                reasoning="OK",
            ),
            RuleResult(
                criterion_id="incident_notes",
                passed=True,
                score=10,
                max_score=20,
                evidence="Partial notes",
                reasoning="Missing some elements",
            ),
        ]
        result = calculator.calculate_score(rule_results, partial_llm)

        assert result.total_score == 25  # 10 + 5 + 10
        assert result.passed is False

    def test_score_capped_at_90(self):
        """Score should never exceed 90."""
        calculator = ScoringCalculator()
        overshoot_results = [
            RuleResult(
                criterion_id=f"test_{i}",
                passed=True,
                score=50,
                max_score=50,
                evidence="OK",
                reasoning="OK",
            )
            for i in range(3)
        ]
        result = calculator.calculate_score(overshoot_results, [])

        assert result.total_score == 90

    def test_pass_threshold_at_81(self):
        """81/90 should pass, 80/90 should fail."""
        calculator = ScoringCalculator()

        pass_results = [
            RuleResult(
                criterion_id="bulk",
                passed=True,
                score=81,
                max_score=90,
                evidence="OK",
                reasoning="OK",
            ),
        ]
        result = calculator.calculate_score(pass_results, [])
        assert result.passed is True

        fail_results = [
            RuleResult(
                criterion_id="bulk",
                passed=True,
                score=80,
                max_score=90,
                evidence="OK",
                reasoning="OK",
            ),
        ]
        result = calculator.calculate_score(fail_results, [])
        assert result.passed is False

    def test_performance_bands(self):
        """Performance bands should be assigned correctly."""
        calculator = ScoringCalculator()

        assert calculator.get_band(95.0) == PerformanceBand.BLUE
        assert calculator.get_band(100.0) == PerformanceBand.BLUE
        assert calculator.get_band(90.0) == PerformanceBand.GREEN
        assert calculator.get_band(94.9) == PerformanceBand.GREEN
        assert calculator.get_band(75.0) == PerformanceBand.YELLOW
        assert calculator.get_band(89.9) == PerformanceBand.YELLOW
        assert calculator.get_band(50.0) == PerformanceBand.RED
        assert calculator.get_band(74.9) == PerformanceBand.RED
        assert calculator.get_band(49.9) == PerformanceBand.PURPLE
        assert calculator.get_band(0.0) == PerformanceBand.PURPLE

    def test_calculate_percentage(self):
        """Should calculate percentage from score."""
        calculator = ScoringCalculator()

        assert calculator.calculate_percentage(90) == 100.0
        assert calculator.calculate_percentage(81) == 90.0
        assert calculator.calculate_percentage(45) == 50.0
        assert calculator.calculate_percentage(0) == 0.0

    def test_passed_method(self):
        """Should check pass threshold correctly."""
        calculator = ScoringCalculator()

        assert calculator.passed(90.0) is True
        assert calculator.passed(89.9) is False
        assert calculator.passed(100.0) is True
        assert calculator.passed(81 / 90 * 100) is True


# ============================================================================
# Formatter Tests
# ============================================================================


class TestResultFormatter:
    """Tests for result formatting."""

    def test_to_criterion_scores(self, rule_results, llm_results):
        """Should convert RuleResults to CriterionScores."""
        formatter = ResultFormatter()
        scores = formatter.to_criterion_scores(rule_results, llm_results)

        assert len(scores) == 8
        for score in scores:
            assert isinstance(score, CriterionScore)
            assert score.points_awarded >= 0

    def test_collect_strengths(self, rule_results, llm_results):
        """Should identify high-scoring criteria as strengths."""
        formatter = ResultFormatter()
        all_results = rule_results + llm_results
        strengths = formatter.collect_strengths(all_results)

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
                max_score=5,
                evidence="Wrong category",
                reasoning="Should be software",
                coaching="Use software category for VDI issues",
            ),
        ]

        improvements = formatter.collect_improvements(results)

        assert len(improvements) > 0
        assert any("Category" in i for i in improvements)

    def test_get_coaching_recommendations(self):
        """Should collect coaching recommendations."""
        formatter = ResultFormatter()

        results = [
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=0,
                max_score=5,
                evidence="Wrong category",
                reasoning="Better category available",
                coaching="Consider using 'software' for VDI issues",
            ),
            RuleResult(
                criterion_id="incident_notes",
                passed=True,
                score=10,
                max_score=20,
                evidence="Partial notes",
                reasoning="Missing contact info",
                coaching="Include contact number and working location",
            ),
        ]

        recommendations = formatter.get_coaching_recommendations(results)

        assert len(recommendations) == 2
        assert any("VDI" in r for r in recommendations)

    def test_format_summary_pass(self):
        """Should format passing summary."""
        formatter = ResultFormatter()
        summary = formatter.format_summary(total_score=85, max_score=90, passed=True)

        assert "85/90" in summary
        assert "PASS" in summary

    def test_format_summary_fail(self):
        """Should format failing summary."""
        formatter = ResultFormatter()
        summary = formatter.format_summary(total_score=70, max_score=90, passed=False)

        assert "70/90" in summary
        assert "FAIL" in summary

    def test_format_score_breakdown(self):
        """Should format criterion scores as text."""
        formatter = ResultFormatter()
        scores = [
            CriterionScore(
                criterion_id="correct_category",
                criterion_name="Category",
                max_points=5,
                points_awarded=5,
                evidence="OK",
                reasoning="OK",
            ),
            CriterionScore(
                criterion_id="incident_notes",
                criterion_name="Incident Notes",
                max_points=20,
                points_awarded=10,
                evidence="Partial",
                reasoning="Missing elements",
            ),
        ]
        breakdown = formatter.format_score_breakdown(scores)

        assert "Category: 5/5" in breakdown
        assert "Incident Notes: 10/20" in breakdown

    def test_generate_path_to_passing_already_passing(self):
        """Should congratulate when already passing."""
        formatter = ResultFormatter()
        scores = [
            CriterionScore(
                criterion_id="correct_category",
                criterion_name="Category",
                max_points=5,
                points_awarded=5,
                evidence="OK",
                reasoning="OK",
            ),
        ]

        recs = formatter.generate_path_to_passing(scores, total_score=85)
        assert len(recs) == 1
        assert recs[0]["category"] == "success"

    def test_generate_path_to_passing_needs_improvement(self):
        """Should generate recommendations when below passing."""
        formatter = ResultFormatter()
        scores = [
            CriterionScore(
                criterion_id="correct_category",
                criterion_name="Category",
                max_points=5,
                points_awarded=0,
                evidence="Wrong",
                reasoning="Incorrect",
                coaching="Select software category",
            ),
            CriterionScore(
                criterion_id="incident_notes",
                criterion_name="Incident Notes",
                max_points=20,
                points_awarded=10,
                evidence="Partial",
                reasoning="Missing elements",
                coaching="Include contact info",
            ),
        ]

        recs = formatter.generate_path_to_passing(scores, total_score=70)
        # Should have summary + individual recs
        assert len(recs) >= 2
        assert recs[0]["category"] == "summary"

    def test_criterion_improvement_actions(self):
        """Should generate specific improvement actions for known criteria."""
        formatter = ResultFormatter()
        opp = {
            "criterion_id": "opened_for_correct",
            "criterion_name": "Opened For",
            "current_score": 0,
            "max_score": 10,
            "points_lost": 10,
            "percentage": 0.0,
            "coaching": "Set the field",
        }
        action, details = formatter._get_criterion_improvement_action(opp)
        assert "Opened For" in action

    def test_format_category_names(self):
        """Should map criterion IDs to readable names."""
        formatter = ResultFormatter()
        names = formatter._format_category_names(
            ["correct_category", "opened_for_correct", "incident_notes"]
        )
        assert names == ["Category", "Opened For", "Incident Notes"]


# ============================================================================
# Evaluator Tests
# ============================================================================


class TestTicketEvaluator:
    """Tests for the ticket evaluator orchestrator."""

    def test_evaluate_with_mocked_llm(self, sample_ticket, llm_results):
        """Should run complete evaluation with mocked LLM."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = llm_results

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        result = evaluator.evaluate_ticket(sample_ticket)

        assert isinstance(result, EvaluationResult)
        assert result.ticket_number == "INC1234567"
        assert result.template == TemplateType.ONSITE_REVIEW
        assert result.max_score == 90
        assert 0 <= result.total_score <= 90

    def test_evaluate_rules_only(self, sample_ticket):
        """Should run rules-only evaluation."""
        evaluator = TicketEvaluator()
        results = evaluator.evaluate_rules_only(sample_ticket)

        assert isinstance(results, list)
        assert all(isinstance(r, RuleResult) for r in results)
        # Should have opened_for result
        assert any(r.criterion_id == "opened_for_correct" for r in results)

    def test_evaluate_llm_only_without_llm_raises(self, sample_ticket):
        """Should raise if no LLM configured for llm_only."""
        evaluator = TicketEvaluator()

        with pytest.raises(ValueError, match="No LLM evaluator"):
            evaluator.evaluate_llm_only(sample_ticket)

    def test_get_raw_results(self, sample_ticket):
        """Should return raw results tuple."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = []

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        rule_results, llm_results = evaluator.get_raw_results(sample_ticket)

        assert isinstance(rule_results, list)
        assert isinstance(llm_results, list)

    def test_get_coaching_recommendations(self, sample_ticket):
        """Should return coaching recommendations."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = [
            RuleResult(
                criterion_id="correct_category",
                passed=True,
                score=0,
                max_score=5,
                evidence="Wrong",
                reasoning="Incorrect",
                coaching="Use software category",
            ),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        recs = evaluator.get_coaching_recommendations(sample_ticket)

        assert isinstance(recs, list)

    def test_evaluate_without_llm(self, sample_ticket):
        """Should evaluate with rules only when no LLM configured."""
        evaluator = TicketEvaluator()
        result = evaluator.evaluate_ticket(sample_ticket)

        assert isinstance(result, EvaluationResult)
        assert result.total_score <= 90
        # Rules only gives max 10 points (Opened For)
        assert result.total_score <= 10


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

    def test_batch_progress_zero_total(self):
        """BatchProgress should handle zero total."""
        progress = BatchProgress(total=0, completed=0)
        assert progress.percentage == 100.0

    def test_batch_progress_estimated_remaining(self):
        """BatchProgress should estimate remaining time."""
        progress = BatchProgress(
            total=10, completed=5, start_time=time.time() - 10
        )

        remaining = progress.estimated_remaining_seconds
        assert 8 <= remaining <= 12

    def test_evaluate_batch(self, sample_ticket, llm_results):
        """Should evaluate batch of tickets."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = llm_results

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets)

        assert len(result.results) == 2
        assert len(result.errors) == 0
        assert result.summary.total_tickets == 2

    def test_batch_with_progress_callback(self, sample_ticket, llm_results):
        """Should call progress callback."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = llm_results

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        progress_updates = []

        def callback(progress: BatchProgress):
            progress_updates.append(progress.completed)

        tickets = [sample_ticket, sample_ticket]
        batch_evaluator.evaluate_batch(tickets, progress_callback=callback)

        assert len(progress_updates) >= 2

    def test_batch_handles_errors(self, sample_ticket, llm_results):
        """Should handle evaluation errors gracefully."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.side_effect = [
            llm_results,
            Exception("API Error"),
        ]

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        batch_evaluator = BatchTicketEvaluator(evaluator)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets)

        assert len(result.results) == 1
        assert len(result.errors) == 1
        assert "API Error" in result.errors[0][1]

    def test_generate_summary(self):
        """Should generate batch summary."""
        batch_evaluator = BatchTicketEvaluator(MagicMock())

        results = [
            EvaluationResult(
                ticket_number="INC001",
                template=TemplateType.ONSITE_REVIEW,
                total_score=90,
                max_score=90,
                criterion_scores=[],
            ),
            EvaluationResult(
                ticket_number="INC002",
                template=TemplateType.ONSITE_REVIEW,
                total_score=70,
                max_score=90,
                criterion_scores=[],
            ),
        ]

        summary = batch_evaluator.generate_summary(results)

        assert summary.total_tickets == 2
        assert summary.passed_count == 1  # 90/90 passes
        assert summary.failed_count == 1  # 70/90 fails
        assert summary.average_score == 80.0
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

    def test_full_pipeline_perfect_ticket(self, sample_ticket, llm_results):
        """Full evaluation pipeline for a perfect ticket."""
        mock_llm = MagicMock()
        mock_llm.evaluate_ticket.return_value = llm_results

        evaluator = TicketEvaluator(llm_evaluator=mock_llm)
        result = evaluator.evaluate_ticket(sample_ticket)

        assert result.ticket_number == sample_ticket.number
        assert result.template == TemplateType.ONSITE_REVIEW
        assert result.max_score == 90
        assert result.total_score == 90
        assert len(result.criterion_scores) == 8
        assert result.evaluation_time_seconds > 0
        assert result.passed is True
        assert result.band == PerformanceBand.BLUE

    def test_scoring_calculator_with_evaluator(self, sample_ticket):
        """Calculator should work with evaluator results."""
        evaluator = TicketEvaluator()
        calculator = ScoringCalculator()

        rule_results = evaluator.evaluate_rules_only(sample_ticket)
        scoring_result = calculator.calculate_score(rule_results, [])

        assert isinstance(scoring_result, ScoringResult)
        assert scoring_result.max_score == 90

    def test_formatter_with_evaluator(self, sample_ticket):
        """Formatter should work with evaluator results."""
        evaluator = TicketEvaluator()
        formatter = ResultFormatter()

        rule_results = evaluator.evaluate_rules_only(sample_ticket)
        criterion_scores = formatter.to_criterion_scores(rule_results, [])

        assert isinstance(criterion_scores, list)
        for score in criterion_scores:
            assert isinstance(score, CriterionScore)
