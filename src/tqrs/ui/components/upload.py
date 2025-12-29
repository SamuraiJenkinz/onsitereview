"""File upload component for TQRS Streamlit app."""

import json
from io import BytesIO

import streamlit as st

from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket
from tqrs.parser.pdf import PDFParser
from tqrs.parser.servicenow import ServiceNowParser
from tqrs.ui.state import get_state, has_data, reset_state, set_error, set_success, update_state


def render_upload_section() -> None:
    """Render file upload interface in sidebar."""
    st.header("📤 Upload & Configure")

    # Batch upload - JSON
    st.subheader("📁 Batch Upload (JSON)")
    uploaded_json = st.file_uploader(
        "Upload ServiceNow JSON",
        type=["json"],
        help="Upload a JSON file exported from ServiceNow containing multiple ticket records",
        key="json_uploader",
    )

    # Only process if it's a new file (not already loaded)
    if uploaded_json is not None:
        # Check if this is a new file by comparing name
        current_file = st.session_state.get("_uploaded_file_name")
        if current_file != uploaded_json.name:
            # Mark as processed BEFORE handling to prevent rerun loop
            st.session_state["_uploaded_file_name"] = uploaded_json.name
            _handle_json_upload(uploaded_json)

    # Single ticket upload - PDF
    st.subheader("📄 Single Ticket (PDF)")
    uploaded_pdf = st.file_uploader(
        "Upload Incident PDF",
        type=["pdf"],
        help="Upload a single incident PDF report exported from ServiceNow",
        key="pdf_uploader",
    )

    # Process PDF upload
    if uploaded_pdf is not None:
        current_pdf = st.session_state.get("_uploaded_pdf_name")
        if current_pdf != uploaded_pdf.name:
            st.session_state["_uploaded_pdf_name"] = uploaded_pdf.name
            _handle_pdf_upload(uploaded_pdf)

    # Show ticket count if loaded
    state = get_state()
    if has_data():
        st.success(f"✅ {len(state.tickets)} ticket(s) loaded")

    st.divider()

    # Template selection
    st.subheader("📋 Evaluation Template")
    template_options = {
        "Incident Logging": TemplateType.INCIDENT_LOGGING,
        "Incident Handling": TemplateType.INCIDENT_HANDLING,
    }

    # Get current template to detect changes
    current_template = state.template

    selected_template = st.radio(
        "Select template",
        options=list(template_options.keys()),
        index=list(template_options.values()).index(current_template),
        help="Choose the evaluation template based on what aspect you want to assess",
    )
    new_template = template_options[selected_template]

    # If template changed, reset evaluation state (but keep tickets and API config)
    if new_template != current_template:
        update_state(
            template=new_template,
            results=None,
            summary=None,
            is_processing=False,
            current_progress=None,
            selected_ticket_index=0,
            errors=[],
        )
        st.rerun()
    else:
        update_state(template=new_template)

    st.divider()

    # API Configuration
    st.subheader("🔑 API Configuration")

    # Provider selection
    provider = st.radio(
        "API Provider",
        options=["OpenAI", "Azure OpenAI"],
        index=1 if state.use_azure else 0,
        horizontal=True,
        help="Select your AI provider",
    )
    use_azure = provider == "Azure OpenAI"
    update_state(use_azure=use_azure)

    if use_azure:
        # Azure OpenAI configuration
        azure_endpoint = st.text_input(
            "Azure Endpoint",
            value=state.azure_endpoint,
            placeholder="https://your-resource.openai.azure.com/",
            help="Azure OpenAI endpoint URL (without /chat/completions)",
        )
        update_state(azure_endpoint=azure_endpoint)

        azure_deployment = st.text_input(
            "Deployment Name",
            value=state.azure_deployment,
            placeholder="gpt-4o-mini",
            help="Azure OpenAI deployment name",
        )
        update_state(azure_deployment=azure_deployment)

        api_key = st.text_input(
            "API Key",
            type="password",
            value=state.api_key,
            help="Azure OpenAI API key",
        )
        update_state(api_key=api_key)

        with st.expander("Advanced Settings"):
            azure_api_version = st.text_input(
                "API Version",
                value=state.azure_api_version,
                help="Azure OpenAI API version",
            )
            update_state(azure_api_version=azure_api_version)
    else:
        # Standard OpenAI configuration
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
                placeholder="https://your-enterprise-endpoint/v1",
                help="For OpenAI Enterprise endpoints. Leave empty for standard OpenAI API.",
            )
            update_state(api_base_url=api_base_url)

    # Test Connection button
    st.divider()
    test_disabled = not api_key
    if st.button("🔌 Test Connection", disabled=test_disabled, use_container_width=True):
        _test_llm_connection(state)

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
            st.session_state.pop("_uploaded_file_name", None)
            st.session_state.pop("_uploaded_pdf_name", None)
            st.rerun()

    # Help text
    if not has_data():
        st.info("👆 Upload a JSON file (batch) or PDF (single ticket) to get started")
    elif not api_key:
        st.warning("⚠️ Enter your API key to enable evaluation")


