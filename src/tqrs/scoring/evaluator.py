"""Ticket Evaluator - Main orchestrator for complete ticket evaluation."""

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
    """Main orchestrator for complete ticket evaluation.

    Combines rules engine and LLM evaluation to produce final scores.
    """

    def __init__(
        self,
        rules_evaluator: RulesEvaluator | None = None,
        llm_evaluator: LLMEvaluator | None = None,
        calculator: ScoringCalculator | None = None,
        formatter: ResultFormatter | None = None,
    ):
        """Initialize the ticket evaluator.

        Args:
            rules_evaluator: Rules engine evaluator (created if not provided)
            llm_evaluator: LLM evaluator (required for full evaluation)
            calculator: Scoring calculator (created if not provided)
            formatter: Result formatter (created if not provided)
        """
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
    ) -> "TicketEvaluator":
        """Create a fully configured ticket evaluator.

        Args:
            api_key: OpenAI API key
            base_url: Optional custom API base URL
            model: Model to use for LLM evaluation
            temperature: Temperature for LLM responses
            max_tokens: Maximum tokens per response
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts

        Returns:
            Configured TicketEvaluator instance
        """
        client = OpenAIClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
        llm_evaluator = LLMEvaluator(client)

        return cls(llm_evaluator=llm_evaluator)

    def evaluate_ticket(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> EvaluationResult:
        """Run complete evaluation on a ticket.

        Pipeline:
        1. Run rules evaluation
        2. Run LLM evaluation
        3. Combine results
        4. Calculate score with deductions
        5. Check auto-fail
        6. Assign performance band
        7. Build EvaluationResult

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            Complete EvaluationResult
        """
        start_time = time.time()

        # Step 1: Run rules evaluation
        logger.debug(f"Running rules evaluation for {ticket.number}")
        rule_results = self.rules_evaluator.evaluate(ticket, template)

        # Step 2: Run LLM evaluation (if available)
        llm_results: list[RuleResult] = []
        if self.llm_evaluator:
            logger.debug(f"Running LLM evaluation for {ticket.number}")
            llm_results = self.llm_evaluator.evaluate_ticket(ticket, template)
        else:
            logger.warning(
                f"No LLM evaluator configured for {ticket.number}, using rules only"
            )

        # Step 3: Calculate score
        logger.debug(f"Calculating score for {ticket.number}")
        scoring_result = self.calculator.calculate_score(
            rule_results, llm_results, template
        )

        # Step 4: Format results
        logger.debug(f"Formatting results for {ticket.number}")
        criterion_scores = self.formatter.to_criterion_scores(
            rule_results, llm_results, template
        )

        # Step 5: Collect strengths and improvements
        all_results = rule_results + llm_results
        strengths = self.formatter.collect_strengths(all_results, template)
        improvements = self.formatter.collect_improvements(all_results, template)

        # Calculate evaluation time
        evaluation_time = time.time() - start_time

        # Step 6: Build final result
        return EvaluationResult(
            ticket_number=ticket.number,
            template=template,
            total_score=scoring_result.final_score,
            max_score=scoring_result.max_score,
            criterion_scores=criterion_scores,
            validation_deduction=scoring_result.validation_deduction,
            critical_process_deduction=scoring_result.critical_process_deduction,
            auto_fail=scoring_result.auto_fail,
            auto_fail_reason=scoring_result.auto_fail_reason,
            strengths=strengths,
            improvements=improvements,
            evaluated_at=datetime.now(),
            evaluation_time_seconds=evaluation_time,
        )

    def evaluate_rules_only(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> list[RuleResult]:
        """Run only rules evaluation (no LLM).

        Useful for quick pre-checks or when LLM is unavailable.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            List of RuleResult from rules engine
        """
        return self.rules_evaluator.evaluate(ticket, template)

    def evaluate_llm_only(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> list[RuleResult]:
        """Run only LLM evaluation (no rules).

        Useful for testing LLM evaluations in isolation.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            List of RuleResult from LLM evaluator

        Raises:
            ValueError: If no LLM evaluator is configured
        """
        if not self.llm_evaluator:
            raise ValueError("No LLM evaluator configured")

        return self.llm_evaluator.evaluate_ticket(ticket, template)

    def get_raw_results(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> tuple[list[RuleResult], list[RuleResult]]:
        """Get raw rule and LLM results without scoring.

        Useful for debugging or custom scoring logic.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            Tuple of (rule_results, llm_results)
        """
        rule_results = self.rules_evaluator.evaluate(ticket, template)

        llm_results: list[RuleResult] = []
        if self.llm_evaluator:
            llm_results = self.llm_evaluator.evaluate_ticket(ticket, template)

        return rule_results, llm_results

    def get_coaching_recommendations(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> list[str]:
        """Get coaching recommendations for a ticket.

        Runs full evaluation and extracts coaching suggestions.

        Args:
            ticket: ServiceNow ticket to evaluate
            template: Template type for evaluation

        Returns:
            List of coaching recommendation strings
        """
        rule_results, llm_results = self.get_raw_results(ticket, template)
        all_results = rule_results + llm_results

        return self.formatter.get_coaching_recommendations(all_results, template)

    def check_auto_fail(
        self,
        ticket: ServiceNowTicket,
        template: TemplateType,
    ) -> tuple[bool, str | None]:
        """Quick check for auto-fail conditions.

        Only runs rules evaluation (faster than full eval).

        Args:
            ticket: ServiceNow ticket to check
            template: Template type for evaluation

        Returns:
            Tuple of (is_auto_fail, reason)
        """
        rule_results = self.rules_evaluator.evaluate(ticket, template)
        return self.calculator.check_auto_fail(rule_results)
