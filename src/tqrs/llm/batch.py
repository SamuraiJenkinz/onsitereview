"""Batch processing for LLM ticket evaluation."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from tqrs.llm.client import LLMError, OpenAIClient, TokenUsage
from tqrs.llm.evaluator import LLMEvaluator
from tqrs.models.ticket import ServiceNowTicket
from tqrs.rules.base import RuleResult

logger = logging.getLogger(__name__)


@dataclass
class BatchProgress:
    """Progress tracking for batch evaluation."""

    total: int = 0
    completed: int = 0
    failed: int = 0
    current_ticket: str = ""
    start_time: float = field(default_factory=time.time)

    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return round((self.completed / self.total) * 100, 1)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time

    @property
    def estimated_remaining_seconds(self) -> float:
        """Estimate remaining time based on current pace."""
        if self.completed == 0:
            return 0.0
        avg_time = self.elapsed_seconds / self.completed
        remaining = self.total - self.completed
        return avg_time * remaining


@dataclass
class TicketEvaluationResult:
    """Result of evaluating a single ticket in a batch."""

    ticket_number: str
    success: bool
    rule_results: list[RuleResult] = field(default_factory=list)
    error: str | None = None
    evaluation_time_seconds: float = 0.0


@dataclass
class BatchResult:
    """Complete result of a batch evaluation."""

    results: list[TicketEvaluationResult]
    total_tickets: int
    successful: int
    failed: int
    total_time_seconds: float
    token_usage: TokenUsage

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tickets == 0:
            return 0.0
        return round((self.successful / self.total_tickets) * 100, 1)


class BatchLLMEvaluator:
    """Batch processor for LLM ticket evaluations with concurrency control."""

    def __init__(
        self,
        client: OpenAIClient,
        concurrency: int = 5,
    ):
        self.client = client
        self.evaluator = LLMEvaluator(client)
        self.concurrency = concurrency

    def evaluate_batch(
        self,
        tickets: list[ServiceNowTicket],
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchResult:
        """Evaluate multiple tickets with rate limiting.

        Args:
            tickets: List of tickets to evaluate
            progress_callback: Optional callback for progress updates

        Returns:
            BatchResult with all evaluation results
        """
        start_time = time.time()
        self.client.reset_usage()

        progress = BatchProgress(total=len(tickets))
        results: list[TicketEvaluationResult] = []

        for ticket in tickets:
            progress.current_ticket = ticket.number

            if progress_callback:
                progress_callback(progress)

            ticket_start = time.time()

            try:
                rule_results = self.evaluator.evaluate_ticket(ticket)

                results.append(TicketEvaluationResult(
                    ticket_number=ticket.number,
                    success=True,
                    rule_results=rule_results,
                    evaluation_time_seconds=time.time() - ticket_start,
                ))
                progress.completed += 1

            except LLMError as e:
                logger.error(f"LLM error evaluating {ticket.number}: {e}")
                results.append(TicketEvaluationResult(
                    ticket_number=ticket.number,
                    success=False,
                    error=str(e),
                    evaluation_time_seconds=time.time() - ticket_start,
                ))
                progress.failed += 1

            except Exception as e:
                logger.exception(f"Unexpected error evaluating {ticket.number}: {e}")
                results.append(TicketEvaluationResult(
                    ticket_number=ticket.number,
                    success=False,
                    error=str(e),
                    evaluation_time_seconds=time.time() - ticket_start,
                ))
                progress.failed += 1

        # Final progress update
        if progress_callback:
            progress_callback(progress)

        return BatchResult(
            results=results,
            total_tickets=len(tickets),
            successful=progress.completed,
            failed=progress.failed,
            total_time_seconds=time.time() - start_time,
            token_usage=self.client.token_usage,
        )

    async def evaluate_batch_async(
        self,
        tickets: list[ServiceNowTicket],
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchResult:
        """Evaluate multiple tickets concurrently.

        Args:
            tickets: List of tickets to evaluate
            progress_callback: Optional callback for progress updates

        Returns:
            BatchResult with all evaluation results
        """
        start_time = time.time()
        self.client.reset_usage()

        progress = BatchProgress(total=len(tickets))
        semaphore = asyncio.Semaphore(self.concurrency)

        async def evaluate_one(ticket: ServiceNowTicket) -> TicketEvaluationResult:
            async with semaphore:
                ticket_start = time.time()

                try:
                    loop = asyncio.get_event_loop()
                    rule_results = await loop.run_in_executor(
                        None,
                        self.evaluator.evaluate_ticket,
                        ticket,
                    )

                    progress.completed += 1
                    progress.current_ticket = ticket.number

                    if progress_callback:
                        progress_callback(progress)

                    return TicketEvaluationResult(
                        ticket_number=ticket.number,
                        success=True,
                        rule_results=rule_results,
                        evaluation_time_seconds=time.time() - ticket_start,
                    )

                except LLMError as e:
                    logger.error(f"LLM error evaluating {ticket.number}: {e}")
                    progress.failed += 1

                    if progress_callback:
                        progress_callback(progress)

                    return TicketEvaluationResult(
                        ticket_number=ticket.number,
                        success=False,
                        error=str(e),
                        evaluation_time_seconds=time.time() - ticket_start,
                    )

                except Exception as e:
                    logger.exception(f"Unexpected error evaluating {ticket.number}: {e}")
                    progress.failed += 1

                    if progress_callback:
                        progress_callback(progress)

                    return TicketEvaluationResult(
                        ticket_number=ticket.number,
                        success=False,
                        error=str(e),
                        evaluation_time_seconds=time.time() - ticket_start,
                    )

        # Run all evaluations concurrently
        results = await asyncio.gather(*[evaluate_one(t) for t in tickets])

        return BatchResult(
            results=list(results),
            total_tickets=len(tickets),
            successful=progress.completed,
            failed=progress.failed,
            total_time_seconds=time.time() - start_time,
            token_usage=self.client.token_usage,
        )

    def evaluate_single(
        self,
        ticket: ServiceNowTicket,
    ) -> TicketEvaluationResult:
        """Evaluate a single ticket.

        Args:
            ticket: Ticket to evaluate

        Returns:
            TicketEvaluationResult
        """
        start_time = time.time()

        try:
            rule_results = self.evaluator.evaluate_ticket(ticket)

            return TicketEvaluationResult(
                ticket_number=ticket.number,
                success=True,
                rule_results=rule_results,
                evaluation_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception(f"Error evaluating {ticket.number}: {e}")
            return TicketEvaluationResult(
                ticket_number=ticket.number,
                success=False,
                error=str(e),
                evaluation_time_seconds=time.time() - start_time,
            )
