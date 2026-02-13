"""Progress tracking component for onsitereview Streamlit app."""

from collections.abc import Callable

import streamlit as st

from onsitereview.scoring.batch import BatchProgress
from onsitereview.ui.state import get_state, update_state


def render_progress_section() -> None:
    """Render progress tracking UI during evaluation."""
    state = get_state()
    progress = state.current_progress

    st.header("⏳ Evaluation in Progress")

    if progress is None:
        st.info("Starting evaluation...")
        return

    # Progress bar
    progress_value = progress.completed / progress.total if progress.total > 0 else 0
    st.progress(progress_value)

    # Progress metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Completed",
            f"{progress.completed}/{progress.total}",
            delta=None,
        )

    with col2:
        st.metric(
            "Progress",
            f"{progress.percentage:.1f}%",
        )

    with col3:
        elapsed = format_time(progress.elapsed_seconds)
        st.metric("Elapsed", elapsed)

    with col4:
        if progress.completed > 0:
            remaining = format_time(progress.estimated_remaining_seconds)
            st.metric("Remaining", remaining)
        else:
            st.metric("Remaining", "Calculating...")

    # Current ticket
    if progress.current_ticket:
        st.info(f"🎫 Processing: **{progress.current_ticket}**")

    # Error count
    if progress.errors > 0:
        st.warning(f"⚠️ {progress.errors} error(s) encountered")

    # Cancel button
    if st.button("❌ Cancel", type="secondary"):
        update_state(is_processing=False)
        st.rerun()


def create_progress_callback() -> Callable[[BatchProgress], None]:
    """Create callback for batch evaluator progress updates.

    Returns:
        Callback function that updates session state
    """
    # Use a placeholder that we can update
    progress_placeholder = st.empty()
    metrics_placeholder = st.empty()

    def callback(progress: BatchProgress) -> None:
        """Update progress display."""
        update_state(current_progress=progress)

        # Update the progress bar
        with progress_placeholder.container():
            progress_value = progress.completed / progress.total if progress.total > 0 else 0
            st.progress(progress_value, text=f"Processing {progress.completed}/{progress.total}")

        # Update metrics
        with metrics_placeholder.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"✅ {progress.completed}/{progress.total} complete")
            with col2:
                st.caption(f"⏱️ {format_time(progress.elapsed_seconds)} elapsed")
            with col3:
                if progress.errors > 0:
                    st.caption(f"⚠️ {progress.errors} errors")

    return callback


def create_simple_progress_callback() -> Callable[[BatchProgress], None]:
    """Create a simpler callback for non-async usage.

    Returns:
        Callback function that just updates state
    """

    def callback(progress: BatchProgress) -> None:
        """Update progress in session state."""
        update_state(current_progress=progress)

    return callback


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
