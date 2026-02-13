"""Main Streamlit application for onsitereview."""

import json
import logging
from datetime import datetime

import streamlit as st

from onsitereview.reports import ReportGenerator
from onsitereview.scoring import BatchTicketEvaluator, TicketEvaluator
from onsitereview.ui.components.analytics import render_analytics_section
from onsitereview.ui.components.progress import format_time
from onsitereview.ui.components.results import render_results_section
from onsitereview.ui.components.upload import render_upload_section
from onsitereview.ui.state import (
    get_state,
    has_data,
    has_results,
    init_state,
    set_error,
    set_success,
    update_state,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main Streamlit application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="onsitereview - Ticket Quality Review",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    init_state()

    # Custom CSS
    st.markdown(
        """
        <style>
        .stProgress > div > div > div {
            background-color: #3B82F6;
        }
        .block-container {
            padding-top: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        render_upload_section()

    # Main content area
    state = get_state()

    # Display messages
    if state.error_message:
        st.error(state.error_message)
    if state.success_message:
        st.success(state.success_message)

    # Check if we need to run evaluation
    if state.is_processing and has_data() and not has_results():
        run_evaluation()
        return

    # Main content based on state
    if has_results():
        render_main_content()
    elif has_data():
        render_data_loaded_view()
    else:
        render_welcome_view()


def render_welcome_view() -> None:
    """Render welcome message when no data loaded."""
    st.title("📊 onsitereview - Ticket Quality Review System")

    st.markdown(
        """
        Welcome to the **Ticket Quality Review System** - an AI-powered tool for
        evaluating onsite support ServiceNow ticket quality.

        ### Getting Started

        1. **Upload** a ServiceNow JSON export (or PDF for single tickets) using the sidebar
        2. **Configure** your OpenAI API key
        3. **Start** the evaluation and watch the progress
        4. **Review** results and coaching recommendations

        ### Scoring (Onsite Support Review)

        8 criteria across **90 points** maximum per ticket:

        | Criterion | Points | Source |
        |-----------|--------|--------|
        | Category | 5 | LLM |
        | Subcategory | 5 | LLM |
        | Service | 5 | LLM |
        | Configuration Item | 10 | LLM |
        | Opened For | 10 | Rules |
        | Incident Notes | 20 | LLM |
        | Incident Handling | 15 | LLM |
        | Resolution Notes | 20 | LLM |

        - **90%** (81 points) required to pass
        - Performance bands: 🔵 Blue (95%+), 🟢 Green (90%+), 🟡 Yellow (75%+), 🔴 Red (50%+), 🟣 Purple (<50%)
        """
    )

    # Sample data option
    st.divider()
    st.subheader("📁 Try with Sample Data")
    st.markdown(
        "Don't have ServiceNow data? Use our sample tickets to explore the system."
    )

    if st.button("Load Sample Data", type="secondary"):
        load_sample_data()


def render_data_loaded_view() -> None:
    """Render view when data is loaded but not yet evaluated."""
    state = get_state()

    st.title("📊 Ready to Evaluate")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f"""
            ### Data Summary

            - **Tickets loaded:** {len(state.tickets)}
            - **Template:** Onsite Support Review (90 points)
            - **API configured:** {'✅ Yes' if state.api_key else '❌ No'}

            Click **Start Evaluation** in the sidebar to begin processing.
            """
        )

    with col2:
        # Preview first few tickets
        st.subheader("Preview")
        for ticket in state.tickets[:3]:
            st.caption(f"🎫 {ticket.number}: {ticket.short_description[:50]}...")
        if len(state.tickets) > 3:
            st.caption(f"... and {len(state.tickets) - 3} more")


def render_main_content() -> None:
    """Render main content with results."""
    st.title("📊 Evaluation Results")

    state = get_state()

    # Summary bar
    if state.summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pass Rate", f"{state.summary.pass_rate:.1f}%")
        with col2:
            st.metric("Average Score", f"{state.summary.average_score:.1f}/90")
        with col3:
            st.metric(
                "Evaluation Time",
                format_time(state.summary.total_evaluation_time_seconds),
            )

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🎫 Tickets", "📥 Export"])

    with tab1:
        render_analytics_section()

    with tab2:
        render_results_section()

    with tab3:
        render_export_section()


def render_export_section() -> None:
    """Render export options."""
    st.subheader("📥 Export Results")

    state = get_state()
    results = state.results
    tickets = state.tickets

    if not results:
        st.info("No results to export")
        return

    # Data exports
    st.markdown("### Data Exports")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**JSON Export**")
        st.caption("Complete evaluation results in JSON format.")

        json_data = export_results_json(results)
        st.download_button(
            "⬇️ Download JSON",
            data=json_data,
            file_name=f"onsitereview_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        st.markdown("**CSV Export**")
        st.caption("Summary results in CSV format.")

        csv_data = export_results_csv(results)
        st.download_button(
            "⬇️ Download CSV",
            data=csv_data,
            file_name=f"onsitereview_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # HTML Reports
    st.divider()
    st.markdown("### HTML Reports")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Batch Summary Report**")
        st.caption("Professional HTML report with charts and analysis.")

        if state.summary:
            generator = ReportGenerator()
            batch_html = generator.generate_batch_report(
                results=results,
                summary=state.summary,
            )
            st.download_button(
                "⬇️ Download Batch Report",
                data=batch_html,
                file_name=f"onsitereview_batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True,
            )

    with col4:
        st.markdown("**Individual Ticket Reports**")
        st.caption("Select a ticket to generate its detailed report.")

        if tickets:
            # Create ticket options
            ticket_options = {r.ticket_number: i for i, r in enumerate(results)}
            selected_ticket = st.selectbox(
                "Select ticket",
                options=list(ticket_options.keys()),
                label_visibility="collapsed",
            )

            if selected_ticket:
                idx = ticket_options[selected_ticket]
                result = results[idx]
                ticket = tickets[idx]

                generator = ReportGenerator()
                individual_html = generator.generate_individual_report(
                    result=result,
                    ticket=ticket,
                )
                template_abbrev = "osr"  # Onsite Support Review

                st.download_button(
                    f"⬇️ Download {selected_ticket} Report",
                    data=individual_html,
                    file_name=f"{selected_ticket}_{template_abbrev}.html",
                    mime="text/html",
                    use_container_width=True,
                )


def run_evaluation() -> None:
    """Run batch evaluation with progress updates."""
    state = get_state()

    st.title("⏳ Evaluating Tickets...")

    # Progress placeholders
    progress_bar = st.progress(0, text="Initializing...")
    status_text = st.empty()
    metrics_container = st.empty()

    try:
        # Create evaluator with appropriate settings
        if state.use_azure:
            evaluator = TicketEvaluator.create(
                api_key=state.api_key,
                use_azure=True,
                azure_endpoint=state.azure_endpoint,
                azure_deployment=state.azure_deployment,
                azure_api_version=state.azure_api_version,
                temperature=0.1,
            )
        else:
            evaluator = TicketEvaluator.create(
                api_key=state.api_key,
                base_url=state.api_base_url or None,
                model="gpt-4o",
                temperature=0.1,
            )
        batch_evaluator = BatchTicketEvaluator(evaluator)

        # Progress callback
        def update_progress(progress):
            pct = progress.completed / progress.total if progress.total > 0 else 0
            progress_bar.progress(pct, text=f"Processing {progress.completed}/{progress.total}")

            status_text.info(f"🎫 Current: **{progress.current_ticket or 'Starting...'}**")

            with metrics_container.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Completed", f"{progress.completed}/{progress.total}")
                with col2:
                    st.metric("Elapsed", format_time(progress.elapsed_seconds))
                with col3:
                    if progress.errors > 0:
                        st.metric("Errors", progress.errors)

        # Run evaluation
        result = batch_evaluator.evaluate_batch(
            tickets=state.tickets,
            progress_callback=update_progress,
        )

        # Update state with results
        update_state(
            results=result.results,
            summary=result.summary,
            errors=result.errors,
            is_processing=False,
            current_progress=None,
        )

        set_success(
            f"Evaluation complete! {len(result.results)} tickets processed in "
            f"{format_time(result.total_time_seconds)}"
        )

    except Exception as e:
        logger.exception("Evaluation failed")
        update_state(is_processing=False)
        set_error(f"Evaluation failed: {e}")

    st.rerun()


def load_sample_data() -> None:
    """Load sample data for demonstration."""
    from pathlib import Path

    from onsitereview.parser.servicenow import ServiceNowParser

    # Find sample file relative to project root
    sample_paths = [
        Path("prototype_samples.json"),
        Path(__file__).parent.parent.parent.parent / "prototype_samples.json",
        Path("C:/onsitereview/prototype_samples.json"),
    ]

    sample_file = None
    for path in sample_paths:
        if path.exists():
            sample_file = path
            break

    if not sample_file:
        set_error("Sample data file not found")
        return

    try:
        with open(sample_file) as f:
            data = json.load(f)

        parser = ServiceNowParser()
        tickets = parser.parse_json(data)

        if tickets:
            update_state(tickets=tickets)
            set_success(f"Loaded {len(tickets)} sample tickets")
            st.rerun()
        else:
            set_error("No valid tickets found in sample data")

    except Exception as e:
        set_error(f"Error loading sample data: {e}")


def export_results_json(results: list) -> str:
    """Export results as JSON string."""
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "total_tickets": len(results),
        "results": [
            {
                "ticket_number": r.ticket_number,
                "template": r.template.value,
                "total_score": r.total_score,
                "max_score": r.max_score,
                "percentage": r.percentage,
                "band": r.band.value,
                "passed": r.passed,
                "strengths": r.strengths,
                "improvements": r.improvements,
                "criterion_scores": [
                    {
                        "criterion_id": c.criterion_id,
                        "criterion_name": c.criterion_name,
                        "points_awarded": c.points_awarded,
                        "max_points": c.max_points,
                        "percentage": c.percentage,
                        "evidence": c.evidence,
                        "reasoning": c.reasoning,
                        "coaching": c.coaching,
                    }
                    for c in r.criterion_scores
                ],
            }
            for r in results
        ],
    }
    return json.dumps(export_data, indent=2)


def export_results_csv(results: list) -> str:
    """Export results as CSV string."""
    lines = [
        "ticket_number,template,total_score,max_score,percentage,band,passed"
    ]

    for r in results:
        lines.append(
            f"{r.ticket_number},{r.template.value},{r.total_score},{r.max_score},"
            f"{r.percentage:.1f},{r.band.value},{r.passed}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    main()
