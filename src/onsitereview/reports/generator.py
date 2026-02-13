"""HTML report generation for onsitereview."""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from onsitereview.models.evaluation import (
    BatchEvaluationSummary,
    EvaluationResult,
    PerformanceBand,
    TemplateType,
)
from onsitereview.models.ticket import ServiceNowTicket
from onsitereview.scoring.formatter import ResultFormatter


class ReportGenerator:
    """Generate HTML reports from evaluation results."""

    # Band color mapping
    BAND_COLORS = {
        "BLUE": "#3B82F6",
        "GREEN": "#22C55E",
        "YELLOW": "#EAB308",
        "RED": "#EF4444",
        "PURPLE": "#A855F7",
    }

    # Template display names
    TEMPLATE_NAMES = {
        TemplateType.ONSITE_REVIEW: "Onsite Support Review",
    }

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize report generator with template directory.

        Args:
            template_dir: Custom template directory. Defaults to package templates.
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _get_band_color(self, band: PerformanceBand | str) -> str:
        """Get hex color for performance band."""
        if isinstance(band, PerformanceBand):
            band_name = band.value.upper()
        else:
            band_name = band.upper()
        return self.BAND_COLORS.get(band_name, "#6B7280")

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display."""
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _get_template_name(self, template: TemplateType) -> str:
        """Get display name for template type."""
        return self.TEMPLATE_NAMES.get(template, str(template.value))

    def _prepare_criterion_data(self, result: EvaluationResult) -> list[dict]:
        """Prepare criterion scores for template rendering."""
        criteria_data = []
        for cs in result.criterion_scores:
            criteria_data.append({
                "name": cs.criterion_name,
                "score": cs.points_awarded,
                "max_points": cs.max_points,
                "percentage": cs.percentage,
                "evidence": cs.evidence,
                "reasoning": cs.reasoning,
                "coaching": cs.coaching,
            })
        return criteria_data

    def generate_individual_report(
        self,
        result: EvaluationResult,
        ticket: ServiceNowTicket,
    ) -> str:
        """Generate HTML report for a single ticket evaluation.

        Args:
            result: Evaluation result for the ticket.
            ticket: Original ServiceNow ticket data.

        Returns:
            HTML string of the report.
        """
        template = self.env.get_template("individual.html")

        # Generate path to passing recommendations for failing tickets
        path_to_passing = []
        if not result.passed:
            formatter = ResultFormatter()
            path_to_passing = formatter.generate_path_to_passing(
                criterion_scores=result.criterion_scores,
                total_score=result.total_score,
                max_score=result.max_score,
            )

        context = {
            # Ticket info
            "ticket_number": result.ticket_number,
            "template_name": self._get_template_name(result.template),
            "contact_type": ticket.contact_type.capitalize(),
            "category": ticket.category,
            "subcategory": ticket.subcategory,
            "priority": ticket.priority,
            "short_description": ticket.short_description,
            "description": ticket.description,
            "close_notes": ticket.close_notes,
            # Scores
            "total_score": result.total_score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "band": result.band.display_name,
            "band_color": self._get_band_color(result.band),
            "passed": result.passed,
            # Criterion breakdown
            "criterion_scores": self._prepare_criterion_data(result),
            # Path to Passing (credit score style recommendations)
            "path_to_passing": path_to_passing,
            # Coaching
            "strengths": result.strengths,
            "improvements": result.improvements,
            # Metadata
            "evaluated_at": self._format_datetime(result.evaluated_at),
            "generated_at": self._format_datetime(datetime.now()),
        }

        return template.render(**context)

    def generate_batch_report(
        self,
        results: list[EvaluationResult],
        summary: BatchEvaluationSummary,
    ) -> str:
        """Generate HTML summary report for a batch of evaluations.

        Args:
            results: List of evaluation results.
            summary: Batch summary statistics.

        Returns:
            HTML string of the batch report.
        """
        template = self.env.get_template("batch.html")

        # Prepare results data for table
        results_data = []
        scores = []
        for r in results:
            scores.append(r.total_score)
            results_data.append({
                "ticket_number": r.ticket_number,
                "total_score": r.total_score,
                "max_score": r.max_score,
                "percentage": r.percentage,
                "band": r.band.display_name,
                "band_color": self._get_band_color(r.band),
                "passed": r.passed,
            })

        # Prepare band distribution data for charts
        band_order = ["BLUE", "GREEN", "YELLOW", "RED", "PURPLE"]
        band_labels = []
        band_values = []
        band_colors = []

        for band in band_order:
            count = summary.band_distribution.get(band, 0)
            if count > 0:
                band_labels.append(band.capitalize())
                band_values.append(count)
                band_colors.append(self.BAND_COLORS[band])

        # Calculate additional stats
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0

        # Average band color
        avg_band = PerformanceBand.from_percentage(summary.average_percentage)

        # Template name
        if results:
            template_name = self._get_template_name(results[0].template)
        else:
            template_name = "Onsite Support Review"

        context = {
            # Header
            "template_name": template_name,
            "generated_at": self._format_datetime(datetime.now()),
            # Summary stats
            "total_tickets": summary.total_tickets,
            "passed_count": summary.passed_count,
            "failed_count": summary.failed_count,
            "average_score": summary.average_score,
            "average_percentage": round(summary.average_percentage, 1),
            "average_band_color": self._get_band_color(avg_band),
            "pass_rate": round(summary.pass_rate, 1),
            # Charts data
            "scores_json": json.dumps(scores),
            "band_labels_json": json.dumps(band_labels),
            "band_values_json": json.dumps(band_values),
            "band_colors_json": json.dumps(band_colors),
            # Band distribution
            "band_distribution": summary.band_distribution,
            "band_colors": self.BAND_COLORS,
            # Common issues
            "common_issues": summary.common_issues[:5],
            # Results table
            "results": results_data,
            # Additional stats
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "total_time_seconds": summary.total_evaluation_time_seconds,
        }

        return template.render(**context)

    def save_report(self, html: str, path: Path) -> None:
        """Save HTML report to file.

        Args:
            html: HTML content to save.
            path: Output file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    def generate_and_save_individual(
        self,
        result: EvaluationResult,
        ticket: ServiceNowTicket,
        output_dir: Path,
    ) -> Path:
        """Generate and save individual report.

        Args:
            result: Evaluation result.
            ticket: Original ticket data.
            output_dir: Directory to save report.

        Returns:
            Path to saved report.
        """
        html = self.generate_individual_report(result, ticket)
        filename = f"{result.ticket_number}_review.html"
        output_path = output_dir / filename
        self.save_report(html, output_path)
        return output_path

    def generate_and_save_batch(
        self,
        results: list[EvaluationResult],
        summary: BatchEvaluationSummary,
        output_path: Path,
    ) -> Path:
        """Generate and save batch summary report.

        Args:
            results: List of evaluation results.
            summary: Batch summary statistics.
            output_path: Output file path.

        Returns:
            Path to saved report.
        """
        html = self.generate_batch_report(results, summary)
        self.save_report(html, output_path)
        return output_path
