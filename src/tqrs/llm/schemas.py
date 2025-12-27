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
    strengths: list[str] = Field(default_factory=list, description="What was done well")
    improvements: list[str] = Field(default_factory=list, description="Areas to improve")
    coaching: str = Field("", description="Specific coaching recommendation")


class DescriptionEvaluation(CriterionEvaluation):
    """Evaluation for issue/request description quality (20 pts)."""

    completeness_score: int = Field(
        ..., ge=0, le=10, description="How complete is the description (0-10)"
    )
    clarity_score: int = Field(
        ..., ge=0, le=10, description="How clear is the description (0-10)"
    )
    issue_stated: bool = Field(..., description="Is the issue/request clearly stated")
    context_provided: bool = Field(..., description="Is relevant context provided")
    user_impact_noted: bool = Field(..., description="Is user impact mentioned")


class TroubleshootingEvaluation(CriterionEvaluation):
    """Evaluation for troubleshooting quality (20 pts)."""

    steps_documented: bool = Field(..., description="Are troubleshooting steps documented")
    logical_progression: bool = Field(
        ..., description="Do steps follow logical sequence"
    )
    appropriate_actions: bool = Field(
        ..., description="Were appropriate actions taken for the issue"
    )
    outcome_documented: bool = Field(
        ..., description="Is the outcome of each step documented"
    )
    steps_count: int = Field(ge=0, description="Number of documented troubleshooting steps")


class ResolutionEvaluation(CriterionEvaluation):
    """Evaluation for resolution notes quality (15 pts)."""

    outcome_clear: bool = Field(..., description="Is the resolution outcome clear")
    steps_documented: bool = Field(..., description="Are resolution steps documented")
    confirmation_obtained: bool = Field(
        ..., description="Was user confirmation obtained"
    )
    resolution_complete: bool = Field(..., description="Does resolution address the issue")


class CustomerServiceEvaluation(CriterionEvaluation):
    """Evaluation for customer service quality (20 pts)."""

    professional_tone: bool = Field(..., description="Is tone professional throughout")
    empathy_shown: bool = Field(..., description="Is empathy demonstrated")
    clear_communication: bool = Field(..., description="Is communication clear")
    proper_greeting: bool = Field(..., description="Was proper greeting used")
    proper_closing: bool = Field(..., description="Was proper closing used")
    expectations_set: bool = Field(
        ..., description="Were expectations clearly communicated"
    )


class SpellingGrammarEvaluation(CriterionEvaluation):
    """Evaluation for spelling and grammar (2 pts)."""

    errors_found: list[str] = Field(
        default_factory=list, description="List of spelling/grammar errors found"
    )
    error_count: int = Field(ge=0, description="Total number of errors")
    severity: str = Field(..., description="Error severity: none, minor, moderate, significant")


class LLMEvaluationResponse(BaseModel):
    """Complete LLM evaluation response for a ticket."""

    ticket_number: str = Field(..., description="Ticket number being evaluated")
    template_type: str = Field(..., description="Template type used for evaluation")
    description_eval: DescriptionEvaluation | None = Field(
        None, description="Description evaluation result"
    )
    troubleshooting_eval: TroubleshootingEvaluation | None = Field(
        None, description="Troubleshooting evaluation result"
    )
    resolution_eval: ResolutionEvaluation | None = Field(
        None, description="Resolution evaluation result"
    )
    customer_service_eval: CustomerServiceEvaluation | None = Field(
        None, description="Customer service evaluation result"
    )
    spelling_grammar_eval: SpellingGrammarEvaluation | None = Field(
        None, description="Spelling/grammar evaluation result"
    )
    overall_assessment: str = Field(..., description="Overall quality assessment")
    total_llm_score: int = Field(ge=0, description="Total LLM score awarded")
    max_llm_score: int = Field(gt=0, description="Maximum possible LLM score")

    @property
    def llm_percentage(self) -> float:
        """Calculate LLM score as percentage."""
        return (self.total_llm_score / self.max_llm_score) * 100 if self.max_llm_score else 0

    def get_all_coaching(self) -> list[str]:
        """Collect all coaching recommendations."""
        coaching = []
        for eval_field in [
            self.description_eval,
            self.troubleshooting_eval,
            self.resolution_eval,
            self.customer_service_eval,
            self.spelling_grammar_eval,
        ]:
            if eval_field and eval_field.coaching:
                coaching.append(eval_field.coaching)
        return coaching

    def get_all_improvements(self) -> list[str]:
        """Collect all improvement suggestions."""
        improvements = []
        for eval_field in [
            self.description_eval,
            self.troubleshooting_eval,
            self.resolution_eval,
            self.customer_service_eval,
            self.spelling_grammar_eval,
        ]:
            if eval_field:
                improvements.extend(eval_field.improvements)
        return improvements
