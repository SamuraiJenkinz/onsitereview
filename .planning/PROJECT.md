# TQRS - Ticket Quality Review System

## Vision

TQRS is an AI-powered automation system that transforms ServiceNow ticket quality reviews from a tedious, inconsistent manual process into a fast, reliable automated workflow. The system replaces Excel-based reviews where team leads spend 15-25 minutes per ticket, reducing that to under 2 minutes while dramatically improving consistency.

The core insight is that ticket quality assessment is a hybrid problem: about 40% can be handled by deterministic rules (format validation, category matching, validation pattern detection), while 60% requires nuanced judgment that LLMs excel at (troubleshooting quality, customer service tone, coaching recommendations). By combining both approaches, TQRS delivers the speed of automation with the nuance of expert human review.

This isn't just about efficiency - it's about fairness and development. Human reviewers suffer from fatigue bias (tickets reviewed at 4pm score differently than 9am), inconsistency across reviewers, and limited capacity for detailed coaching feedback. TQRS scores every ticket identically and generates specific, actionable coaching recommendations that help analysts improve.

## Problem

The Global Service Desk team manually reviews ServiceNow incident tickets for quality assurance. The current process:

- **Time Sink**: Each ticket takes 15-25 minutes to review manually using Excel templates
- **Inconsistency**: Different reviewers apply criteria differently; reviewer fatigue affects scores
- **Limited Capacity**: Can only review a small sample of tickets, missing quality issues
- **Shallow Coaching**: Generic feedback like "improve documentation" rather than specific guidance
- **Data in Silos**: Quality data locked in Excel files, no trend analysis or team insights

The team has 3,831+ closed tickets to potentially review, but manual processes make comprehensive review impossible. Team leads need to identify patterns, coach analysts effectively, and demonstrate quality metrics - none of which the current process supports well.

## Success Criteria

How we know this worked:

- [ ] Process 50-500 tickets per batch in under 10 minutes total
- [ ] Achieve 88-94% agreement with human reviewer scores on validation set
- [ ] Generate HTML reports with detailed scoring breakdown and coaching recommendations
- [ ] Score identical tickets identically every time (100% consistency)
- [ ] Support all three evaluation templates (Incident Logging, Handling, Customer Service)
- [ ] Provide actionable coaching recommendations for every deduction
- [ ] Display batch analytics (pass rates, common issues, score distributions)

## Scope

### Building

**Core Evaluation Engine**
- ServiceNow JSON parser with field extraction and normalization
- Rules engine for deterministic evaluations (40% of scoring):
  - Short description 4-part format validation
  - Validation pattern detection (OKTA, phone, guest chat templates)
  - Category/subcategory matching
  - Critical process detection
- OpenAI integration for nuanced evaluations (60% of scoring):
  - Troubleshooting quality assessment
  - Resolution notes completeness
  - Customer service quality
  - Description accuracy and completeness
  - Spelling/grammar checking (consolidated with OpenAI, no LanguageTool)

**Scoring System**
- 70-point maximum score calculation
- Deduction logic (validation -15, critical process -35/FAIL)
- Performance band assignment (BLUE/GREEN/YELLOW/RED/PURPLE)
- Pass threshold at 63/70 (90%)

**Three Evaluation Templates**
- Incident Logging (documentation quality focus)
- Incident Handling (troubleshooting and resolution focus)
- Customer Service (soft skills and interaction focus)

**Streamlit Web Application**
- JSON file upload interface
- Template selection
- Real-time progress tracking during batch processing
- Individual ticket report viewing
- Batch analytics dashboard (score distributions, pass rates, common issues)
- HTML report generation and download

**Reporting**
- Professional HTML reports per ticket:
  - Executive summary with score gauge
  - Detailed criterion-by-criterion breakdown
  - Evidence quotes from ticket
  - Specific coaching recommendations
  - Strengths and areas for improvement
- Batch summary reports with analytics

### Not Building

- **Five9 Integration**: Call recording analysis deferred to future phase
- **Direct ServiceNow API**: Using JSON file exports only, no live connection
- **ML Training/Feedback Loop**: No model training on reviewed tickets
- **User Authentication**: Internal network deployment, firewall-protected
- **Multi-tenancy**: Single team deployment
- **Historical Trend Analysis**: Basic batch analytics only, no long-term tracking
- **Analyst Performance Dashboards**: Focus on ticket quality, not analyst metrics

## Context

**Environment**
- Greenfield Python project
- Local/on-prem server deployment
- Internal network access only (no public exposure)
- OpenAI Enterprise API available via API key

**Data Characteristics**
- ServiceNow JSON exports with nested record structure
- ~100 fields per ticket, ~15 relevant for evaluation
- Mix of sys_id references and display values
- Boolean flags as string "true"/"false"
- Timestamps in "YYYY-MM-DD HH:MM:SS" format

**Existing Documentation**
- Comprehensive project specification (CTSS_PROJECT_SPECIFICATION.md)
- Machine-readable scoring rubrics (scoring_rubrics.json)
- 3 validated sample tickets (prototype_samples.json)
- All expected to score 70/70 (100%)

## Constraints

- **API**: Must use OpenAI Enterprise API (not Anthropic Claude as originally spec'd)
- **Deployment**: Local/on-prem server, no cloud services
- **Network**: Internal only, no external auth required
- **Dependencies**: Minimize external service calls - OpenAI handles spelling/grammar (no LanguageTool)
- **Batch Size**: Optimized for 50-500 tickets per batch (medium scale)
- **Python**: Version 3.12+ as specified

## Decisions Made

Key decisions from project exploration:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend Framework | Streamlit | Rapid development, native file upload/progress, data visualization built-in |
| Backend Framework | FastAPI (if needed) | Streamlit handles most needs; FastAPI available for API endpoints |
| LLM Provider | OpenAI Enterprise | Enterprise agreement available, consolidates spelling/grammar |
| Spelling/Grammar | OpenAI (not LanguageTool) | Reduces external dependencies, single API for all LLM needs |
| Authentication | None | Internal network deployment with firewall protection |
| Template Priority | All 3 simultaneously | Templates share 80% logic; build once, configure per template |
| Deployment | Local/on-prem | Data sensitivity, enterprise policy |

## Open Questions

Things to figure out during execution:

- [ ] OpenAI model selection (GPT-4, GPT-4-turbo, GPT-4o) - test accuracy vs cost
- [ ] Optimal batch size for OpenAI rate limits and processing time
- [ ] Caching strategy for repeated evaluations (same ticket, different template)
- [ ] Error handling for API failures mid-batch (retry vs skip vs partial results)
- [ ] ServiceNow taxonomy validation - need actual category/subcategory/service mappings

---
*Initialized: 2025-12-26*
