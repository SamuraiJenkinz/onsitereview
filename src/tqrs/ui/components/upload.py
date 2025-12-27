"""File upload component for TQRS Streamlit app."""

import json
from io import BytesIO

import streamlit as st

from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.parser.servicenow import ServiceNowParser
from tqrs.ui.state import get_state, has_data, reset_state, set_error, update_state


def render_upload_section() -> None:
    """Render file upload interface in sidebar."""
    st.header("📤 Upload & Configure")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload ServiceNow JSON",
        type=["json"],
        help="Upload a JSON file exported from ServiceNow containing ticket records",
    )

    if uploaded_file is not None:
        _handle_file_upload(uploaded_file)

    # Show ticket count if loaded
    state = get_state()
    if has_data():
        st.success(f"✅ {len(state.tickets)} tickets loaded")

    st.divider()

    # Template selection
    st.subheader("📋 Evaluation Template")
    template_options = {
        "Incident Logging": TemplateType.INCIDENT_LOGGING,
        "Incident Handling": TemplateType.INCIDENT_HANDLING,
        "Customer Service": TemplateType.CUSTOMER_SERVICE,
    }

    selected_template = st.radio(
        "Select template",
        options=list(template_options.keys()),
        index=0,
        help="Choose the evaluation template based on what aspect you want to assess",
    )
    update_state(template=template_options[selected_template])

    st.divider()

    # API key configuration
    st.subheader("🔑 API Configuration")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=state.api_key,
        help="Enter your OpenAI API key for LLM-based evaluations",
    )
    update_state(api_key=api_key)

    # Enterprise endpoint (optional)
    with st.expander("Enterprise Settings", expanded=bool(state.api_base_url)):
        api_base_url = st.text_input(
            "API Base URL (optional)",
            value=state.api_base_url,
            placeholder="https://your-endpoint.openai.azure.com/",
            help="For OpenAI Enterprise or Azure OpenAI endpoints. Leave empty for standard OpenAI API.",
        )
        update_state(api_base_url=api_base_url)

    # Process button
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        process_disabled = not has_data() or not api_key or state.is_processing
        if st.button(
            "🚀 Start Evaluation",
            disabled=process_disabled,
            use_container_width=True,
            type="primary",
        ):
            update_state(is_processing=True)
            st.rerun()

    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            reset_state()
            st.rerun()

    # Help text
    if not has_data():
        st.info("👆 Upload a JSON file to get started")
    elif not api_key:
        st.warning("⚠️ Enter your API key to enable evaluation")


def _handle_file_upload(uploaded_file: BytesIO) -> None:
    """Handle uploaded file parsing."""
    try:
        # Read and parse JSON
        content = uploaded_file.read().decode("utf-8")
        data = json.loads(content)

        # Validate structure
        is_valid, error_msg = validate_json_structure(data)
        if not is_valid:
            set_error(f"Invalid file format: {error_msg}")
            return

        # Parse tickets
        tickets = parse_tickets(data)
        if not tickets:
            set_error("No valid tickets found in file")
            return

        update_state(tickets=tickets, results=None, summary=None)

    except json.JSONDecodeError as e:
        set_error(f"Invalid JSON: {e}")
    except Exception as e:
        set_error(f"Error processing file: {e}")


def validate_json_structure(data: dict) -> tuple[bool, str]:
    """Validate uploaded JSON has expected structure.

    Args:
        data: Parsed JSON data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(data, dict):
        # Check for "records" key (standard export format)
        if "records" in data:
            if not isinstance(data["records"], list):
                return False, "'records' must be a list"
            if len(data["records"]) == 0:
                return False, "No records found in file"
            return True, ""

        # Check for "result" key (alternative format)
        if "result" in data:
            if not isinstance(data["result"], list):
                return False, "'result' must be a list"
            return True, ""

        # Check if it's a single record
        if "number" in data and "sys_id" in data:
            return True, ""

        return False, "Expected 'records' or 'result' key in JSON"

    elif isinstance(data, list):
        if len(data) == 0:
            return False, "Empty list"
        return True, ""

    return False, "Expected object or array"


def parse_tickets(data: dict | list) -> list[ServiceNowTicket]:
    """Parse JSON data into ServiceNowTicket objects.

    Args:
        data: Parsed JSON data

    Returns:
        List of parsed tickets
    """
    parser = ServiceNowParser()

    # Handle different formats
    if isinstance(data, dict):
        if "records" in data:
            records = data["records"]
        elif "result" in data:
            records = data["result"]
        else:
            # Single record
            records = [data]
    else:
        records = data

    tickets = []
    for record in records:
        try:
            ticket = parser.parse_ticket(record)
            tickets.append(ticket)
        except Exception:
            # Skip invalid records
            continue

    return tickets
