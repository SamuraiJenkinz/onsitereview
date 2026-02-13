# Codebase Structure

**Analysis Date:** 2026-02-13

## Directory Layout

```
TQRS/
├── src/tqrs/                    # Main package (importable as `import tqrs`)
│   ├── __init__.py              # Package exports (models, parsing, rules, llm, scoring)
│   │
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py          # Pydantic Settings for env vars and .env
│   │
│   ├── models/                  # Data models (Pydantic BaseModel)
│   │   ├── __init__.py
│   │   ├── ticket.py            # ServiceNowTicket (parsed incident record)
│   │   ├── evaluation.py        # EvaluationResult, CriterionScore, PerformanceBand, TemplateType
│   │   └── rubric.py            # Scoring rubrics and criteria definitions
│   │
│   ├── parser/                  # Input parsers
│   │   ├── __init__.py
│   │   ├── servicenow.py        # ServiceNowParser (JSON export → tickets)
│   │   └── pdf.py               # PDF parser for single tickets
│   │
│   ├── rules/                   # Deterministic rule-based evaluation
│   │   ├── __init__.py
│   │   ├── base.py              # RuleResult, RuleEvaluator protocol
│   │   ├── evaluator.py         # RulesEvaluator (orchestrator for all rules)
│   │   ├── short_description.py # ShortDescriptionValidator (format check)
│   │   ├── category.py          # CategoryValidator (category/subcategory/service/ci checks)
│   │   ├── validation.py        # ValidationDetector (identifies validation docs)
│   │   └── critical_process.py  # CriticalProcessDetector (password/critical checks)
│   │
│   ├── llm/                     # LLM-based evaluation
│   │   ├── __init__.py
│   │   ├── client.py            # OpenAIClient (API abstraction with retry logic)
│   │   ├── evaluator.py         # LLMEvaluator (orchestrator for all LLM evaluations)
│   │   ├── prompts.py           # Prompt templates (DescriptionPrompt, TroubleshootingPrompt, etc.)
│   │   ├── schemas.py           # Response validation schemas (DescriptionEvaluation, etc.)
│   │   └── batch.py             # Batch API support for LLM requests
│   │
│   ├── scoring/                 # Score calculation and aggregation
│   │   ├── __init__.py
│   │   ├── evaluator.py         # TicketEvaluator (main facade, coordinates rules+llm+calc)
│   │   ├── calculator.py        # ScoringCalculator (aggregates results, applies deductions)
│   │   ├── formatter.py         # ResultFormatter (raw results → CriterionScore objects)
│   │   ├── templates.py         # Template-specific criteria and max points
│   │   └── batch.py             # BatchTicketEvaluator (process multiple tickets + progress)
│   │
│   ├── reports/                 # Report generation
│   │   ├── __init__.py
│   │   ├── generator.py         # ReportGenerator (Jinja2-based HTML/JSON/CSV)
│   │   └── templates/           # Jinja2 HTML templates (batch_report.html, individual_report.html, etc.)
│   │
│   └── ui/                      # Streamlit web application
│       ├── __init__.py
│       ├── app.py               # Main entry point (@st.cache_resource decorated components)
│       ├── state.py             # AppState dataclass + state management functions
│       └── components/          # Modular UI sections
│           ├── __init__.py
│           ├── upload.py        # render_upload_section() - file upload and config
│           ├── analytics.py     # render_analytics_section() - charts and statistics
│           ├── results.py       # render_results_section() - individual ticket results
│           └── progress.py      # Progress utilities (format_time, BatchProgress display)
│
├── tests/                       # Test suite
│   └── (test files for units, integration, etc.)
│
├── docs/                        # Documentation
│   └── (README.md, guides, etc.)
│
├── .planning/codebase/          # GSD planning documents (THIS LOCATION)
│   ├── ARCHITECTURE.md          # Architecture and layers
│   ├── STRUCTURE.md             # This file
│   ├── CONVENTIONS.md           # Coding conventions
│   └── TESTING.md               # Testing patterns
│
└── (root config files: pyproject.toml, requirements.txt, .env, etc.)
```

## Directory Purposes

**`src/tqrs/`:**
- Purpose: Main package implementing the ticket evaluation system
- Contains: All business logic, models, parsers, rules, LLM integration, scoring, UI
- Key files: `__init__.py` exports public API

**`src/tqrs/config/`:**
- Purpose: Configuration management
- Contains: Pydantic Settings for environment variables and .env file loading
- Key files: `settings.py` with cached get_settings() function

**`src/tqrs/models/`:**
- Purpose: Data models and type definitions
- Contains: Pydantic BaseModel classes for type safety and validation
- Key files:
  - `ticket.py`: ServiceNowTicket with 50+ fields including identifiers, timestamps, content, business context, flags
  - `evaluation.py`: EvaluationResult (final scores), CriterionScore (individual criterion), PerformanceBand (color bands), TemplateType (evaluation types)
  - `rubric.py`: Scoring rubric definitions

