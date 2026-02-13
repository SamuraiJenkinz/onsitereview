"""Analytics dashboard component for TQRS Streamlit app."""

import plotly.graph_objects as go
import streamlit as st

from tqrs.models.evaluation import (
    BatchEvaluationSummary,
    EvaluationResult,
    PerformanceBand,
)
from tqrs.ui.state import get_state

# Color scheme for bands
BAND_COLORS = {
    "blue": "#3B82F6",
    "green": "#22C55E",
    "yellow": "#EAB308",
    "red": "#EF4444",
    "purple": "#A855F7",
}


def render_analytics_section() -> None:
    """Render analytics dashboard."""
    state = get_state()
    results = state.results
    summary = state.summary

    if not results:
        st.info("No results to analyze. Run an evaluation first.")
        return

    # Summary metrics row
    render_summary_metrics(results, summary)

    st.divider()

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Score Distribution")
        fig = create_score_distribution_chart(results)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 Performance Bands")
        fig = create_band_distribution_chart(results)
        st.plotly_chart(fig, use_container_width=True)

    # Common issues
    if summary and summary.common_issues:
        st.divider()
        st.subheader("⚠️ Common Issues")
        fig = create_common_issues_chart(summary)
        st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.divider()
    st.subheader("📋 Results Table")
    render_results_table(results)


def render_summary_metrics(
    results: list[EvaluationResult],
    summary: BatchEvaluationSummary | None,
) -> None:
    """Render summary metric cards."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_score = sum(r.total_score for r in results) / total if total > 0 else 0
    avg_percentage = sum(r.percentage for r in results) / total if total > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Tickets", total)

    with col2:
        pass_rate = (passed / total * 100) if total > 0 else 0
        st.metric("Passed", f"{passed} ({pass_rate:.0f}%)")

    with col3:
        st.metric("Failed", failed)

    with col4:
        st.metric("Avg Score", f"{avg_score:.1f}/90")

    with col5:
        st.metric("Avg %", f"{avg_percentage:.1f}%")


def create_score_distribution_chart(results: list[EvaluationResult]) -> go.Figure:
    """Create score distribution histogram."""
    scores = [r.total_score for r in results]

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=scores,
            nbinsx=18,  # 90 points / 5 = 18 bins
            marker_color="#3B82F6",
            marker_line_color="#1E40AF",
            marker_line_width=1,
            hovertemplate="Score: %{x}<br>Count: %{y}<extra></extra>",
        )
    )

    # Add pass threshold line
    fig.add_vline(
        x=81,
        line_dash="dash",
        line_color="#22C55E",
        annotation_text="Pass (81)",
        annotation_position="top",
    )

    fig.update_layout(
        xaxis_title="Score",
        yaxis_title="Number of Tickets",
        xaxis={"range": [0, 90]},
        showlegend=False,
        height=300,
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
    )

    return fig


def create_band_distribution_chart(results: list[EvaluationResult]) -> go.Figure:
    """Create band distribution pie chart."""
    # Count by band
    band_counts = {}
    for band in PerformanceBand:
        count = sum(1 for r in results if r.band == band)
        if count > 0:
            band_counts[band.display_name] = count

    if not band_counts:
        return go.Figure()

    labels = list(band_counts.keys())
    values = list(band_counts.values())
    colors = [BAND_COLORS.get(label.lower(), "#888888") for label in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                hole=0.4,
                textinfo="label+percent",
                textposition="outside",
                hovertemplate="%{label}: %{value} tickets<br>%{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        showlegend=False,
        height=300,
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
    )

    return fig


def create_common_issues_chart(summary: BatchEvaluationSummary) -> go.Figure:
    """Create common issues horizontal bar chart."""
    if not summary.common_issues:
        return go.Figure()

    # Get issue counts (using improvement frequency from results)
    issues = summary.common_issues[:5]  # Top 5

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=issues,
            x=[1] * len(issues),  # Placeholder counts
            orientation="h",
            marker_color="#EAB308",
            marker_line_color="#CA8A04",
            marker_line_width=1,
            hovertemplate="%{y}<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis_title="Frequency",
        yaxis_title="",
        showlegend=False,
        height=250,
        margin={"l": 200, "r": 40, "t": 40, "b": 40},
    )

    return fig


def render_results_table(results: list[EvaluationResult]) -> None:
    """Render results as a sortable table."""
    # Build table data
    table_data = []
    for r in results:
        band_emoji = {
            PerformanceBand.BLUE: "🔵",
            PerformanceBand.GREEN: "🟢",
            PerformanceBand.YELLOW: "🟡",
            PerformanceBand.RED: "🔴",
            PerformanceBand.PURPLE: "🟣",
        }.get(r.band, "⚪")

        status = "✅ Pass" if r.passed else "❌ Fail"

        table_data.append({
            "Ticket": r.ticket_number,
            "Score": f"{r.total_score}/90",
            "Percentage": f"{r.percentage:.1f}%",
            "Band": f"{band_emoji} {r.band.display_name}",
            "Status": status,
        })

    # Display with filtering
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pass", "Fail"],
        )

    with filter_col2:
        band_filter = st.selectbox(
            "Filter by Band",
            ["All", "Blue", "Green", "Yellow", "Red", "Purple"],
        )

    # Apply filters
    filtered_data = table_data
    if status_filter != "All":
        if status_filter == "Pass":
            filtered_data = [d for d in filtered_data if "Pass" in d["Status"]]
        elif status_filter == "Fail":
            filtered_data = [d for d in filtered_data if "Fail" in d["Status"]]

    if band_filter != "All":
        filtered_data = [d for d in filtered_data if band_filter in d["Band"]]

    # Display table
    if filtered_data:
        st.dataframe(
            filtered_data,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No tickets match the selected filters")
