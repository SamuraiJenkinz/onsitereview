"""Tests for TQRS data models."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tqrs.models import (
    BatchEvaluationSummary,
    CriterionScore,
    EvaluationResult,
    PerformanceBand,
    ScoringRubric,
    TemplateType,
    load_rubrics,
)


class TestPerformanceBand:
    """Tests for PerformanceBand enum."""

    def test_blue_threshold(self):
        """Blue band should be >= 95%."""
        assert PerformanceBand.from_percentage(95) == PerformanceBand.BLUE
        assert PerformanceBand.from_percentage(100) == PerformanceBand.BLUE
        assert PerformanceBand.from_percentage(95.5) == PerformanceBand.BLUE

    def test_green_threshold(self):
        """Green band should be >= 90% and < 95%."""
        assert PerformanceBand.from_percentage(90) == PerformanceBand.GREEN
        assert PerformanceBand.from_percentage(94.9) == PerformanceBand.GREEN

    def test_yellow_threshold(self):
        """Yellow band should be >= 75% and < 90%."""
        assert PerformanceBand.from_percentage(75) == PerformanceBand.YELLOW
        assert PerformanceBand.from_percentage(89.9) == PerformanceBand.YELLOW

    def test_red_threshold(self):
        """Red band should be >= 50% and < 75%."""
        assert PerformanceBand.from_percentage(50) == PerformanceBand.RED
        assert PerformanceBand.from_percentage(74.9) == PerformanceBand.RED

    def test_purple_threshold(self):
        """Purple band should be < 50%."""
        assert PerformanceBand.from_percentage(49.9) == PerformanceBand.PURPLE
        assert PerformanceBand.from_percentage(0) == PerformanceBand.PURPLE

    def test_display_name(self):
        """Display name should be capitalized."""
        assert PerformanceBand.BLUE.display_name == "Blue"
        assert PerformanceBand.GREEN.display_name == "Green"

    def test_css_color(self):
        """CSS colors should be valid hex codes."""
        for band in PerformanceBand:
            color = band.css_color
            assert color.startswith("#")
            assert len(color) == 7


class TestCriterionScore:
    """Tests for CriterionScore model."""

    def test_create_valid_criterion_score(self):
        """Should create valid criterion score."""
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
        """Percentage should be calculated correctly."""
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
        """Percentage should be 100 when max_points is 0."""
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
        """is_perfect should be True when max points awarded."""
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
        """Create sample criterion scores."""
        return [
            CriterionScore(
                criterion_id="short_desc",
                criterion_name="Short Description",
                max_points=8,
                points_awarded=8,
                evidence="Good format",
                reasoning="Follows 4-part format",
            ),
            CriterionScore(
                criterion_id="description",
                criterion_name="Description",
                max_points=20,
                points_awarded=18,
                evidence="Detailed",
                reasoning="Missing one element",
                coaching="Include error messages",
            ),
        ]

    def test_create_passing_evaluation(self, sample_criteria: list[CriterionScore]):
        """Should create evaluation that passes."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=65,
            criterion_scores=sample_criteria,
            strengths=["Good documentation"],
            improvements=["Add more detail"],
        )
        assert result.passed is True
        assert result.percentage == pytest.approx(92.9, 0.1)
        assert result.band == PerformanceBand.GREEN

    def test_create_failing_evaluation(self, sample_criteria: list[CriterionScore]):
        """Should create evaluation that fails."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=55,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=["Improve documentation"],
        )
        assert result.passed is False
        assert result.percentage == pytest.approx(78.6, 0.1)
        assert result.band == PerformanceBand.YELLOW

    def test_auto_fail_evaluation(self, sample_criteria: list[CriterionScore]):
        """Auto-fail should result in 0% and failed status."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=65,  # Would pass normally
            criterion_scores=sample_criteria,
            auto_fail=True,
            auto_fail_reason="Password process violation",
            strengths=[],
            improvements=[],
        )
        assert result.passed is False
        assert result.percentage == 0.0
        assert result.band == PerformanceBand.PURPLE

    def test_pass_threshold(self, sample_criteria: list[CriterionScore]):
        """Pass threshold should be 63 (90% of 70)."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=63,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        assert result.pass_threshold == 63
        assert result.passed is True  # Exactly at threshold

    def test_points_to_pass(self, sample_criteria: list[CriterionScore]):
        """Should calculate points needed to pass."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=58,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        assert result.points_to_pass == 5  # 63 - 58

    def test_total_deductions(self, sample_criteria: list[CriterionScore]):
        """Should sum all deductions."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=40,
            criterion_scores=sample_criteria,
            validation_deduction=-15,
            critical_process_deduction=-35,
            strengths=[],
            improvements=[],
        )
        assert result.total_deductions == 50

    def test_get_criterion_by_id(self, sample_criteria: list[CriterionScore]):
        """Should retrieve criterion by ID."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=65,
            criterion_scores=sample_criteria,
            strengths=[],
            improvements=[],
        )
        crit = result.get_criterion_by_id("short_desc")
        assert crit is not None
        assert crit.points_awarded == 8

        missing = result.get_criterion_by_id("nonexistent")
        assert missing is None


