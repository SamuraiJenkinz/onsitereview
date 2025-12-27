# Roadmap: TQRS - Ticket Quality Review System

## Overview

TQRS transforms manual ticket quality reviews into an AI-powered automated workflow. The journey goes from data parsing through hybrid evaluation (rules + LLM) to a polished Streamlit interface with professional HTML reports. Each phase builds on the previous, with the core evaluation logic established before UI work begins.

## Domain Expertise

None - standard Python/Streamlit patterns apply.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Project setup, JSON parser, data models
- [x] **Phase 2: Rules Engine** - Deterministic evaluations (40% of scoring)
- [x] **Phase 3: LLM Evaluator** - OpenAI integration for nuanced assessments (60%)
- [x] **Phase 4: Scoring Engine** - Score calculation, bands, pass/fail logic
- [x] **Phase 5: Streamlit UI** - Web interface with upload, progress, analytics
- [x] **Phase 6: Reporting** - HTML reports with coaching recommendations

## Phase Details

### Phase 1: Foundation
**Goal**: Establish project structure, parse ServiceNow JSON, define data models
**Depends on**: Nothing (first phase)
**Research**: Unlikely (standard Python patterns)
**Plans**: 1 (01-01-PLAN.md)

Key deliverables:
- Project scaffolding (pyproject.toml, src/ structure)
- ServiceNow JSON parser with field extraction/normalization
- Pydantic data models for tickets and evaluations
- Configuration management (environment variables, settings)
- Validate against prototype_samples.json

### Phase 2: Rules Engine
**Goal**: Implement deterministic evaluation rules (40% of total scoring)
**Depends on**: Phase 1
**Research**: Unlikely (regex, string parsing - established patterns)
**Plans**: 1 (02-01-PLAN.md)

Key deliverables:
- Short description 4-part format validator ([LoB] - [Location] - [App] - [Brief])
- Validation pattern detection (OKTA Push, phone validation, guest chat templates)
- Category/subcategory validation logic
- Critical process detection (password reset, VIP, lost/stolen, etc.)
- Line of Business extraction from boolean flags or short description

### Phase 3: LLM Evaluator
**Goal**: Integrate OpenAI for nuanced quality assessments (60% of scoring)
**Depends on**: Phase 2
**Research**: Likely (new API integration)
**Research topics**: OpenAI Python SDK, structured output JSON schemas, GPT-4o vs GPT-4-turbo accuracy/cost, rate limit handling
**Plans**: 1 (03-01-PLAN.md)

Key deliverables:
- OpenAI API client with retry logic
- Structured output schema for evaluation responses
- Prompt templates for each evaluation criterion:
  - Description accuracy/completeness (20 pts)
  - Troubleshooting quality (20 pts)
  - Resolution notes assessment (15 pts)
  - Customer service quality (20 pts)
  - Spelling/grammar (2 pts)
- Response parsing and validation
- Error handling for API failures

### Phase 4: Scoring Engine
**Goal**: Calculate final scores, apply deductions, assign performance bands
**Depends on**: Phase 3
**Research**: Unlikely (pure business logic from specification)
**Plans**: TBD

Key deliverables:
- 70-point score calculation per template
- Deduction logic:
  - Validation: PASS / -15 / FAIL
  - Critical Process: PASS / -35 / FAIL (automatic 0 for password violations)
- Performance band assignment (BLUE ≥95%, GREEN ≥90%, YELLOW ≥75%, RED ≥50%, PURPLE <50%)
- Pass/fail determination (90% = 63/70 threshold)
- Template-specific scoring (Incident Logging, Handling, Customer Service)

### Phase 5: Streamlit UI
**Goal**: Build web interface for upload, processing, and viewing results
**Depends on**: Phase 4
**Research**: Likely (Streamlit patterns)
**Research topics**: Streamlit file upload handling, progress tracking patterns, session state management, batch processing UX
**Plans**: TBD

Key deliverables:
- JSON file upload interface
- Template selection (Incident Logging / Handling / Customer Service)
- Real-time progress tracking (progress bars, status messages)
- Individual ticket result viewing
- Batch analytics dashboard:
  - Score distribution charts
  - Pass/fail rates
  - Common issues breakdown
- Export functionality

### Phase 6: Reporting
**Goal**: Generate professional HTML reports with coaching recommendations
**Depends on**: Phase 5
**Research**: Unlikely (Jinja2 templating - established patterns)
**Plans**: TBD

Key deliverables:
- Jinja2 HTML templates with Tailwind CSS (CDN)
- Score gauge visualization (Plotly.js)
- Criterion-by-criterion breakdown:
  - Score vs max points
  - Evidence quotes from ticket
  - Reasoning for score
  - Specific coaching recommendations
- Strengths and improvements summary
- Batch summary report
- HTML download functionality

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2025-12-26 |
| 2. Rules Engine | 1/1 | Complete | 2025-12-26 |
| 3. LLM Evaluator | 1/1 | Complete | 2025-12-26 |
| 4. Scoring Engine | 1/1 | Complete | 2025-12-26 |
| 5. Streamlit UI | 1/1 | Complete | 2025-12-26 |
| 6. Reporting | 1/1 | Complete | 2025-12-26 |
