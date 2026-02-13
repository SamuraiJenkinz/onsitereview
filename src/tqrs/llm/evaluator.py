"""LLM Evaluator orchestrator for onsite support ticket quality assessment."""

import logging
from typing import Any

from pydantic import ValidationError

from tqrs.llm.client import OpenAIClient
from tqrs.llm.prompts import (
    RESPONSE_SCHEMA,
    FieldCorrectnessPrompt,
    IncidentHandlingPrompt,
    IncidentNotesPrompt,
    ResolutionNotesPrompt,
)
from tqrs.llm.schemas import (
    FieldCorrectnessEvaluation,
    IncidentHandlingEvaluation,
    IncidentNotesEvaluation,
    ResolutionNotesEvaluation,
)
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """Orchestrates LLM-based ticket evaluation for onsite support review."""

    def __init__(self, client: OpenAIClient):
        self.client = client

    def evaluate_ticket(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Run all LLM evaluations for a ticket.

        Makes 4 LLM API calls and returns 7 RuleResult objects:
        - Field correctness (1 call -> 4 results)
        - Incident notes (1 call -> 1 result)
        - Incident handling (1 call -> 1 result)
        - Resolution notes (1 call -> 1 result)
        """
        results: list[RuleResult] = []

        eval_methods = [
            ("field_correctness", self.evaluate_field_correctness),
            ("incident_notes", self.evaluate_incident_notes),
            ("incident_handling", self.evaluate_incident_handling),
            ("resolution_notes", self.evaluate_resolution_notes),
        ]

        for eval_type, method in eval_methods:
            try:
                method_results = method(ticket)
                if isinstance(method_results, list):
                    results.extend(method_results)
                else:
                    results.append(method_results)
            except Exception as e:
                logger.error(f"Error in {eval_type} evaluation for {ticket.number}: {e}")
                results.extend(self._create_error_results(eval_type, str(e)))

        return results

    def evaluate_field_correctness(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Evaluate field correctness for criteria 1-4 (25 pts total).

        Single LLM call returns 4 RuleResults:
        - correct_category (5 pts)
        - correct_subcategory (5 pts)
        - correct_service (5 pts)
        - correct_ci (10 pts)
        """
        messages = FieldCorrectnessPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = FieldCorrectnessEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing field correctness response: {e}")
            eval_result = self._parse_field_correctness(response)

        return [
            RuleResult(
                criterion_id="correct_category",
                passed=eval_result.category_score == 5,
                score=eval_result.category_score,
                max_score=5,
                evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
                reasoning=eval_result.category_reasoning,
                coaching=eval_result.coaching if eval_result.coaching else None,
            ),
            RuleResult(
                criterion_id="correct_subcategory",
                passed=eval_result.subcategory_score == 5,
                score=eval_result.subcategory_score,
                max_score=5,
                evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
                reasoning=eval_result.subcategory_reasoning,
                coaching=eval_result.coaching if eval_result.coaching else None,
            ),
            RuleResult(
                criterion_id="correct_service",
                passed=eval_result.service_score == 5,
                score=eval_result.service_score,
                max_score=5,
                evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
                reasoning=eval_result.service_reasoning,
                coaching=eval_result.coaching if eval_result.coaching else None,
            ),
            RuleResult(
                criterion_id="correct_ci",
                passed=eval_result.ci_score == 10,
                score=eval_result.ci_score,
                max_score=10,
                evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
                reasoning=eval_result.ci_reasoning,
                coaching=eval_result.coaching if eval_result.coaching else None,
            ),
        ]

    def evaluate_incident_notes(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate incident notes quality (20 pts)."""
        messages = IncidentNotesPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = IncidentNotesEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing incident notes response: {e}")
            eval_result = self._parse_criterion_response(response, IncidentNotesEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_incident_handling(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate incident handling (15 pts)."""
        messages = IncidentHandlingPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = IncidentHandlingEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing incident handling response: {e}")
            eval_result = self._parse_criterion_response(response, IncidentHandlingEvaluation)

        return self._to_rule_result(eval_result)

    def evaluate_resolution_notes(self, ticket: ServiceNowTicket) -> RuleResult:
        """Evaluate resolution notes quality (20 pts)."""
        messages = ResolutionNotesPrompt.build_messages(ticket)
        response = self.client.complete(messages, RESPONSE_SCHEMA)

        try:
            eval_result = ResolutionNotesEvaluation.model_validate(response)
        except ValidationError as e:
            logger.warning(f"Validation error parsing resolution notes response: {e}")
            eval_result = self._parse_criterion_response(response, ResolutionNotesEvaluation)

        return self._to_rule_result(eval_result)

    def _to_rule_result(self, eval_result: Any) -> RuleResult:
        """Convert a CriterionEvaluation to RuleResult format."""
        return RuleResult(
            criterion_id=eval_result.criterion_id,
            passed=eval_result.score == eval_result.max_score,
            score=eval_result.score,
            max_score=eval_result.max_score,
            evidence="; ".join(eval_result.evidence) if eval_result.evidence else "",
            reasoning=eval_result.reasoning,
            coaching=eval_result.coaching if eval_result.coaching else None,
        )

    def _parse_field_correctness(self, response: dict) -> FieldCorrectnessEvaluation:
        """Parse a partial field correctness response with defaults."""
        defaults = {
            "category_score": response.get("category_score", 0),
            "category_reasoning": response.get("category_reasoning", "Unable to parse response"),
            "subcategory_score": response.get("subcategory_score", 0),
            "subcategory_reasoning": response.get("subcategory_reasoning", "Unable to parse response"),
            "service_score": response.get("service_score", 0),
            "service_reasoning": response.get("service_reasoning", "Unable to parse response"),
            "ci_score": response.get("ci_score", 0),
            "ci_reasoning": response.get("ci_reasoning", "Unable to parse response"),
            "evidence": response.get("evidence", []),
            "coaching": response.get("coaching", ""),
        }
        merged = {**defaults, **response}
        return FieldCorrectnessEvaluation.model_validate(merged)

    def _parse_criterion_response(self, response: dict, model_class: type) -> Any:
        """Parse a partial criterion response with defaults."""
        defaults = {
            "criterion_id": response.get("criterion_id", "unknown"),
            "score": response.get("score", 0),
            "max_score": response.get("max_score", 0),
            "evidence": response.get("evidence", []),
            "reasoning": response.get("reasoning", "Unable to fully parse response"),
            "coaching": response.get("coaching", ""),
        }

        if model_class == IncidentNotesEvaluation:
            defaults.update({
                "location_documented": response.get("location_documented", False),
                "contact_info_present": response.get("contact_info_present", False),
                "relevant_details_present": response.get("relevant_details_present", False),
                "troubleshooting_documented": response.get("troubleshooting_documented", False),
                "appropriate_field_usage": response.get("appropriate_field_usage", False),
            })
        elif model_class == IncidentHandlingEvaluation:
            defaults.update({
                "routed_correctly": response.get("routed_correctly", False),
                "resolved_appropriately": response.get("resolved_appropriately", False),
                "fcr_opportunity_missed": response.get("fcr_opportunity_missed", False),
            })
        elif model_class == ResolutionNotesEvaluation:
            defaults.update({
                "summary_present": response.get("summary_present", False),
                "confirmation_present": response.get("confirmation_present", False),
                "is_wip_or_routed": response.get("is_wip_or_routed", False),
            })

        merged = {**defaults, **response}
        return model_class.model_validate(merged)

    def _create_error_results(self, eval_type: str, error_msg: str) -> list[RuleResult]:
        """Create zero-score results for evaluation errors."""
        if eval_type == "field_correctness":
            return [
                RuleResult(
                    criterion_id="correct_category",
                    passed=False, score=0, max_score=5,
                    evidence="", reasoning=f"Evaluation failed: {error_msg}",
                    coaching="Unable to evaluate due to error. Please review manually.",
                ),
                RuleResult(
                    criterion_id="correct_subcategory",
                    passed=False, score=0, max_score=5,
                    evidence="", reasoning=f"Evaluation failed: {error_msg}",
                    coaching="Unable to evaluate due to error. Please review manually.",
                ),
                RuleResult(
                    criterion_id="correct_service",
                    passed=False, score=0, max_score=5,
                    evidence="", reasoning=f"Evaluation failed: {error_msg}",
                    coaching="Unable to evaluate due to error. Please review manually.",
                ),
                RuleResult(
                    criterion_id="correct_ci",
                    passed=False, score=0, max_score=10,
                    evidence="", reasoning=f"Evaluation failed: {error_msg}",
                    coaching="Unable to evaluate due to error. Please review manually.",
                ),
            ]

        criterion_map = {
            "incident_notes": ("incident_notes", 20),
            "incident_handling": ("incident_handling", 15),
            "resolution_notes": ("resolution_notes", 20),
        }
        criterion_id, max_score = criterion_map.get(eval_type, ("unknown", 0))

        return [RuleResult(
            criterion_id=criterion_id,
            passed=False, score=0, max_score=max_score,
            evidence="", reasoning=f"Evaluation failed: {error_msg}",
            coaching="Unable to evaluate due to error. Please review manually.",
        )]
