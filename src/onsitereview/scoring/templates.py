"""Template criterion mappings for onsitereview scoring - Onsite Support Review."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class TemplateCriterion:
    """Definition of a scoring criterion within the onsite support template."""

    criterion_id: str
    criterion_name: str
    max_points: int
    source: Literal["rules", "llm"]
    required: bool = True


# Onsite Support Review Criteria (90 points total, 8 criteria)
ONSITE_REVIEW_CRITERIA: list[TemplateCriterion] = [
    TemplateCriterion(
        criterion_id="correct_category",
        criterion_name="Category",
        max_points=5,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="correct_subcategory",
        criterion_name="Subcategory",
        max_points=5,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="correct_service",
        criterion_name="Service",
        max_points=5,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="correct_ci",
        criterion_name="Configuration Item",
        max_points=10,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="opened_for_correct",
        criterion_name="Opened For",
        max_points=10,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="incident_notes",
        criterion_name="Incident Notes",
        max_points=20,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="incident_handling",
        criterion_name="Incident Handling",
        max_points=15,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="resolution_notes",
        criterion_name="Resolution Notes",
        max_points=20,
        source="llm",
    ),
]

# Criterion lookup by ID
_CRITERIA_BY_ID: dict[str, TemplateCriterion] = {
    c.criterion_id: c for c in ONSITE_REVIEW_CRITERIA
}


def get_max_score() -> int:
    """Get maximum possible score (90 points)."""
    return sum(c.max_points for c in ONSITE_REVIEW_CRITERIA)


def get_criteria() -> list[TemplateCriterion]:
    """Get all criteria for the onsite support review."""
    return ONSITE_REVIEW_CRITERIA


def get_criterion_by_id(criterion_id: str) -> TemplateCriterion | None:
    """Look up a specific criterion by ID."""
    return _CRITERIA_BY_ID.get(criterion_id)