class TestBatchEvaluationSummary:
    """Tests for BatchEvaluationSummary model."""

    def test_pass_rate_calculation(self):
        """Pass rate should be calculated correctly."""
        summary = BatchEvaluationSummary(
            total_tickets=100,
            passed_count=85,
            failed_count=15,
            average_score=62.5,
            average_percentage=89.3,
        )
        assert summary.pass_rate == 85.0

    def test_pass_rate_zero_tickets(self):
        """Pass rate should be 0 when no tickets."""
        summary = BatchEvaluationSummary(
            total_tickets=0,
            passed_count=0,
            failed_count=0,
            average_score=0,
            average_percentage=0,
        )
        assert summary.pass_rate == 0.0


class TestScoringRubrics:
    """Tests for scoring rubric loading and models."""

    def test_load_all_rubrics(self, rubrics_path: Path):
        """Should load all three rubrics."""
        rubrics = load_rubrics(rubrics_path)
        assert len(rubrics) == 3
        assert TemplateType.INCIDENT_LOGGING in rubrics
        assert TemplateType.INCIDENT_HANDLING in rubrics
        assert TemplateType.CUSTOMER_SERVICE in rubrics

    def test_rubric_has_criteria(self, incident_logging_rubric: ScoringRubric):
        """Each rubric should have multiple criteria."""
        assert len(incident_logging_rubric.criteria) > 0
        assert len(incident_logging_rubric.criteria) >= 5

    def test_rubric_template_name(self, incident_logging_rubric: ScoringRubric):
        """Rubric should have correct template name."""
        assert incident_logging_rubric.template_name == "Incident Logging"
        assert incident_logging_rubric.template == TemplateType.INCIDENT_LOGGING

    def test_criterion_has_options(self, incident_logging_rubric: ScoringRubric):
        """Each criterion should have scoring options."""
        for criterion in incident_logging_rubric.criteria:
            assert len(criterion.options) > 0

    def test_criterion_max_points(self, incident_logging_rubric: ScoringRubric):
        """Criteria should have valid max points."""
        scoring_criteria = incident_logging_rubric.scoring_criteria
        for criterion in scoring_criteria:
            assert criterion.max_points >= 0

    def test_get_criterion_by_id(self, incident_logging_rubric: ScoringRubric):
        """Should retrieve criterion by ID."""
        crit = incident_logging_rubric.get_criterion("correct_category")
        assert crit is not None
        assert "category" in crit.name.lower()

    def test_get_criterion_by_name(self, incident_logging_rubric: ScoringRubric):
        """Should retrieve criterion by name."""
        crit = incident_logging_rubric.get_criterion_by_name("Short Description")
        assert crit is not None
        assert "short" in crit.name.lower()

    def test_deduction_criteria_identified(self, incident_logging_rubric: ScoringRubric):
        """Deduction criteria should be identified correctly."""
        deduction_criteria = incident_logging_rubric.deduction_criteria
        assert len(deduction_criteria) >= 2

        # Should include validation and critical process
        names = [c.name.lower() for c in deduction_criteria]
        assert any("validation" in n for n in names)
        assert any("critical" in n for n in names)

    def test_scoring_criteria_excludes_deductions(self, incident_logging_rubric: ScoringRubric):
        """Scoring criteria should exclude deduction criteria."""
        scoring = incident_logging_rubric.scoring_criteria
        deduction = incident_logging_rubric.deduction_criteria

        scoring_ids = {c.id for c in scoring}
        deduction_ids = {c.id for c in deduction}

        # No overlap
        assert scoring_ids.isdisjoint(deduction_ids)

    def test_calculated_max_points(self, incident_logging_rubric: ScoringRubric):
        """Calculated max should sum scoring criteria."""
        scoring = incident_logging_rubric.scoring_criteria
        expected = sum(c.max_points for c in scoring)
        assert incident_logging_rubric.calculated_max_points == expected

    def test_evaluation_type_assigned(self, incident_logging_rubric: ScoringRubric):
        """Criteria should have evaluation type assigned."""
        for criterion in incident_logging_rubric.criteria:
            assert criterion.evaluation_type in ["rules", "llm"]

    def test_category_assigned(self, incident_logging_rubric: ScoringRubric):
        """Criteria should have category assigned."""
        for criterion in incident_logging_rubric.criteria:
            assert criterion.category is not None


class TestTemplateType:
    """Tests for TemplateType enum."""

    def test_all_templates(self):
        """Should have all three template types."""
        assert len(TemplateType) == 3

    def test_template_values(self):
        """Template values should be snake_case."""
        assert TemplateType.INCIDENT_LOGGING.value == "incident_logging"
        assert TemplateType.INCIDENT_HANDLING.value == "incident_handling"
        assert TemplateType.CUSTOMER_SERVICE.value == "customer_service"


class TestModelValidation:
    """Tests for Pydantic model validation."""

    def test_evaluation_result_score_bounds(self):
        """Total score should be bounded 0-70."""
        with pytest.raises(ValidationError):
            EvaluationResult(
                ticket_number="INC123",
                template=TemplateType.INCIDENT_LOGGING,
                total_score=71,  # Over max
                criterion_scores=[],
                strengths=[],
                improvements=[],
            )

        with pytest.raises(ValidationError):
            EvaluationResult(
                ticket_number="INC123",
                template=TemplateType.INCIDENT_LOGGING,
                total_score=-1,  # Under min
                criterion_scores=[],
                strengths=[],
                improvements=[],
            )

    def test_criterion_score_requires_fields(self):
        """CriterionScore should require all fields."""
        with pytest.raises(ValidationError):
            CriterionScore(
                criterion_id="test",
                # Missing other required fields
            )
