# Technology Stack

**Analysis Date:** 2026-02-13

## Languages

**Primary:**
- Python 3.11+ - Primary language for entire application
- HTML/CSS/JavaScript - Streamlit-generated UI rendering

**Secondary:**
- JSON - ServiceNow export format and data interchange
- PowerShell - Windows service deployment scripts
- Markdown - Documentation

## Runtime

**Environment:**
- Python 3.11+ (verified in `pyproject.toml`: requires-python = ">=3.11")

**Package Manager:**
- pip (via `requirements.txt` and `pyproject.toml`)
- Lockfile: Not present (using pinned versions in `pyproject.toml`)

## Frameworks

**Core:**
- Streamlit 1.30+ - Web UI framework for interactive data applications
- Pydantic 2.0+ - Data validation and settings management (BaseModel, BaseSettings)
- pydantic-settings 2.0+ - Configuration management from environment variables

**Testing:**
- pytest 8.0+ - Test runner framework
- pytest-cov 4.0+ - Code coverage reporting

**Build/Dev:**
- hatchling - Build backend (configured in `pyproject.toml`)
- ruff 0.1+ - Code linter and formatter
- python-dotenv 1.0+ - Environment variable loading from `.env` files

## Key Dependencies

**Critical:**
- openai 1.0+ - OpenAI API client (ChatGPT, GPT-4o models)
  - Supports both standard OpenAI and Azure OpenAI endpoints
  - Handles JSON streaming responses and structured output format
  - Built-in retry logic for rate limits and API errors

- streamlit 1.30+ - Web framework for building interactive dashboards
  - Session state management for app data persistence
  - File upload handling (JSON, PDF)
  - Charts and progress indicators via Plotly integration

**Infrastructure:**
- jinja2 3.0+ - HTML template rendering for report generation
- plotly 5.0+ - Interactive charts and visualizations for analytics dashboard
- pdfplumber 0.10+ - PDF parsing for single-ticket PDF uploads
- httpx - HTTP client for custom header handling (corporate proxy support)

## Configuration

**Environment:**
- Configuration via Pydantic Settings (`src/tqrs/config/settings.py`)
- Loads from `.env` file (case-insensitive, extra fields ignored)
- Two credential modes: direct OpenAI API key OR Azure OpenAI endpoint + deployment

**Build:**
- `pyproject.toml` - Project metadata, dependencies, tool configuration
- `ruff` settings: target Python 3.12, 100-char line length
- `pytest` settings: testpaths=["tests"], pythonpath=["src"]

**Key Configuration Files:**
- `.env` (user-created from `envexample`) - Runtime credentials
- `envexample` - Template showing required environment variables
- `src/tqrs/config/settings.py` - Pydantic Settings class with validation

## Platform Requirements

**Development:**
- Windows 10+ or Linux/macOS with Python 3.11+
- 200MB disk space for venv and dependencies
- Network access to OpenAI or Azure OpenAI APIs

**Production:**
- Windows Server 2016+ (deployment via PowerShell scripts)
- Can run as Windows Service via `setup_service.ps1`
- Alternative: Docker container (not configured)
- Network access to OpenAI/Azure OpenAI for LLM inference
- Streaming web server via Streamlit (built-in Tornado-based server)

## Environment Variables

**Required (one of these credential sets):**
- `OPENAI_API_KEY` - Direct OpenAI API key (for OpenAI provider)
- `TQRS_AZURE_OPENAI_ENDPOINT` - Azure resource URL (for Azure provider)
- `TQRS_AZURE_OPENAI_API_KEY` - Azure API key (for Azure provider)
- `TQRS_AZURE_OPENAI_DEPLOYMENT` - Azure model deployment name (for Azure provider)

**Optional:**
- `OPENAI_BASE_URL` - Custom API endpoint (for Enterprise OpenAI)
- `OPENAI_MODEL` - Model name (default: gpt-4o)
- `OPENAI_TEMPERATURE` - Sampling temperature (default: 0.1)
- `OPENAI_MAX_TOKENS` - Max response tokens (default: 2000)
- `OPENAI_TIMEOUT` - Request timeout seconds (default: 30)
- `OPENAI_MAX_RETRIES` - Retry attempts (default: 3)
- `BATCH_SIZE` - Tickets per batch (default: 50)
- `BATCH_CONCURRENCY` - Parallel LLM requests (default: 5)
- `LOG_LEVEL` - Logging level (default: INFO)
- `TQRS_AZURE_OPENAI_API_VERSION` - Azure API version (default: 2024-02-15-preview)

## Dependency Management

**Direct Dependencies (Production):**
- `pydantic>=2.0` - Data models and validation
- `pydantic-settings>=2.0` - Configuration management
- `openai>=1.0` - LLM API client
- `streamlit>=1.30` - Web UI framework
- `jinja2>=3.0` - HTML template rendering
- `plotly>=5.0` - Interactive charts
- `python-dotenv>=1.0` - Environment loading
- `pdfplumber>=0.10` - PDF parsing

**Development Dependencies:**
- `pytest>=8.0` - Test framework
- `pytest-cov>=4.0` - Coverage reporting
- `ruff>=0.1` - Code quality (linting + formatting)

**Transitive Dependencies:**
- `httpx` - HTTP client (used by `openai` SDK)
- Tornado (via Streamlit) - Web server backend

---

*Stack analysis: 2026-02-13*
