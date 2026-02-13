"""Evaluation result models for onsitereview."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class TemplateType(str, Enum):
    """Evaluation template types."""

    ONSITE_REVIEW = "onsite_review"


class PerformanceBand(str, Enum):
    """Performance band classification based on percentage score."""

    BLUE = "blue"  # >= 95%
    GREEN = "green"  # >= 90%
    YELLOW = "yellow"  # >= 75%
    RED = "red"  # >= 50%
    PURPLE = "purple"  # < 50%

    @classmethod
    def from_percentage(cls, percentage: float) -> "PerformanceBand":
        """Determine performance band from percentage score."""
        if percentage >= 95:
            return cls.BLUE
        if percentage >= 90:
            return cls.GREEN
        if percentage >= 75:
            return cls.YELLOW
        if percentage >= 50:
            return cls.RED
        return cls.PURPLE

    @property
    def display_name(self) -> str:
        """Human-readable band name."""
        return self.value.capitalize()

    @property
    def css_color(self) -> str:
        """CSS color for the band."""
        colors = {
            "blue": "#3B82F6",
            "green": "#22C55E",
            "yellow": "#EAB308",
            "red": "#EF4444",
            "purple": "#A855F7",
        }
        return colors[self.value]


class CriterionScore(BaseModel):
    """Individual criterion evaluation result."""

    criterion_id: str = Field(..., description="Unique criterion identifier")
    criterion_name: str = Field(..., description="Human-readable criterion name")
    max_points: int = Field(..., description="Maximum points available")
    points_awarded: int = Field(..., description="Points awarded for this criterion")
    evidence: str = Field(..., description="Quote or data supporting the score")
    reasoning: str = Field(..., description="Explanation of why this score was given")
    coaching: str | None = Field(None, description="Improvement suggestion if points lost")

    @computed_field
    @property
    def percentage(self) -> float:
        """Percentage of max points achieved."""
        if self.max_points == 0:
            return 100.0
        return round((self.points_awarded / self.max_points) * 100, 1)

    @property
    def is_perfect(self) -> bool:
        """Check if maximum points were awarded."""
        return self.points_awarded == self.max_points


class EvaluationResult(BaseModel):
    """Complete evaluation result for one ticket."""

    # Ticket reference
    ticket_number: str = Field(..., description="ServiceNow ticket number")
    template: TemplateType = Field(..., description="Template used for evaluation")

    # Score totals
    total_score: int = Field(..., ge=0, le=90, description="Total points earned (0-90)")
    max_score: int = Field(90, description="Maximum possible score")

    # Criterion breakdown
    criterion_scores: list[CriterionScore] = Field(
        ..., description="Individual criterion scores"
    )

    # Summary
    strengths: list[str] = Field(default_factory=list, description="Areas of strength")
    improvements: list[str] = Field(
        default_factory=list, description="Areas for improvement"
    )

    # Metadata
    evaluated_at: datetime = Field(
        default_factory=datetime.now, description="When evaluation was performed"
    )
    evaluation_time_seconds: float = Field(
        0.0, description="Time taken to evaluate in seconds"
    )

    @computed_field
    @property
    def percentage(self) -> float:
        """Calculate percentage score."""
        return round((self.total_score / self.max_score) * 100, 1)

    @computed_field
    @property
    def band(self) -> PerformanceBand:
        """Determine performance band from score."""
        return PerformanceBand.from_percentage(self.percentage)

    @computed_field
    @property
    def passed(self) -> bool:
        """Check if ticket passed (>= 90% = 81/90)."""
        return self.percentage >= 90.0

    @property
    def pass_threshold(self) -> int:
        """Minimum score to pass."""
        return 81  # 90% of 90

    @property
    def points_to_pass(self) -> int:
        """Points needed to reach passing threshold."""
        if self.passed:
            return 0
        return self.pass_threshold - self.total_score

    def get_criterion_by_id(self, criterion_id: str) -> CriterionScore | None:
        """Get a specific criterion score by ID."""
        return next(
            (c for c in self.criterion_scores if c.criterion_id == criterion_id),
            None,
        )


class BatchEvaluationSummary(BaseModel):
    """Summary statistics for a batch of evaluations."""

    total_tickets: int = Field(..., description="Number of tickets evaluated")
    passed_count: int = Field(..., description="Number of tickets that passed")
    failed_count: int = Field(..., description="Number of tickets that failed")

    average_score: float = Field(..., description="Average score across batch")
    average_percentage: float = Field(..., description="Average percentage across batch")

    band_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of tickets per band"
    )

    common_issues: list[str] = Field(
        default_factory=list, description="Most common areas for improvement"
    )

    evaluated_at: datetime = Field(
        default_factory=datetime.now, description="When batch was evaluated"
    )
    total_evaluation_time_seconds: float = Field(
        0.0, description="Total time for batch evaluation"
    )

    @computed_field
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tickets == 0:
            return 0.0
        return round((self.passed_count / self.total_tickets) * 100, 1)


class AnalystReview(BaseModel):
    """Aggregated review for a single analyst across multiple incidents."""

    analyst_id: str = Field(..., description="Analyst identifier")
    evaluations: list[EvaluationResult] = Field(
        ..., description="Up to 3 incident evaluations"
    )

    @computed_field
    @property
    def average_percentage(self) -> float:
        """Average percentage across all evaluated incidents."""
        if not self.evaluations:
            return 0.0
        return round(
            sum(e.percentage for e in self.evaluations) / len(self.evaluations), 1
        )

    @computed_field
    @property
    def band(self) -> PerformanceBand:
        """Performance band from average percentage."""
        return PerformanceBand.from_percentage(self.average_percentage)

    @computed_field
    @property
    def passed(self) -> bool:
        """Whether analyst passed (average >= 90%)."""
        return self.average_percentage >= 90.0
