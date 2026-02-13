"""Pydantic models for LLM evaluation responses."""

from pydantic import BaseModel, Field


class CriterionEvaluation(BaseModel):
    """Base evaluation result for a single criterion."""

    criterion_id: str = Field(..., description="Unique criterion identifier")
    score: int = Field(..., ge=0, description="Points awarded")
    max_score: int = Field(..., gt=0, description="Maximum possible points")
    evidence: list[str] = Field(
        default_factory=list, description="Quotes from ticket supporting evaluation"
    )
    reasoning: str = Field(..., description="Explanation of score")
    coaching: str = Field("", description="Specific coaching recommendation")


class FieldCorrectnessEvaluation(BaseModel):
    """Evaluation for field correctness criteria 1-4 (combined in single LLM call).

    Category (5pts), Subcategory (5pts), Service (5pts), Configuration Item (10pts).
    """

    # Category (5 or 0)
    category_score: int = Field(..., description="5=correct, 0=incorrect")
    category_reasoning: str = Field(..., description="Why category is/isn't correct")

    # Subcategory (5 or 0)
    subcategory_score: int = Field(..., description="5=correct, 0=incorrect")
    subcategory_reasoning: str = Field(..., description="Why subcategory is/isn't correct")

    # Service (5, 2, or 0)
    service_score: int = Field(..., description="5=correct, 2=better available, 0=incorrect/none")
    service_reasoning: str = Field(..., description="Why service score was given")

    # Configuration Item (10, 5, or 0)
    ci_score: int = Field(..., description="10=correct, 5=better available, 0=incorrect/none")
    ci_reasoning: str = Field(..., description="Why CI score was given")

    # Shared
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence")
    coaching: str = Field("", description="Overall coaching for field correctness")


class IncidentNotesEvaluation(CriterionEvaluation):
    """Evaluation for incident notes quality (20 pts).

    Meets(20) / Partially(10) / N/A(20) / Does Not Meet(0).
    """

    location_documented: bool = Field(..., description="User location is documented")
    contact_info_present: bool = Field(..., description="Contact info is present")
    relevant_details_present: bool = Field(..., description="Relevant issue details documented")
    troubleshooting_documented: bool = Field(
        ..., description="Troubleshooting steps documented where applicable"
    )
    appropriate_field_usage: bool = Field(
        ..., description="Info in appropriate fields (description vs work notes)"
    )


class IncidentHandlingEvaluation(CriterionEvaluation):
    """Evaluation for incident handling (15 pts).

    Correct(15) / N/A(15) / Incorrect(0).
    """

    routed_correctly: bool = Field(..., description="Ticket routed to correct team")
    resolved_appropriately: bool = Field(..., description="Resolution approach was appropriate")
    fcr_opportunity_missed: bool = Field(
        False, description="First contact resolution opportunity was missed"
    )


class ResolutionNotesEvaluation(CriterionEvaluation):
    """Evaluation for resolution notes quality (20 pts).

    Meets(20) / Partially(10) / N/A(20) / Does Not Meet(0).
    """

    summary_present: bool = Field(..., description="Resolution summary is documented")
    confirmation_present: bool = Field(..., description="User confirmation is documented")
    is_wip_or_routed: bool = Field(
        False, description="Ticket is WIP or routed to another team"
    )
