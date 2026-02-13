# Architecture

**Analysis Date:** 2026-02-13

## Pattern Overview

**Overall:** Modular pipeline architecture with layered evaluation orchestration

**Key Characteristics:**
- Multi-stage evaluation pipeline combining deterministic rules and LLM-based assessment
- Clean separation between data models, business logic, and UI layers
- Pluggable evaluation engines (rules-based and LLM-based) unified through scoring layer
- Template-driven criteria system allowing multiple evaluation templates (Incident Logging, Incident Handling, Customer Service)
- Structured streaming of results with progress tracking for batch operations

## Layers

**Data Layer:**
- Purpose: Pydantic-based data models for tickets, evaluations, and results
- Location: `src/tqrs/models/`
- Contains: `ticket.py` (ServiceNowTicket), `evaluation.py` (EvaluationResult, PerformanceBand, TemplateType), `rubric.py`
- Depends on: Pydantic, Python stdlib
- Used by: All other layers

**Input/Parser Layer:**
- Purpose: Convert external formats (ServiceNow JSON, PDF) into internal ticket models
- Location: `src/tqrs/parser/`
- Contains: `servicenow.py` (ServiceNowParser), `pdf.py`
- Depends on: Data Layer (ServiceNowTicket)
- Used by: UI layer for data import

**Rules Engine Layer:**
- Purpose: Deterministic, code-based evaluation rules for concrete validation checks
- Location: `src/tqrs/rules/`
- Contains: `base.py` (RuleResult, RuleEvaluator), `evaluator.py` (RulesEvaluator - orchestrator), `short_description.py`, `category.py`, `validation.py`, `critical_process.py`
- Pattern: Each rule class inherits from RuleEvaluator protocol, returns RuleResult
- Depends on: Data Layer (ServiceNowTicket, TemplateType)
- Used by: Scoring Layer (TicketEvaluator)
- Note: Always runs, provides baseline scores and deductions

**LLM Evaluation Layer:**
- Purpose: GPT-based subjective evaluation for content quality (description, troubleshooting, resolution, tone)
- Location: `src/tqrs/llm/`
- Contains: `client.py` (OpenAIClient - API abstraction), `evaluator.py` (LLMEvaluator - orchestrator), `prompts.py` (prompt templates), `schemas.py` (Pydantic response schemas), `batch.py` (batch processing)
- Pattern: Prompt-schema pairs for each evaluation type (Description, Troubleshooting, Resolution, CustomerService, SpellingGrammar)
- Depends on: Data Layer (ServiceNowTicket, TemplateType), `openai` library
- Used by: Scoring Layer (TicketEvaluator)
- Note: Optional but recommended; returns RuleResult objects for unified scoring

**Scoring/Calculation Layer:**
- Purpose: Combines rules and LLM results into final 70-point scores with deductions and performance bands
- Location: `src/tqrs/scoring/`
- Contains:
  - `calculator.py` (ScoringCalculator - score aggregation, deduction logic, auto-fail detection)
  - `evaluator.py` (TicketEvaluator - main orchestrator, coordinates rules + LLM + calculator)
  - `formatter.py` (ResultFormatter - converts raw results to CriterionScore objects with evidence/reasoning)
  - `templates.py` (scoring criteria templates per template type)
  - `batch.py` (BatchTicketEvaluator - processes multiple tickets with progress tracking)
- Pattern: TicketEvaluator is the main facade; creates evaluation pipeline and returns EvaluationResult
- Depends on: Data Layer, Rules Layer, LLM Layer
- Used by: UI layer, batch processing

**Configuration Layer:**
- Purpose: Centralized environment-based configuration for API keys, model selection, Azure setup
- Location: `src/tqrs/config/`
- Contains: `settings.py` (Settings - Pydantic Settings for .env and env vars)
- Depends on: `pydantic_settings`, `python-dotenv`
- Used by: UI layer for credential management

**Reporting Layer:**
- Purpose: Generate HTML/JSON/CSV exports of evaluation results
- Location: `src/tqrs/reports/`
- Contains: `generator.py` (ReportGenerator - Jinja2 templating), `templates/` (HTML templates)
- Depends on: `jinja2`, Data Layer (EvaluationResult)
- Used by: UI layer for export functionality

**UI Layer:**
- Purpose: Streamlit web application for interactive ticket upload, evaluation, result visualization
- Location: `src/tqrs/ui/`
- Contains:
  - `app.py` (main Streamlit entry point)
  - `state.py` (AppState - session state management)
  - `components/` (modular UI sections: upload.py, analytics.py, results.py, progress.py)
- Pattern: Component-based architecture; state isolated in AppState dataclass
- Depends on: All other layers (models, parser, scoring, reports)
- Used by: End users via web browser

## Data Flow

**Evaluation Pipeline:**

1. **Data Input** (UI.upload → Parser) - User uploads ServiceNow JSON or PDF
   - File → ServiceNowParser.parse_file/parse_json → List[ServiceNowTicket]
   - Tickets stored in AppState.tickets

2. **Configuration** (UI → AppState) - User configures API credentials
   - AppState holds api_key, use_azure, azure_endpoint, etc.
   - Settings.azure_credentials_configured checks for server-side env vars

3. **Evaluation Request** (UI.app → Scoring.TicketEvaluator.create) - User clicks "Start"
   - TicketEvaluator.create() with api_key → creates OpenAIClient → creates LLMEvaluator
   - BatchTicketEvaluator wraps TicketEvaluator

4. **Batch Processing** (Scoring.BatchTicketEvaluator.evaluate_batch) - Process all tickets
   - For each ticket:
     - RulesEvaluator.evaluate() → List[RuleResult] (always runs)
     - LLMEvaluator.evaluate_ticket() → List[RuleResult] (conditional on api_key)
     - ScoringCalculator.calculate_score() → ScoringResult (base score + deductions)
     - ResultFormatter.to_criterion_scores() → List[CriterionScore]
     - Build EvaluationResult with metadata
   - ScoringCalculator.generate_summary() → BatchEvaluationSummary

