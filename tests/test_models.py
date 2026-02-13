"""Tests for TQRS data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from tqrs.models import (
    AnalystReview,
    BatchEvaluationSummary,
    CriterionScore,
    EvaluationResult,
    PerformanceBand,
    TemplateType,
)


class TestPerformanceBand:
    """Tests for PerformanceBand enum."""

    def test_blue_threshold(self):
        assert PerformanceBand.from_percentage(95) == PerformanceBand.BLUE
        assert PerformanceBand.from_percentage(100) == PerformanceBand.BLUE
        assert PerformanceBand.from_percentage(95.5) == PerformanceBand.BLUE

    def test_green_threshold(self):
        assert PerformanceBand.from_percentage(90) == PerformanceBand.GREEN
        assert PerformanceBand.from_percentage(94.9) == PerformanceBand.GREEN

    def test_yellow_threshold(self):
        assert PerformanceBand.from_percentage(75) == PerformanceBand.YELLOW
        assert PerformanceBand.from_percentage(89.9) == PerformanceBand.YELLOW

    def test_red_threshold(self):
        assert PerformanceBand.from_percentage(50) == PerformanceBand.RED
        assert PerformanceBand.from_percentage(74.9) == PerformanceBand.RED

    def test_purple_threshold(self):
        assert PerformanceBand.from_percentage(49.9) == PerformanceBand.PURPLE
        assert PerformanceBand.from_percentage(0) == PerformanceBand.PURPLE

    def test_display_name(self):
        assert PerformanceBand.BLUE.display_name == "Blue"
        assert PerformanceBand.GREEN.display_name == "Green"

    def test_css_color(self):
        for band in PerformanceBand:
            color = band.css_color
            assert color.startswith("#")
            assert len(color) == 7


class TestCriterionScore:
    """Tests for CriterionScore model."""

    def test_create_valid_criterion_score(self):
        score = CriterionScore(
            criterion_id="test_criterion",
            criterion_name="Test Criterion",
            max_points=10,
            points_awarded=8,
            evidence="Found good documentation",
            reasoning="Documentation is complete and accurate",
            coaching=None,
        )
        assert score.points_awarded == 8
        assert score.is_perfect is False

    def test_percentage_calculation(self):
        score = CriterionScore(
            criterion_id="test",
            criterion_name="Test",
            max_points=10,
            points_awarded=8,
            evidence="test",
            reasoning="test",
        )
        assert score.percentage == 80.0

    def test_percentage_zero_max_points(self):
        score = CriterionScore(
            criterion_id="test",
            criterion_name="Test",
            max_points=0,
            points_awarded=0,
            evidence="test",
            reasoning="test",
        )
        assert score.percentage == 100.0

    def test_is_perfect(self):
        score = CriterionScore(
            criterion_id="test",
            criterion_name="Test",
            max_points=10,
            points_awarded=10,
            evidence="test",
            reasoning="test",
        )
        assert score.is_perfect is True


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    @pytest.fixture
    def sample_criteria(self) -> list[CriterionScore]:
        return [
            CriterionScore(
                criterion_id="correct_category",
                criterion_name="Category",
                max_points=5,
                points_awarded=5,
                evidence="Correct",
                reasoning="Category matches incident",
            ),
            CriterionScore(
                criterion_id="incident_notes",
                criterion_name="Incident Notes",
                max_points=20,
                points_awarded=18,
                evidence="Detailed",
                reasoning="Missing one element",
                coaching="Include error messages",
            ),
        ]

    def test_create_passing_evaluation(self, sample_criteria):
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.ONSITE_REVIEW,
            total_score=83,
            criterion_scores=sample_criteria,
            strengths=["Good documentation"],
            improvements=["Add more detail"],
        )
        assert result.passed is True
        assert result.percentage == pytest.approx(92.2, 0.1)
        assert result.band == PerformanceBand.GREEN

    def test_create_failing_evaluation(self, sample_criteria):
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.ONSITE_REVIEW,
            total_score=70,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=["Improve documentation"],
        )
        assert result.passed is False
        assert result.percentage == pytest.approx(77.8, 0.1)
        assert result.band == PerformanceBand.YELLOW

    def test_pass_threshold(self, sample_criteria):
        """Pass threshold should be 81 (90% of 90)."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.ONSITE_REVIEW,
            total_score=81,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        assert result.pass_threshold == 81
        assert result.passed is True

    def test_points_to_pass(self, sample_criteria):
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.ONSITE_REVIEW,
            total_score=75,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        assert result.points_to_pass == 6  # 81 - 75

    def test_get_criterion_by_id(self, sample_criteria):
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.ONSITE_REVIEW,
            total_score=83,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        crit = result.get_criterion_by_id("correct_category")
        assert crit is not None
        assert crit.points_awarded == 5

        missing = result.get_criterion_by_id("nonexistent")
        assert missing is None