**`src/tqrs/parser/`:**
- Purpose: Parse external ticket formats into ServiceNowTicket objects
- Contains: ServiceNow JSON export parser, PDF single-ticket parser
- Key files: `servicenow.py` handles "records" array in exported JSON, datetime parsing, LoB extraction

**`src/tqrs/rules/`:**
- Purpose: Deterministic, rule-based evaluation logic
- Contains: Concrete validators for format, category, validation status, critical processes
- Key files:
  - `evaluator.py`: RulesEvaluator orchestrator (dispatcher for all rules)
  - `base.py`: RuleResult (unified result container), RuleEvaluator protocol
  - Individual validators: short_description.py, category.py, validation.py, critical_process.py

**`src/tqrs/llm/`:**
- Purpose: GPT-based evaluation for subjective quality assessment
- Contains: OpenAI API abstraction, LLM orchestration, prompts, response schemas
- Key files:
  - `evaluator.py`: LLMEvaluator orchestrator (runs template-specific evaluations)
  - `client.py`: OpenAIClient with retry logic, supports both OpenAI and Azure OpenAI
  - `prompts.py`: Prompt templates (Description, Troubleshooting, Resolution, CustomerService, SpellingGrammar)
  - `schemas.py`: Pydantic schemas for LLM responses

**`src/tqrs/scoring/`:**
- Purpose: Combine rule and LLM results into final 70-point scores
- Contains: Score calculation, result formatting, batch processing with progress tracking
- Key files:
  - `evaluator.py`: TicketEvaluator (main facade - coordinates rules+llm+calculator)
  - `calculator.py`: ScoringCalculator (sums scores, applies deductions, checks auto-fail)
  - `formatter.py`: ResultFormatter (converts raw RuleResult to CriterionScore with evidence)
  - `templates.py`: Scoring criteria per template (which criteria, max points)
  - `batch.py`: BatchTicketEvaluator (process multiple, progress tracking)

**`src/tqrs/reports/`:**
- Purpose: Generate exportable reports in multiple formats
- Contains: HTML report generation via Jinja2, JSON/CSV helpers
- Key files: `generator.py` with ReportGenerator class, `templates/` directory for Jinja2 templates

**`src/tqrs/ui/`:**
- Purpose: Streamlit web application
- Contains: Main app entry point, session state management, modular components
- Key files:
  - `app.py`: Main Streamlit entry point (main() function)
  - `state.py`: AppState dataclass + session state helpers (get_state, update_state, set_error, set_success)
  - `components/upload.py`: File upload section with template selection
  - `components/analytics.py`: Charts and statistics visualization
  - `components/results.py`: Individual ticket result display and filtering

**`tests/`:**
- Purpose: Test suite for units, integration, E2E
- Contains: pytest test files matching source structure

**`docs/`:**
- Purpose: User and developer documentation
- Contains: README, deployment guides, API documentation

## Key File Locations

**Entry Points:**

- `src/tqrs/ui/app.py`: Streamlit web UI entry point (run via `streamlit run src/tqrs/ui/app.py`)
- `src/tqrs/scoring/evaluator.py:TicketEvaluator.create()`: Programmatic library entry point
- `src/tqrs/__init__.py`: Package public API (imports core classes)

**Configuration:**

- `src/tqrs/config/settings.py`: Environment variable and .env configuration
- `.env`: Local development credentials (not committed)
- `pyproject.toml`: Project metadata, dependencies, build config

**Core Logic:**

- `src/tqrs/scoring/evaluator.py`: TicketEvaluator (main orchestrator)
- `src/tqrs/rules/evaluator.py`: RulesEvaluator (rules dispatch)
- `src/tqrs/llm/evaluator.py`: LLMEvaluator (LLM dispatch)
- `src/tqrs/scoring/calculator.py`: ScoringCalculator (score aggregation)

**Data Models:**

- `src/tqrs/models/ticket.py`: ServiceNowTicket
- `src/tqrs/models/evaluation.py`: EvaluationResult, PerformanceBand, TemplateType
- `src/tqrs/rules/base.py`: RuleResult

**Parsing:**

- `src/tqrs/parser/servicenow.py`: ServiceNowParser (JSON → tickets)
- `src/tqrs/parser/pdf.py`: PDF → single ticket

**UI Components:**

- `src/tqrs/ui/app.py`: Main app and view rendering
- `src/tqrs/ui/state.py`: Session state management
- `src/tqrs/ui/components/*.py`: Modular sections (upload, analytics, results, progress)

**Reporting:**

- `src/tqrs/reports/generator.py`: HTML/JSON/CSV export
- `src/tqrs/reports/templates/*.html`: Jinja2 HTML templates

## Naming Conventions

**Files:**

- Module files: lowercase_with_underscores (e.g., `short_description.py`, `servicenow.py`)
- Main files: `app.py` (Streamlit), `client.py` (API clients), `evaluator.py` (orchestrators)
- Template files: snake_case in `templates/` directory (e.g., `batch_report.html`)

