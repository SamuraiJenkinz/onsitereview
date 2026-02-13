"""Session state management for TQRS Streamlit app."""

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from tqrs.config import get_settings
from tqrs.models.evaluation import (
    BatchEvaluationSummary,
    EvaluationResult,
    TemplateType,
)
from tqrs.models.ticket import ServiceNowTicket
from tqrs.scoring.batch import BatchProgress


@dataclass
class AppState:
    """Application state container."""

    # Data
    tickets: list[ServiceNowTicket] | None = None
    results: list[EvaluationResult] | None = None
    summary: BatchEvaluationSummary | None = None
    errors: list[tuple[str, str]] = field(default_factory=list)

    # Configuration
    template: TemplateType = TemplateType.ONSITE_REVIEW
    api_key: str = ""
    api_base_url: str = ""  # For OpenAI Enterprise endpoints
    # Azure OpenAI settings
    use_azure: bool = False
    azure_endpoint: str = ""
    azure_deployment: str = ""
    azure_api_version: str = "2024-02-15-preview"

    # Server-side credential configuration
    # True when credentials are configured via environment variables
    server_credentials_configured: bool = False

    # Processing state
    is_processing: bool = False
    current_progress: BatchProgress | None = None

    # UI state
    selected_ticket_index: int = 0
    error_message: str | None = None
    success_message: str | None = None


# Session state keys
_STATE_KEY = "app_state"
_INITIALIZED_KEY = "initialized"


def init_state() -> None:
    """Initialize session state with defaults.

    If Azure OpenAI credentials are configured via environment variables
    (TQRS_AZURE_OPENAI_*), the state is pre-populated with those values
    and server_credentials_configured is set to True.
    """
    if _INITIALIZED_KEY not in st.session_state:
        settings = get_settings()

        # Check if server-side Azure credentials are configured
        if settings.azure_credentials_configured:
            # Pre-populate with env var values
            st.session_state[_STATE_KEY] = AppState(
                use_azure=True,
                azure_endpoint=settings.azure_openai_endpoint or "",
                azure_deployment=settings.azure_openai_deployment or "",
                azure_api_version=settings.azure_openai_api_version,
                api_key=settings.azure_openai_api_key or "",
                server_credentials_configured=True,
            )
        else:
            st.session_state[_STATE_KEY] = AppState()

        st.session_state[_INITIALIZED_KEY] = True


def get_state() -> AppState:
    """Get current application state."""
    if _STATE_KEY not in st.session_state:
        init_state()
    return st.session_state[_STATE_KEY]


def update_state(**kwargs: Any) -> None:
    """Update state attributes.

    Args:
        **kwargs: State attributes to update
    """
    state = get_state()
    for key, value in kwargs.items():
        if hasattr(state, key):
            setattr(state, key, value)
        else:
            raise AttributeError(f"AppState has no attribute '{key}'")


def reset_state() -> None:
    """Reset to initial state."""
    st.session_state[_STATE_KEY] = AppState()


def clear_messages() -> None:
    """Clear error and success messages."""
    state = get_state()
    state.error_message = None
    state.success_message = None


def set_error(message: str) -> None:
    """Set error message."""
    update_state(error_message=message, success_message=None)


def set_success(message: str) -> None:
    """Set success message."""
    update_state(success_message=message, error_message=None)


def has_data() -> bool:
    """Check if tickets have been loaded."""
    return get_state().tickets is not None and len(get_state().tickets) > 0


def has_results() -> bool:
    """Check if evaluation results are available."""
    return get_state().results is not None and len(get_state().results) > 0
