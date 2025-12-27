"""Template criterion mappings for TQRS scoring."""

from dataclasses import dataclass
from typing import Literal

from tqrs.models.evaluation import TemplateType


@dataclass
class TemplateCriterion:
    """Definition of a scoring criterion within a template."""

    criterion_id: str
    criterion_name: str
    max_points: int
    source: Literal["rules", "llm", "both"]
    required: bool = True
    is_deduction: bool = False  # True for validation/critical process


# Incident Logging Template Criteria (70 points total)
INCIDENT_LOGGING_CRITERIA: list[TemplateCriterion] = [
    # Deduction criteria (not counted in base total)
    TemplateCriterion(
        criterion_id="critical_process_followed",
        criterion_name="Critical Process",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    TemplateCriterion(
        criterion_id="validation_performed",
        criterion_name="Validation",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    # Positive scoring criteria
    TemplateCriterion(
        criterion_id="correct_category",
        criterion_name="Category",
        max_points=10,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="correct_subcategory",
        criterion_name="Subcategory",
        max_points=10,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="correct_service",
        criterion_name="Service",
        max_points=10,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="correct_ci",
        criterion_name="Configuration Item",
        max_points=10,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="short_description_format",
        criterion_name="Short Description",
        max_points=8,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="accurate_description",
        criterion_name="Description",
        max_points=20,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="spelling_grammar",
        criterion_name="Spelling/Grammar",
        max_points=2,
        source="llm",
    ),
]

# Incident Handling Template Criteria (70 points total)
INCIDENT_HANDLING_CRITERIA: list[TemplateCriterion] = [
    # Deduction criteria
    TemplateCriterion(
        criterion_id="critical_process_followed",
        criterion_name="Critical Process",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    TemplateCriterion(
        criterion_id="validation_performed",
        criterion_name="Validation",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    # Positive scoring criteria
    TemplateCriterion(
        criterion_id="correct_priority",
        criterion_name="Priority",
        max_points=5,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="troubleshooting_quality",
        criterion_name="Troubleshooting",
        max_points=20,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="interaction_vs_incident",
        criterion_name="Interaction vs Incident",
        max_points=5,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="routing_resolving",
        criterion_name="Routing/Resolving",
        max_points=20,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="resolution_code",
        criterion_name="Resolution Code",
        max_points=5,
        source="rules",
    ),
    TemplateCriterion(
        criterion_id="resolution_notes",
        criterion_name="Resolution Notes",
        max_points=15,
        source="llm",
    ),
]

# Customer Service Template Criteria (70 points total)
CUSTOMER_SERVICE_CRITERIA: list[TemplateCriterion] = [
    # Deduction criteria
    TemplateCriterion(
        criterion_id="critical_process_followed",
        criterion_name="Critical Process",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    TemplateCriterion(
        criterion_id="validation_performed",
        criterion_name="Validation",
        max_points=0,
        source="rules",
        is_deduction=True,
    ),
    # Positive scoring criteria
    TemplateCriterion(
        criterion_id="greeting",
        criterion_name="Greeting",
        max_points=5,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="offer_work_around",
        criterion_name="Offer Work Around",
        max_points=10,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="necessary_troubleshooting",
        criterion_name="Necessary Troubleshooting",
        max_points=10,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="self_resolve_training",
        criterion_name="Self-Resolve Training",
        max_points=10,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="resolution_follow_through",
        criterion_name="Resolution Follow-through",
        max_points=10,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="closing_message",
        criterion_name="Closing Message",
        max_points=5,
        source="llm",
    ),
    TemplateCriterion(
        criterion_id="general_customer_service",
        criterion_name="General Customer Service",
        max_points=20,
        source="llm",
    ),
]


# Template to criteria mapping
TEMPLATE_CRITERIA: dict[TemplateType, list[TemplateCriterion]] = {
    TemplateType.INCIDENT_LOGGING: INCIDENT_LOGGING_CRITERIA,
    TemplateType.INCIDENT_HANDLING: INCIDENT_HANDLING_CRITERIA,
    TemplateType.CUSTOMER_SERVICE: CUSTOMER_SERVICE_CRITERIA,
}


def get_template_max_score(template: TemplateType) -> int:
    """Get maximum possible score for a template (always 70)."""
    criteria = TEMPLATE_CRITERIA[template]
    return sum(c.max_points for c in criteria if not c.is_deduction)


def get_template_criteria(template: TemplateType) -> list[TemplateCriterion]:
    """Get all criteria for a template."""
    return TEMPLATE_CRITERIA[template]


def get_scoring_criteria(template: TemplateType) -> list[TemplateCriterion]:
    """Get only positive scoring criteria (excludes deductions)."""
    return [c for c in TEMPLATE_CRITERIA[template] if not c.is_deduction]


def get_deduction_criteria(template: TemplateType) -> list[TemplateCriterion]:
    """Get only deduction criteria (validation, critical process)."""
    return [c for c in TEMPLATE_CRITERIA[template] if c.is_deduction]


def get_criterion_by_id(
    template: TemplateType, criterion_id: str
) -> TemplateCriterion | None:
    """Look up a specific criterion by ID."""
    for criterion in TEMPLATE_CRITERIA[template]:
        if criterion.criterion_id == criterion_id:
            return criterion
    return None