5. **Progress Tracking** - Real-time UI updates via callback
   - BatchTicketEvaluator calls progress_callback(BatchProgress) after each ticket
   - UI updates progress bar, metrics, current ticket display

6. **Result Export** (UI.render_export_section) - Multiple output formats
   - JSON: export_results_json() → downloadable JSON file
   - CSV: export_results_csv() → downloadable CSV summary
   - HTML: ReportGenerator.generate_batch_report() → formatted HTML report

**State Management:**

```
AppState (UI session state)
├── tickets: List[ServiceNowTicket]  # Parsed input
├── results: List[EvaluationResult]  # Evaluation output
├── summary: BatchEvaluationSummary  # Statistics
├── template: TemplateType           # Selected evaluation template
├── api_key/azure_*: credentials     # LLM configuration
├── is_processing: bool              # Processing flag
└── current_progress: BatchProgress  # Real-time progress
```

## Key Abstractions

**ServiceNowTicket:**
- Purpose: Immutable representation of a ServiceNow incident ticket
- Examples: `src/tqrs/models/ticket.py`
- Pattern: Pydantic BaseModel with field validators for type coercion (datetime parsing, LoB detection)
- Properties: is_closed, is_resolved, has_validation for computed checks

**RuleResult:**
- Purpose: Unified result container for any evaluation (rules-based or LLM-based)
- Examples: `src/tqrs/rules/base.py`
- Pattern: Holds criterion_id, score (int or string like "PASS"/"FAIL"/"-15"), evidence, reasoning, coaching
- Properties: is_deduction (negative score), is_auto_fail (FAIL string), numeric_score (coerces string to int)

**EvaluationResult:**
- Purpose: Complete evaluation outcome for a single ticket
- Examples: `src/tqrs/models/evaluation.py`
- Pattern: Aggregates criterion_scores, deductions, auto_fail status, performance band
- Computed Fields: percentage (auto-calculated from total/max), passed (percentage >= 90%)

**TemplateType:**
- Purpose: Enum selecting which evaluation criteria and rules apply
- Examples: INCIDENT_LOGGING, INCIDENT_HANDLING, CUSTOMER_SERVICE
- Pattern: Determines which rules run in RulesEvaluator and which LLM evaluations in LLMEvaluator

**PerformanceBand:**
- Purpose: Color-coded performance classification (Blue 95%+, Green 90%+, Yellow 75%+, Red 50%+, Purple <50%)
- Examples: `src/tqrs/models/evaluation.py`
- Pattern: from_percentage() factory method, css_color property for UI rendering

## Entry Points

**Streamlit UI:**
- Location: `src/tqrs/ui/app.py:main()`
- Triggers: User runs `streamlit run src/tqrs/ui/app.py`
- Responsibilities: Initialize session state, render UI, orchestrate evaluation flow

**Programmatic Evaluation:**
- Location: `src/tqrs/scoring/evaluator.py:TicketEvaluator.create()`
- Triggers: Programmatic import of TQRS library
- Responsibilities: Factory method creating fully configured evaluator, runs evaluate_ticket() for single ticket or get_raw_results() for debugging

**Batch Processing:**
- Location: `src/tqrs/scoring/batch.py:BatchTicketEvaluator.evaluate_batch()`
- Triggers: UI calls with progress callback
- Responsibilities: Loop through tickets, call TicketEvaluator.evaluate_ticket(), track progress, aggregate results

## Error Handling

**Strategy:** Fail-safe with fallback to rules-only when LLM unavailable; track errors in batch results

**Patterns:**

1. **LLM Errors** (client.py) - Retry logic with exponential backoff
   - RateLimitError → sleep and retry up to max_retries times
   - APIConnectionError → exponential backoff with jitter
   - ValidationError → log warning, attempt partial parsing, create zero-score error result

2. **Parser Errors** (servicenow.py) - Skip failed records, log details
   - FileNotFoundError → raised to caller
   - json.JSONDecodeError → raised to caller
   - Individual record parsing fails → log and raise (stops batch)

3. **Scoring Errors** (batch.py) - Continue batch on individual failures
   - Exception during ticket evaluation → append to errors list, increment error count, continue
   - Progress callback still called to update UI

4. **Rules Engine Errors** (rules/) - Return zero-score RuleResult
   - Rule evaluation throws exception → create error result with score=0, evidence="Error: {e}"

## Cross-Cutting Concerns

**Logging:**
- Python stdlib logging configured at module level in each package
- Levels: DEBUG (detailed flow), INFO (major steps), WARNING (recoverable issues), ERROR (failures)
- Example: `logger = logging.getLogger(__name__)` in evaluator.py, logs at DEBUG/INFO/WARNING/ERROR

**Validation:**
- Pydantic models enforce type validation on construction
- ServiceNowTicket validators coerce strings to int/datetime, handle LoB detection
- RuleResult validators ensure score is numeric or recognized string
- LLM response validation via schemas.py Pydantic models

**Configuration:**
- Settings.py loads from .env file and environment variables
- Supports both direct OpenAI API and Azure OpenAI via configuration
- Azure credentials configurable via server-side env vars (TQRS_AZURE_OPENAI_*) or user-entered in UI

**Progress Tracking:**
- BatchProgress dataclass tracks total/completed/current/errors with elapsed/estimated_remaining calculations
- Callback mechanism allows UI to display real-time updates without blocking evaluation
- Used in batch.py evaluate_batch() with progress_callback parameter

---

*Architecture analysis: 2026-02-13*