def _test_llm_connection(state) -> None:
    """Test the LLM API connection."""
    from tqrs.llm.client import OpenAIClient

    with st.spinner("Testing connection..."):
        try:
            if state.use_azure:
                client = OpenAIClient(
                    api_key=state.api_key,
                    use_azure=True,
                    azure_endpoint=state.azure_endpoint,
                    azure_deployment=state.azure_deployment,
                    azure_api_version=state.azure_api_version,
                    timeout=15,
                    max_retries=1,
                )
            else:
                client = OpenAIClient(
                    api_key=state.api_key,
                    base_url=state.api_base_url or None,
                    model="gpt-4o",
                    timeout=15,
                    max_retries=1,
                )

            # Send a simple test message (include 'json' in prompt for Azure compatibility)
            response = client.complete(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Respond in JSON format."},
                    {"role": "user", "content": "Return a json object with a single key 'status' and value 'ok'."},
                ],
                response_format={"type": "json_object"},
            )

            st.success(f"✅ Connection successful! API is responding.")

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                st.error("❌ Authentication failed. Check your API key.")
            elif "429" in error_msg:
                st.warning("⚠️ Connection works but rate limited. Wait a moment and try again.")
            elif "timeout" in error_msg.lower():
                st.error("❌ Connection timed out. Check your endpoint URL.")
            else:
                st.error(f"❌ Connection failed: {error_msg[:200]}")


def _handle_json_upload(uploaded_file: BytesIO) -> None:
    """Handle uploaded JSON file parsing."""
    with st.spinner("Parsing tickets..."):
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
            set_success(f"Loaded {len(tickets)} tickets")

        except json.JSONDecodeError as e:
            set_error(f"Invalid JSON: {e}")
        except Exception as e:
            set_error(f"Error processing file: {e}")


def _handle_pdf_upload(uploaded_file: BytesIO) -> None:
    """Handle uploaded PDF file parsing."""
    with st.spinner("Parsing PDF..."):
        try:
            # Parse PDF
            parser = PDFParser()
            ticket = parser.parse_bytes(uploaded_file)

            if ticket is None:
                set_error("Could not extract ticket data from PDF. Ensure it's a ServiceNow incident report.")
                return

            # Validate we have minimum data
            if not ticket.number:
                set_error("PDF does not contain a valid ticket number")
                return

            update_state(tickets=[ticket], results=None, summary=None)
            set_success(f"Loaded ticket {ticket.number} from PDF")

        except Exception as e:
            set_error(f"Error processing PDF: {e}")


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

    # Handle different formats - wrap in dict with 'records' key if needed
    if isinstance(data, dict):
        if "records" in data or "result" in data:
            # Already in expected format
            pass
        else:
            # Single record - wrap it
            data = {"records": [data]}
    elif isinstance(data, list):
        # List of records - wrap it
        data = {"records": data}

    try:
        return parser.parse_json(data)
    except Exception:
        return []