**Directories:**

- Functional grouping: lowercase plural or singular (e.g., `models/`, `parser/`, `rules/`, `llm/`, `scoring/`)
- Component subdirectory: `components/` for modular UI pieces

**Classes:**

- PascalCase (e.g., `ServiceNowTicket`, `RuleResult`, `TicketEvaluator`, `BatchTicketEvaluator`)
- Evaluator suffix for orchestrators (e.g., `RulesEvaluator`, `LLMEvaluator`, `TicketEvaluator`)
- Validator/Detector suffix for rule classes (e.g., `ShortDescriptionValidator`, `ValidationDetector`)

**Functions:**

- snake_case (e.g., `get_state()`, `evaluate_ticket()`, `calculate_score()`)
- Prefix patterns: `get_*` (accessor), `is_*` (boolean), `has_*` (boolean), `evaluate_*` (core logic), `render_*` (UI)

**Constants:**

- UPPER_CASE for module-level constants (e.g., `PASS_THRESHOLD_PERCENTAGE`, `SERVICENOW_DATETIME_FORMAT`)
- snake_case for configuration objects (e.g., `retry_delays`)

**Enum Members:**

- UPPER_SNAKE_CASE for enum values (e.g., `INCIDENT_LOGGING`, `BLUE`, `PASS_THRESHOLD_PERCENTAGE`)
- String values: lowercase_snake_case (e.g., `incident_logging`, `blue`)

## Where to Add New Code

**New Rule/Validator:**
- File: `src/tqrs/rules/{rule_name}.py`
- Class: Inherit from or implement RuleEvaluator protocol
- Return: RuleResult with criterion_id matching scoring template
- Register: Add import and dispatch in `src/tqrs/rules/evaluator.py:RulesEvaluator`

**New LLM Evaluation:**
- File: `src/tqrs/llm/evaluator.py` (method) + `src/tqrs/llm/prompts.py` (prompt) + `src/tqrs/llm/schemas.py` (schema)
- Pattern: Create PromptName class in prompts.py, ResponseName schema in schemas.py, evaluate_type() method in evaluator.py
- Return: RuleResult via self._to_rule_result()
- Register: Add to TEMPLATE_EVALUATIONS dict in LLMEvaluator.__init__

**New Scoring Template:**
- File: `src/tqrs/scoring/templates.py`
- Pattern: Add TemplateType enum value in `models/evaluation.py`, add criteria list to TEMPLATE_CRITERIA
- Register: Add dispatch in `src/tqrs/rules/evaluator.py` for rules and `src/tqrs/llm/evaluator.py` for LLM evaluations

**New UI Component:**
- File: `src/tqrs/ui/components/{component_name}.py`
- Function: render_{component_name}() or setup_{component_name}()
- Pattern: Use st.* functions for UI rendering, get/update AppState for data
- Register: Import and call in `src/tqrs/ui/app.py` main layout sections

**New Report Format:**
- File: `src/tqrs/reports/generator.py` (method) + `src/tqrs/reports/templates/{format_name}.{ext}`
- Pattern: Add generate_{format}_report() method, use Jinja2 for HTML or format strings for CSV/JSON
- Register: Add to export section in `src/tqrs/ui/app.py:render_export_section()`

**New Parser:**
- File: `src/tqrs/parser/{format_name}.py`
- Class: Named {Format}Parser
- Return: List[ServiceNowTicket]
- Register: Import in `src/tqrs/parser/__init__.py` and UI upload component

**Utilities:**
- Shared helpers: `src/tqrs/utils/` (create if not exists)
- Constants/enums: Keep in `models/` or create `src/tqrs/constants.py`
- Formatters: Add to `src/tqrs/scoring/formatter.py` if scoring-related

## Special Directories

**`src/tqrs/llm/schemas.py`:**
- Purpose: Pydantic response schemas for LLM outputs
- Generated: No (manually written for type safety)
- Committed: Yes (part of source)
- Pattern: Each evaluation type has schema (DescriptionEvaluation, TroubleshootingEvaluation, etc.)

**`src/tqrs/reports/templates/`:**
- Purpose: Jinja2 HTML templates for report generation
- Generated: No (hand-authored)
- Committed: Yes (part of source)
- Pattern: Templates use context passed from ReportGenerator (results, summary, metadata)

**`.planning/codebase/`:**
- Purpose: GSD planning documents for orchestrator
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes (should commit for team reference)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**`tests/`:**
- Purpose: Test suite
- Generated: No (manually written)
- Committed: Yes (part of source)
- Pattern: Mirror src/tqrs structure for organization

**`docs/`:**
- Purpose: User and developer documentation
- Generated: Partially (some auto-docs from docstrings)
- Committed: Yes
- Contains: README, deployment guides, user guides, API docs

---

*Structure analysis: 2026-02-13*
