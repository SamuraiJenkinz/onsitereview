"""Results display component for onsitereview Streamlit app."""

import streamlit as st

from onsitereview.models.evaluation import EvaluationResult, PerformanceBand
from onsitereview.scoring.formatter import ResultFormatter
from onsitereview.ui.state import get_state, update_state


def render_results_section() -> None:
    """Render results viewing interface."""
    state = get_state()
    results = state.results

    if not results:
        st.info("No results to display. Run an evaluation first.")
        return

    # Ticket selector
    st.subheader("🎫 Select Ticket")

    # Create options for selectbox
    ticket_options = [
        f"{r.ticket_number} - {_get_band_emoji(r.band)} {r.total_score}/{r.max_score}"
        for r in results
    ]

    selected_idx = st.selectbox(
        "Choose a ticket to view details",
        range(len(results)),
        format_func=lambda i: ticket_options[i],
        index=state.selected_ticket_index,
    )

    if selected_idx != state.selected_ticket_index:
        update_state(selected_ticket_index=selected_idx)

    # Display selected ticket
    selected_result = results[selected_idx]
    render_ticket_details(selected_result)


def render_ticket_details(result: EvaluationResult) -> None:
    """Render detailed view for a single ticket."""
    st.divider()

    # Score summary card
    render_score_card(result)

    # Tabs for different sections - include Path to Passing for failing tickets
    if not result.passed:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎯 Path to Passing",
            "📊 Scores",
            "💪 Strengths & Improvements",
            "💡 Coaching"
        ])

        with tab1:
            render_path_to_passing(result)

        with tab2:
            render_criterion_table(result)

        with tab3:
            render_strengths_improvements(result)

        with tab4:
            render_coaching_section(result)
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Scores", "💪 Strengths & Improvements", "💡 Coaching"])

        with tab1:
            render_criterion_table(result)

        with tab2:
            render_strengths_improvements(result)

        with tab3:
            render_coaching_section(result)


