"""Ticket Evaluator - Main orchestrator for onsite support ticket evaluation."""

import logging
import time
from datetime import datetime

from tqrs.llm.client import OpenAIClient
from tqrs.llm.evaluator import LLMEvaluator
from tqrs.models.evaluation import EvaluationResult, TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult
from tqrs.rules.evaluator import RulesEvaluator
from tqrs.scoring.calculator import ScoringCalculator
from tqrs.scoring.formatter import ResultFormatter

logger = logging.getLogger(__name__)


class TicketEvaluator:
    """Main orchestrator for onsite support ticket evaluation.

    Combines rules engine (Opened For) and LLM evaluation (7 criteria)
    to produce 90-point scores.
    """

    def __init__(
        self,
        rules_evaluator: RulesEvaluator | None = None,
        llm_evaluator: LLMEvaluator | None = None,
        calculator: ScoringCalculator | None = None,
        formatter: ResultFormatter | None = None,
    ):
        self.rules_evaluator = rules_evaluator or RulesEvaluator()
        self.llm_evaluator = llm_evaluator
        self.calculator = calculator or ScoringCalculator()
        self.formatter = formatter or ResultFormatter()

    @classmethod
    def create(
        cls,
        api_key: str,
        base_url: str | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        timeout: int = 30,
        max_retries: int = 3,
        use_azure: bool = False,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        azure_api_version: str = "2023-05-15",
    ) -> "TicketEvaluator":
        """Create a fully configured ticket evaluator."""
        client = OpenAIClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            use_azure=use_azure,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            azure_api_version=azure_api_version,
        )
        llm_evaluator = LLMEvaluator(client)
        return cls(llm_evaluator=llm_evaluator)

    def evaluate_ticket(self, ticket: ServiceNowTicket) -> EvaluationResult:
        """Run complete evaluation on a ticket.

        Pipeline:
        1. Run rules evaluation (Opened For)
        2. Run LLM evaluation (7 criteria)
        3. Combine results
        4. Calculate score (sum, no deductions)
        5. Assign performance band
        6. Build EvaluationResult
        """
        start_time = time.time()

        # Step 1: Run rules evaluation
        logger.debug(f"Running rules evaluation for {ticket.number}")
        rule_results = self.rules_evaluator.evaluate(ticket)

        # Step 2: Run LLM evaluation (if available)
        llm_results: list[RuleResult] = []
        if self.llm_evaluator:
            logger.debug(f"Running LLM evaluation for {ticket.number}")
            llm_results = self.llm_evaluator.evaluate_ticket(ticket)
        else:
            logger.warning(
                f"No LLM evaluator configured for {ticket.number}, using rules only"
            )

        # Step 3: Calculate score
        scoring_result = self.calculator.calculate_score(rule_results, llm_results)

        # Step 4: Format results
        criterion_scores = self.formatter.to_criterion_scores(rule_results, llm_results)

        # Step 5: Collect strengths and improvements
        all_results = rule_results + llm_results
        strengths = self.formatter.collect_strengths(all_results)
        improvements = self.formatter.collect_improvements(all_results)

        evaluation_time = time.time() - start_time

        # Step 6: Build final result
        return EvaluationResult(
            ticket_number=ticket.number,
            template=TemplateType.ONSITE_REVIEW,
            total_score=scoring_result.total_score,
            max_score=scoring_result.max_score,
            criterion_scores=criterion_scores,
            strengths=strengths,
            improvements=improvements,
            evaluated_at=datetime.now(),
            evaluation_time_seconds=evaluation_time,
        )

    def evaluate_rules_only(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Run only rules evaluation (no LLM)."""
        return self.rules_evaluator.evaluate(ticket)

    def evaluate_llm_only(self, ticket: ServiceNowTicket) -> list[RuleResult]:
        """Run only LLM evaluation (no rules)."""
        if not self.llm_evaluator:
            raise ValueError("No LLM evaluator configured")
        return self.llm_evaluator.evaluate_ticket(ticket)

    def get_raw_results(
        self, ticket: ServiceNowTicket
    ) -> tuple[list[RuleResult], list[RuleResult]]:
        """Get raw rule and LLM results without scoring."""
        rule_results = self.rules_evaluator.evaluate(ticket)
        llm_results: list[RuleResult] = []
        if self.llm_evaluator:
            llm_results = self.llm_evaluator.evaluate_ticket(ticket)
        return rule_results, llm_results

    def get_coaching_recommendations(self, ticket: ServiceNowTicket) -> list[str]:
        """Get coaching recommendations for a ticket."""
        rule_results, llm_results = self.get_raw_results(ticket)
        all_results = rule_results + llm_results
        return self.formatter.get_coaching_recommendations(all_results)
