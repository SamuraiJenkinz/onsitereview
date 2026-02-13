"""Batch ticket evaluation for onsitereview - Onsite Support Review."""

import asyncio
import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from onsitereview.models.evaluation import (
    BatchEvaluationSummary,
    EvaluationResult,
    PerformanceBand,
)
from onsitereview.models.ticket import ServiceNowTicket
from onsitereview.scoring.evaluator import TicketEvaluator

logger = logging.getLogger(__name__)


@dataclass
class BatchProgress:
    """Progress information for batch processing."""

    total: int
    completed: int
    current_ticket: str | None = None
    errors: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 100.0
        return round((self.completed / self.total) * 100, 1)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def estimated_remaining_seconds(self) -> float:
        if self.completed == 0:
            return 0.0
        avg_time = self.elapsed_seconds / self.completed
        remaining = self.total - self.completed
        return avg_time * remaining


@dataclass
class BatchResult:
    """Complete result from batch evaluation."""

    results: list[EvaluationResult]
    errors: list[tuple[str, str]]  # (ticket_number, error_message)
    summary: BatchEvaluationSummary
    total_time_seconds: float


class BatchTicketEvaluator:
    """Evaluate multiple tickets with progress tracking."""

    def __init__(
        self,
        evaluator: TicketEvaluator,
        concurrency: int = 5,
    ):
        self.evaluator = evaluator
        self.concurrency = concurrency

    def evaluate_batch(
        self,
        tickets: list[ServiceNowTicket],
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchResult:
        """Evaluate a batch of tickets sequentially."""
        start_time = time.time()
        results: list[EvaluationResult] = []
        errors: list[tuple[str, str]] = []

        progress = BatchProgress(total=len(tickets), completed=0)

        for ticket in tickets:
            progress.current_ticket = ticket.number

            if progress_callback:
                progress_callback(progress)

            try:
                result = self.evaluator.evaluate_ticket(ticket)
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating {ticket.number}: {e}")
                errors.append((ticket.number, str(e)))
                progress.errors += 1

            progress.completed += 1

        progress.current_ticket = None
        if progress_callback:
            progress_callback(progress)

        total_time = time.time() - start_time
        summary = self.generate_summary(results)
        summary.total_evaluation_time_seconds = total_time

        return BatchResult(
            results=results,
            errors=errors,
            summary=summary,
            total_time_seconds=total_time,
        )

    async def evaluate_batch_async(
        self,
        tickets: list[ServiceNowTicket],
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ) -> BatchResult:
        """Evaluate a batch of tickets with concurrency."""
        start_time = time.time()
        semaphore = asyncio.Semaphore(self.concurrency)

        progress = BatchProgress(total=len(tickets), completed=0)
        results: list[EvaluationResult] = []
        errors: list[tuple[str, str]] = []
        lock = asyncio.Lock()

        async def evaluate_one(ticket: ServiceNowTicket) -> None:
            nonlocal progress
            async with semaphore:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.evaluator.evaluate_ticket(ticket),
                    )
                    async with lock:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error evaluating {ticket.number}: {e}")
                    async with lock:
                        errors.append((ticket.number, str(e)))
                        progress.errors += 1
                finally:
                    async with lock:
                        progress.completed += 1
                        progress.current_ticket = ticket.number
                        if progress_callback:
                            progress_callback(progress)

        await asyncio.gather(*[evaluate_one(t) for t in tickets])

        progress.current_ticket = None
        if progress_callback:
            progress_callback(progress)

        total_time = time.time() - start_time
        summary = self.generate_summary(results)
        summary.total_evaluation_time_seconds = total_time

        return BatchResult(
            results=results,
            errors=errors,
            summary=summary,
            total_time_seconds=total_time,
        )

    def generate_summary(
        self,
        results: list[EvaluationResult],
    ) -> BatchEvaluationSummary:
        """Generate summary statistics from evaluation results."""
        if not results:
            return BatchEvaluationSummary(
                total_tickets=0,
                passed_count=0,
                failed_count=0,
                average_score=0.0,
                average_percentage=0.0,
                band_distribution={},
                common_issues=[],
                evaluated_at=datetime.now(),
            )

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        avg_score = sum(r.total_score for r in results) / total
        avg_percentage = sum(r.percentage for r in results) / total

        band_counts: Counter[str] = Counter()
        for result in results:
            band_counts[result.band.value] += 1

        band_distribution = {
            band.value: band_counts.get(band.value, 0)
            for band in PerformanceBand
        }

        issue_counts: Counter[str] = Counter()
        for result in results:
            for improvement in result.improvements:
                if ": " in improvement:
                    criterion = improvement.split(": ")[0]
                    issue_counts[criterion] += 1
                else:
                    issue_counts[improvement] += 1

        common_issues = [issue for issue, _ in issue_counts.most_common(5)]

        return BatchEvaluationSummary(
            total_tickets=total,
            passed_count=passed,
            failed_count=failed,
            average_score=round(avg_score, 1),
            average_percentage=round(avg_percentage, 1),
            band_distribution=band_distribution,
            common_issues=common_issues,
            evaluated_at=datetime.now(),
        )


def evaluate_tickets(
    tickets: list[ServiceNowTicket],
    api_key: str,
    base_url: str | None = None,
    model: str = "gpt-4o",
    concurrency: int = 5,
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> BatchResult:
    """High-level API for batch ticket evaluation."""
    evaluator = TicketEvaluator.create(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    batch_evaluator = BatchTicketEvaluator(
        evaluator=evaluator,
        concurrency=concurrency,
    )

    return batch_evaluator.evaluate_batch(
        tickets=tickets,
        progress_callback=progress_callback,
    )


async def evaluate_tickets_async(
    tickets: list[ServiceNowTicket],
    api_key: str,
    base_url: str | None = None,
    model: str = "gpt-4o",
    concurrency: int = 5,
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> BatchResult:
    """High-level async API for batch ticket evaluation."""
    evaluator = TicketEvaluator.create(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    batch_evaluator = BatchTicketEvaluator(
        evaluator=evaluator,
        concurrency=concurrency,
    )

    return await batch_evaluator.evaluate_batch_async(
        tickets=tickets,
        progress_callback=progress_callback,
    )