def render_score_card(result: EvaluationResult) -> None:
    """Render score summary card."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        band_color = _get_band_color(result.band)
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem; background-color: {band_color}20;
                        border-radius: 0.5rem; border: 2px solid {band_color};">
                <h2 style="color: {band_color}; margin: 0;">{result.total_score}/{result.max_score}</h2>
                <p style="margin: 0;">Score</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.metric("Percentage", f"{result.percentage:.1f}%")

    with col3:
        band_emoji = _get_band_emoji(result.band)
        st.metric("Band", f"{band_emoji} {result.band.display_name}")

    with col4:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        st.metric("Status", status)


def render_path_to_passing(result: EvaluationResult) -> None:
    """Render path to passing recommendations (like credit score improvement tips)."""
    st.subheader("🎯 How to Reach 90% (Passing)")

    # Generate path to passing recommendations
    formatter = ResultFormatter()
    recommendations = formatter.generate_path_to_passing(
        criterion_scores=result.criterion_scores,
        total_score=result.total_score,
        max_score=result.max_score,
    )

    if not recommendations:
        st.info("No improvement recommendations available.")
        return

    # Show summary card
    for rec in recommendations:
        if rec["priority"] == "summary":
            points_needed = rec["points_recoverable"]
            current_pct = result.percentage

            # Summary box
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; padding: 1.5rem; border-radius: 1rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
                                {rec["action"]}
                            </div>
                            <div style="opacity: 0.9;">{rec["details"]}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2.5rem; font-weight: bold;">+{points_needed}</div>
                            <div style="opacity: 0.8;">points needed</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Progress bar
            st.progress(current_pct / 100, text=f"Current: {current_pct:.1f}% → Target: 90%")
            break

    st.divider()
    st.markdown("### Prioritized Actions")
    st.caption("Actions are sorted by impact. Focus on the top items first.")

    # Show individual recommendations
    for rec in recommendations:
        if rec["priority"] in ("summary", "none"):
            continue

        # Priority badge color
        priority_colors = {
            "critical": ("#dc2626", "🚨"),
            "high": ("#ea580c", "⚡"),
            "medium": ("#ca8a04", "📌"),
            "low": ("#6b7280", "💡"),
        }
        color, icon = priority_colors.get(rec["priority"], ("#6b7280", "•"))

        # Create expandable section for each recommendation
        with st.expander(
            f"{icon} **+{rec['points_recoverable']} pts** - {rec['action']} → {rec['projected_percentage']}%",
            expanded=rec["priority"] in ("critical", "high"),
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Details:** {rec.get('details', 'No additional details.')}")
                if rec.get("current"):
                    st.caption(f"Current score: {rec['current']}")

            with col2:
                st.metric(
                    "Impact",
                    f"+{rec['points_recoverable']}",
                    delta=f"→ {rec['projected_percentage']}%",
                )

            # Highlight if this action alone would achieve passing
            if rec["projected_percentage"] >= 90:
                st.success("✓ This action would bring the ticket to passing!")


def render_criterion_table(result: EvaluationResult) -> None:
    """Render criterion scores as table."""
    st.subheader("Criterion Breakdown")

    for score in result.criterion_scores:
        with st.expander(
            f"{_get_score_emoji(score.points_awarded, score.max_points)} "
            f"**{score.criterion_name}**: {score.points_awarded}/{score.max_points} ({score.percentage}%)"
        ):
            # Score bar
            if score.max_points > 0:
                progress = score.points_awarded / score.max_points
                st.progress(progress)

            # Details
            st.markdown(f"**Evidence:** {score.evidence}")
            st.markdown(f"**Reasoning:** {score.reasoning}")

            if score.coaching:
                st.info(f"💡 **Coaching:** {score.coaching}")


def render_strengths_improvements(result: EvaluationResult) -> None:
    """Render strengths and improvements sections."""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💪 Strengths")
        if result.strengths:
            for strength in result.strengths:
                st.success(f"✓ {strength}")
        else:
            st.info("No specific strengths identified")

    with col2:
        st.subheader("📈 Areas for Improvement")
        if result.improvements:
            for improvement in result.improvements:
                st.warning(f"• {improvement}")
        else:
            st.info("No specific improvements needed")


def render_coaching_section(result: EvaluationResult) -> None:
    """Render coaching recommendations."""
    st.subheader("💡 Coaching Recommendations")

    # Collect all coaching from criteria
    coaching_items = [
        (score.criterion_name, score.coaching)
        for score in result.criterion_scores
        if score.coaching
    ]

    if coaching_items:
        for criterion_name, coaching in coaching_items:
            st.markdown(f"**{criterion_name}:**")
            st.info(coaching)
    else:
        st.success("Great work! No specific coaching recommendations at this time.")

    # General tips based on score
    st.divider()
    st.markdown("### 📚 General Tips")

    if result.percentage >= 95:
        st.success(
            "Excellent ticket quality! Maintain this high standard by continuing to "
            "document thoroughly and follow all processes."
        )
    elif result.percentage >= 90:
        st.info(
            "Good ticket quality. Review the minor improvements above to "
            "reach excellence level."
        )
    elif result.percentage >= 75:
        st.warning(
            "Adequate ticket quality but room for improvement. Focus on the "
            "identified areas and consider additional training."
        )
    else:
        st.error(
            "Ticket quality needs significant improvement. Please review the "
            "coaching recommendations carefully and seek guidance from your team lead."
        )


def _get_band_emoji(band: PerformanceBand) -> str:
    """Get emoji for performance band."""
    emojis = {
        PerformanceBand.BLUE: "🔵",
        PerformanceBand.GREEN: "🟢",
        PerformanceBand.YELLOW: "🟡",
        PerformanceBand.RED: "🔴",
        PerformanceBand.PURPLE: "🟣",
    }
    return emojis.get(band, "⚪")


def _get_band_color(band: PerformanceBand) -> str:
    """Get CSS color for performance band."""
    return band.css_color


def _get_score_emoji(points: int, max_points: int) -> str:
    """Get emoji based on score percentage."""
    if max_points == 0:
        return "✓"
    percentage = (points / max_points) * 100
    if percentage >= 90:
        return "✅"
    elif percentage >= 70:
        return "⚠️"
    else:
        return "❌"
