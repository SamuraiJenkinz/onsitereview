# External Integrations

**Analysis Date:** 2026-02-13

## APIs & External Services

**Large Language Models:**
- OpenAI (GPT-4o) - Primary LLM for ticket quality evaluation
  - SDK/Client: `openai>=1.0` package via `src/tqrs/llm/client.py`
  - Auth: `OPENAI_API_KEY` environment variable
  - Features: Structured output (JSON mode), streaming, token usage tracking
  - Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s delays)
  - Price tracking: Calculates estimated cost ($2.50/1M input tokens, $10/1M output tokens)

- Azure OpenAI - Alternative LLM provider (enterprise)
  - SDK/Client: `AzureOpenAI` from `openai` package
  - Auth: `TQRS_AZURE_OPENAI_ENDPOINT`, `TQRS_AZURE_OPENAI_API_KEY`, `TQRS_AZURE_OPENAI_DEPLOYMENT`
  - Features: Supports corporate proxy authentication with X-Api-Key headers
  - API Version: Configurable (default: 2024-02-15-preview)

## Data Storage

**Databases:**
- None - This is a stateless analysis application
- No persistence layer: Evaluation results are in-memory during session or exported to files
- Session state: Stored in Streamlit session memory (not persistent between restarts)

**File Storage:**
- Local filesystem only - No cloud storage integration
- Input sources: JSON files (ServiceNow export), PDF files (single tickets)
- Output files: JSON, CSV, HTML reports saved to local disk
- Temporary storage: Uses system temp directory (`tempfile.gettempdir()`)

**Caching:**
- None detected - No Redis, Memcached, or external caching service
- In-memory caching: Settings cached via `@lru_cache` decorator (`src/tqrs/config/settings.py`)

## Authentication & Identity

**Auth Provider:**
- None - Application does not manage user authentication
- API key-based auth only: OpenAI or Azure OpenAI credentials passed by end-user or configured via environment
- Server-side credentials: Optional environment variables for Windows Server deployment
- Admin override: Query parameter `?admin=true` for temporary credential override (development)

**Credential Storage:**
- Development: `.env` file (template: `envexample`)
- Production: Windows environment variables set via `configure_credentials.ps1` script
- No credential management service (AWS Secrets Manager, Azure Key Vault, etc.)

## Monitoring & Observability

**Error Tracking:**
- None detected - No external error tracking service (Sentry, DataDog, etc.)
- Logging: Python standard `logging` module configured to INFO level
- Log output: Streamed to console/Streamlit stdout

**Logs:**
- Local logging only via Python `logging` module
- Levels: DEBUG, INFO, WARNING, ERROR (configurable via `LOG_LEVEL`)
- Output: Printed to application stdout (accessible via Streamlit logs)

## CI/CD & Deployment

**Hosting:**
- Local development: `streamlit run src/tqrs/ui/app.py` (default port 8501)
- Windows Server: Windows Service via `setup_service.ps1`
- No cloud hosting detected (AWS, Azure, GCP)
- No Docker support (no Dockerfile present)

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, Jenkins, or other CI/CD
- Manual deployment via PowerShell scripts
- Git repository: GitHub (referenced in README as `https://github.com/mmctech/IncidentReviews.git`)

## Environment Configuration

**Required env vars:**
- One of:
  - `OPENAI_API_KEY` (for direct OpenAI)
  - `TQRS_AZURE_OPENAI_ENDPOINT`, `TQRS_AZURE_OPENAI_API_KEY`, `TQRS_AZURE_OPENAI_DEPLOYMENT` (for Azure)

**Optional env vars:**
- `OPENAI_BASE_URL` - Custom OpenAI Enterprise endpoint
- `OPENAI_MODEL` - Model name (default: gpt-4o)
- `OPENAI_TEMPERATURE` - Sampling temperature (default: 0.1)
- `OPENAI_MAX_TOKENS` - Max response tokens (default: 2000)
- `OPENAI_TIMEOUT` - Request timeout in seconds (default: 30)
- `OPENAI_MAX_RETRIES` - Retry attempts (default: 3)
- `BATCH_SIZE` - Tickets per batch (default: 50)
- `BATCH_CONCURRENCY` - Parallel LLM requests (default: 5)
- `LOG_LEVEL` - Logging level (default: INFO)
- `TQRS_AZURE_OPENAI_API_VERSION` - Azure API version (default: 2024-02-15-preview)

**Secrets location:**
- Development: `.env` file in project root
- Production (Windows Server): System environment variables (set via `configure_credentials.ps1`)
- No secrets manager integration (AWS Secrets Manager, Azure Key Vault, Vault, etc.)

## Webhooks & Callbacks

**Incoming:**
- None detected - No webhook endpoints for external services

**Outgoing:**
- None detected - No callbacks or events sent to external systems
- No ServiceNow API integration detected - System only reads ServiceNow JSON exports (offline)

## Data Format Integrations

**ServiceNow JSON Export:**
- Parser: `src/tqrs/parser/servicenow.py`
- Format: `{"records": [{...ticket fields...}]}`
- Required fields: `number`, `category`, `subcategory`, `short_description`, `description`, `close_notes`
- Encoding: UTF-8

**PDF Parsing:**
- Parser: `src/tqrs/parser/pdf.py`
- Library: `pdfplumber>=0.10`
- Use case: Single ticket PDF uploads as alternative to JSON

## Transport & Protocols

**HTTP/HTTPS:**
- Standard HTTPS for OpenAI API calls (automatic via `openai` package)
- Azure OpenAI: Supports corporate proxy with X-Api-Key header authentication
- Streamlit server: HTTP by default (port 8501 for development, configurable for Windows Service)

**Network Requirements:**
- Outbound HTTPS to api.openai.com (OpenAI)
- Outbound HTTPS to Azure OpenAI endpoint (if Azure provider selected)
- Inbound HTTP on configured port (Streamlit web interface)

## Integration Patterns

**Pull-based Integration:**
- ServiceNow data: Manual export from ServiceNow → JSON file → uploaded to TQRS
- No push/pull webhooks
- No continuous data synchronization

**Stateless Processing:**
- Each ticket evaluation is independent
- No cross-ticket state or session data
- Results generated per batch, exported to files

**Batch Processing:**
- Default batch size: 50 tickets
- Concurrency: Up to 5 parallel LLM requests (configurable)
- Progress tracking with time estimation

---

*Integration audit: 2026-02-13*
