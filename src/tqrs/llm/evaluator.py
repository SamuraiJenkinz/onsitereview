"""LLM Evaluator orchestrator for ticket quality assessment."""

import logging
from typing import Any

from pydantic import ValidationError

from tqrs.llm.client import OpenAIClient
from tqrs.llm.prompts import (
    RESPONSE_SCHEMA,
    CustomerServicePrompt,
    DescriptionPrompt,
    ResolutionPrompt,
    SpellingGrammarPrompt,
    TroubleshootingPrompt,
)
from tqrs.llm.schemas import (
    CustomerServiceEvaluation,
    DescriptionEvaluation,
    LLMEvaluationResponse,
    ResolutionEvaluation,
    SpellingGrammarEvaluation,
    TroubleshootingEvaluation,
)
from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """Orchestrates LLM-based ticket evaluation."""

    # Map template types to which evaluations to run
    TEMPLATE_EVALUATIONS: dict[TemplateType, list[str]] = {
        TemplateType.INCIDENT_LOGGING: ["description", "spelling_grammar"],
        TemplateType.INCIDENT_HANDLING: [
            "description",
            "troubleshooting",
            "resolution",
            "spelling_grammar",
        ],
        TemplateType.CUSTOMER_SERVICE: [
            "description",
            "troubleshooting",
            "customer_service",
            "spelling_grammar",
        ],
    }

    def __init__(self, client: OpenAIClient):
        """Initialize the LLM evaluator.

        Args:
            client: Configured OpenAI client
        """
        self.client = client

    def evaluate_ticket(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> list[RuleResult]:
        """Run all LLM evaluations for a ticket based on template.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type determining which evaluations to run

        Returns:
            List of RuleResult objects from LLM evaluations
        """
        results: list[RuleResult] = []
        evaluations = self.TEMPLATE_EVALUATIONS.get(template, [])

        for eval_type in evaluations:
            try:
                if eval_type == "description":
                    results.append(self.evaluate_description(ticket))
                elif eval_type == "troubleshooting":
                    results.append(self.evaluate_troubleshooting(ticket))
                elif eval_type == "resolution":
                    results.append(self.evaluate_resolution(ticket))
                elif eval_type == "customer_service":
                    results.append(self.evaluate_customer_service(ticket))
                elif eval_type == "spelling_grammar":
                    results.append(self.evaluate_spelling_grammar(ticket))
            except Exception as e:
                logger.error(f"Error in {eval_type} evaluation for {ticket.number}: {e}")
                # Return a zero-score result on error
                results.append(self._create_error_result(eval_type, str(e)))

        return results

    def evaluate_description(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate description quality (20 pts).

        Args:
            ticket: ServiceNow ticket to evaluate

        Returns:
            RuleResult with description evaluation
        """
        messages = DescriptionPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = DescriptionEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing description response: {e}")
            eval_result = self._parse_partial_response(response, DescriptionEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_troubleshooting(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate troubleshooting quality (20 pts).

        Args:
            ticket: ServiceNow ticket to evaluate

        Returns:
            RuleResult with troubleshooting evaluation
        """
        messages = TroubleshootingPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = TroubleshootingEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing troubleshooting response: {e}")
            eval_result = self._parse_partial_response(response, TroubleshootingEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_resolution(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate resolution notes quality (15 pts).

        Args:
            ticket: ServiceNow ticket to evaluate

        Returns:
            RuleResult with resolution evaluation
        """
        messages = ResolutionPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = ResolutionEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing resolution response: {e}")
            eval_result = self._parse_partial_response(response, ResolutionEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_customer_service(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate customer service quality (20 pts).

        Args:
            ticket: ServiceNow ticket to evaluate

        Returns:
            RuleResult with customer service evaluation
        """
        messages = CustomerServicePrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = CustomerServiceEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing customer service response: {e}")
            eval_result = self._parse_partial_response(response, CustomerServiceEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_spelling_grammar(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate spelling and grammar (2 pts).

        Args:
            ticket: ServiceNow ticket to evaluate

        Returns:
            RuleResult with spelling/grammar evaluation
        """
        messages = SpellingGrammarPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = SpellingGrammarEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing spelling/grammar response: {e}")
            eval_result = self._parse_partial_response(response, SpellingGrammarEvaluation)

        return self._to_rule_result(eval_result)

    def get_full_evaluation(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> LLMEvaluationResponse:
        """Get complete LLM evaluation with all details.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            Complete LLM evaluation response with all criteria
        """
        evaluations = self.TEMPLATE_EVALUATIONS.get(template, [])

        description_eval = None
        troubleshooting_eval = None
        resolution_eval = None
        customer_service_eval = None
        spelling_eval = None
        total_score = 0
        max_score = 0

        for eval_type in evaluations:
            if eval_type == "description":
                messages = DescriptionPrompt.build_messages(ticket)
                response = self.client.complete(messages, RESPONSE_SCHEMA)
                description_eval = self._safe_parse(response, DescriptionEvaluation)
                if description_eval:
                    total_score += description_eval.score
                    max_score += description_eval.max_score

            elif eval_type == "troubleshooting":
                messages = TroubleshootingPrompt.build_messages(ticket)
                response = self.client.complete(messages, RESPONSE_SCHEMA)
                troubleshooting_eval = self._safe_parse(response, TroubleshootingEvaluation)
                if troubleshooting_eval:
                    if isinstance(troubleshooting_eval.score, int):
                        total_score += troubleshooting_eval.score
                        max_score += troubleshooting_eval.max_score

            elif eval_type == "resolution":
                messages = ResolutionPrompt.build_messages(ticket)
                response = self.client.complete(messages, RESPONSE_SCHEMA)
                resolution_eval = self._safe_parse(response, ResolutionEvaluation)
                if resolution_eval:
                    if isinstance(resolution_eval.score, int):
                        total_score += resolution_eval.score
                        max_score += resolution_eval.max_score

            elif eval_type == "customer_service":
                messages = CustomerServicePrompt.build_messages(ticket)
                response = self.client.complete(messages, RESPONSE_SCHEMA)
                customer_service_eval = self._safe_parse(response, CustomerServiceEvaluation)
                if customer_service_eval:
                    total_score += customer_service_eval.score
                    max_score += customer_service_eval.max_score

            elif eval_type == "spelling_grammar":
                messages = SpellingGrammarPrompt.build_messages(ticket)
                response = self.client.complete(messages, RESPONSE_SCHEMA)
                spelling_eval = self._safe_parse(response, SpellingGrammarEvaluation)
                if spelling_eval:
                    total_score += spelling_eval.score
                    max_score += spelling_eval.max_score

        return LLMEvaluationResponse(
            ticket_number=ticket.number,
            template_type=template.value,
            description_eval=description_eval,
            troubleshooting_eval=troubleshooting_eval,
            resolution_eval=resolution_eval,
            customer_service_eval=customer_service_eval,
            spelling_grammar_eval=spelling_eval,
            overall_assessment=self._generate_assessment(
                description_eval,
                troubleshooting_eval,
                resolution_eval,
                customer_service_eval,
                spelling_eval,
            ),
            total_llm_score=total_score,
            max_llm_score=max_score if max_score > 0 else 1,
        )

    def _to_rule_result(self, eval_result: Any) -> RuleResult:
        """Convert evaluation result to RuleResult format."""
        # Handle N/A scores
        score: int | str = eval_result.score
        if isinstance(score, str) and score.upper() == "N/A":
            score = "N/A"
        elif isinstance(score, str):
            try:
                score = int(score)
            except ValueError:
                score = 0

        return RuleResult(
            criterion_id=eval_result.criterion_id,
            passed=eval_result.score == eval_result.max_score if isinstance(eval_result.score, int) else True,
            score=score,
            max_score=eval_result.max_score,
            evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
            reasoning=eval_result.reasoning,
            coaching=eval_result.coaching if eval_result.coaching else None,
        )

    def _parse_partial_response(self, response: dict, model_class: type) -> Any:
        """Attempt to parse a partial response with defaults."""
        # Fill in required fields with defaults if missing
        defaults = {
            "criterion_id": response.get("criterion_id", "unknown"),
            "score": response.get("score", 0),
            "max_score": response.get("max_score", 0),
            "evidence": response.get("evidence", []),
            "reasoning": response.get("reasoning", "Unable to fully parse response"),
            "strengths": response.get("strengths", []),
            "improvements": response.get("improvements", []),
            "coaching": response.get("coaching", ""),
        }

        # Add model-specific defaults
        if model_class == DescriptionEvaluation:
            defaults.update({
                "completeness_score": response.get("completeness_score", 0),
                "clarity_score": response.get("clarity_score", 0),
                "issue_stated": response.get("issue_stated", False),
                "context_provided": response.get("context_provided", False),
                "user_impact_noted": response.get("user_impact_noted", False),
            })
        elif model_class == TroubleshootingEvaluation:
            defaults.update({
                "steps_documented": response.get("steps_documented", False),
                "logical_progression": response.get("logical_progression", False),
                "appropriate_actions": response.get("appropriate_actions", False),
                "outcome_documented": response.get("outcome_documented", False),
                "steps_count": response.get("steps_count", 0),
            })
        elif model_class == ResolutionEvaluation:
            defaults.update({
                "outcome_clear": response.get("outcome_clear", False),
                "steps_documented": response.get("steps_documented", False),
                "confirmation_obtained": response.get("confirmation_obtained", False),
                "resolution_complete": response.get("resolution_complete", False),
            })
        elif model_class == CustomerServiceEvaluation:
            defaults.update({
                "professional_tone": response.get("professional_tone", False),
                "empathy_shown": response.get("empathy_shown", False),
                "clear_communication": response.get("clear_communication", False),
                "proper_greeting": response.get("proper_greeting", False),
                "proper_closing": response.get("proper_closing", False),
                "expectations_set": response.get("expectations_set", False),
            })
        elif model_class == SpellingGrammarEvaluation:
            defaults.update({
                "errors_found": response.get("errors_found", []),
                "error_count": response.get("error_count", 0),
                "severity": response.get("severity", "unknown"),
            })

        # Merge response with defaults
        merged = {**defaults, **response}
        return model_class.model_validate(merged)

    def _safe_parse(self, response: dict, model_class: type) -> Any | None:
        """Safely parse response, returning None on failure."""
        try:
            return model_class.model_validate(response)
        except ValidationError:
            try:
                return self._parse_partial_response(response, model_class)
            except Exception as e:
                logger.error(f"Failed to parse response: {e}")
                return None

    def _create_error_result(self, eval_type: str, error_msg: str) -> RuleResult:
        """Create a zero-score result for evaluation errors."""
        criterion_map = {
            "description": ("accurate_description", 20),
            "troubleshooting": ("troubleshooting_quality", 20),
            "resolution": ("resolution_notes", 15),
            "customer_service": ("customer_service_quality", 20),
            "spelling_grammar": ("spelling_grammar", 2),
        }
        criterion_id, max_score = criterion_map.get(eval_type, ("unknown", 0))

        return RuleResult(
            criterion_id=criterion_id,
            passed=False,
            score=0,
            max_score=max_score,
            evidence="",
            reasoning=f"Evaluation failed: {error_msg}",
            coaching="Unable to evaluate due to error. Please review manually.",
        )

    def _generate_assessment(self, *evals: Any) -> str:
        """Generate overall assessment from evaluations."""
        total = 0
        max_total = 0

        for eval_result in evals:
            if eval_result and isinstance(eval_result.score, int):
                total += eval_result.score
                max_total += eval_result.max_score

        if max_total == 0:
            return "Unable to generate assessment."

        percentage = (total / max_total) * 100

        if percentage >= 95:
            return "Excellent ticket quality. All criteria met to a high standard."
        elif percentage >= 90:
            return "Good ticket quality. Minor improvements possible."
        elif percentage >= 75:
            return "Adequate ticket quality. Several areas need improvement."
        elif percentage >= 50:
            return "Below standard ticket quality. Significant improvements required."
        else:
            return "Poor ticket quality. Major issues need to be addressed."