class TestBatchEvaluationSummary:
    """Tests for BatchEvaluationSummary model."""

    def test_pass_rate_calculation(self):
        summary = BatchEvaluationSummary(
            total_tickets=100,
            passed_count=85,
            failed_count=15,
            average_score=78.0,
            average_percentage=86.7,
        )
        assert summary.pass_rate == 85.0

    def test_pass_rate_zero_tickets(self):
        summary = BatchEvaluationSummary(
            total_tickets=0,
            passed_count=0,
            failed_count=0,
            average_score=0,
            average_percentage=0,
        )
        assert summary.pass_rate == 0.0


class TestAnalystReview:
    """Tests for AnalystReview model."""

    def _make_eval(self, score: int) -> EvaluationResult:
        return EvaluationResult(
            ticket_number=f"INC{score}",
            template=TemplateType.ONSITE_REVIEW,
            total_score=score,
            criterion_scores=[],
            strengths=[],
            improvements=[],
        )

    def test_average_percentage(self):
        review = AnalystReview(
            analyst_id="analyst1",
            evaluations=[self._make_eval(81), self._make_eval(90), self._make_eval(72)],
        )
        # (90.0 + 100.0 + 80.0) / 3 = 90.0
        assert review.average_percentage == 90.0

    def test_passed_when_average_meets_threshold(self):
        review = AnalystReview(
            analyst_id="analyst1",
            evaluations=[self._make_eval(81), self._make_eval(90), self._make_eval(72)],
        )
        assert review.passed is True

    def test_failed_when_average_below_threshold(self):
        review = AnalystReview(
            analyst_id="analyst1",
            evaluations=[self._make_eval(60), self._make_eval(70), self._make_eval(50)],
        )
        assert review.passed is False

    def test_band_assignment(self):
        review = AnalystReview(
            analyst_id="analyst1",
            evaluations=[self._make_eval(90), self._make_eval(90), self._make_eval(90)],
        )
        assert review.band == PerformanceBand.BLUE

    def test_empty_evaluations(self):
        review = AnalystReview(
            analyst_id="analyst1",
            evaluations=[],
        )
        assert review.average_percentage == 0.0
        assert review.passed is False


class TestTemplateType:
    """Tests for TemplateType enum."""

    def test_single_template(self):
        assert len(TemplateType) == 1

    def test_template_value(self):
        assert TemplateType.ONSITE_REVIEW.value == "onsite_review"


class TestModelValidation:
    """Tests for Pydantic model validation."""

    def test_evaluation_result_score_bounds(self):
        with pytest.raises(ValidationError):
            EvaluationResult(
                ticket_number="INC123",
                template=TemplateType.ONSITE_REVIEW,
                total_score=91,  # Over max
                criterion_scores=[],
                strengths=[],
                improvements=[],
            )

        with pytest.raises(ValidationError):
            EvaluationResult(
                ticket_number="INC123",
                template=TemplateType.ONSITE_REVIEW,
                total_score=-1,  # Under min
                criterion_scores=[],
                strengths=[],
                improvements=[],
            )

    def test_criterion_score_requires_fields(self):
        with pytest.raises(ValidationError):
            CriterionScore(
                criterion_id="test",
                # Missing other required fields
            )
