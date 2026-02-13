# Codebase Concerns

**Analysis Date:** 2026-02-13

## Tech Debt

**Broad Exception Handling (Multiple Files):**
- Issue: Multiple `except Exception as e:` blocks silently catch all exceptions without specific error classification
- Files: `C:\TQRS\src\tqrs\llm\evaluator.py` (line 89, 369), `C:\TQRS\src\tqrs\ui\app.py` (lines 365, 410), `C:\TQRS\src\tqrs\ui\components\upload.py` (lines 288, 325, 349, 416), `C:\TQRS\src\tqrs\scoring\batch.py` (lines 113, 171), `C:\TQRS\src\tqrs\parser\servicenow.py` (line 68)
- Impact: Error handling is non-specific, making debugging difficult and potentially hiding critical failures
- Fix approach: Replace broad exception handlers with specific exception types. Create custom exception hierarchy for each module domain (ParsingError, EvaluationError, ConfigurationError)

**Silent Failure on Parse Errors (Upload Component):**
- Issue: `C:\TQRS\src\tqrs\ui\components\upload.py` line 416 has `except Exception: return []` with no logging
- Files: `C:\TQRS\src\tqrs\ui\components\upload.py:416`
- Impact: Failed ticket parsing silently returns empty list, user sees "0 tickets loaded" with no error details
- Fix approach: Add logging before returning empty list, propagate parsing errors to caller with context

**Partial Response Fallback Pattern (LLM Evaluator):**
- Issue: `C:\TQRS\src\tqrs\llm\evaluator.py` lines 304-360 implements `_parse_partial_response` that fills missing fields with defaults, potentially returning incomplete evaluations
- Files: `C:\TQRS\src\tqrs\llm\evaluator.py:304-360`
- Impact: LLM evaluation quality degrades silently when API returns malformed responses; scores may not reflect actual ticket quality
- Fix approach: Add validation thresholds - if too many fields are missing (>30%), log warning and treat as failed evaluation rather than partial success

## Performance Bottlenecks

**Sequential LLM Evaluation in Batch Processing:**
- Issue: `C:\TQRS\src\tqrs\llm\batch.py` contains both `evaluate_batch()` (sequential) and `evaluate_batch_async()` (concurrent), but the UI uses synchronous approach
- Files: `C:\TQRS\src\tqrs\llm\batch.py`, `C:\TQRS\src\tqrs\ui\app.py`
- Impact: Large batches (100+ tickets) process slowly due to sequential API calls; estimated 5+ minutes per 50 tickets at 5-second per API call latency
- Improvement path: Enable async batch processing in UI by integrating `evaluate_batch_async()` with Streamlit's progress tracking
- Mitigation: Current concurrency limit of 5 prevents rate limiting but could be increased to 10-15 with exponential backoff retry logic

**Memory Accumulation in Token Tracking:**
- Issue: `C:\TQRS\src\tqrs\llm\client.py:189-295` maintains running token usage stats without periodic reset in long-running sessions
- Files: `C:\TQRS\src\tqrs\llm\client.py`
- Impact: Memory footprint grows linearly with number of API calls in sessions processing 1000+ tickets
- Improvement path: Implement periodic token usage reporting and reset after each batch, or implement circular buffer for last N requests

**PDF Parsing Regex Performance:**
- Issue: `C:\TQRS\src\tqrs\parser\pdf.py` line 101 uses `re.search()` for each field with DOTALL flag across full document text multiple times
- Files: `C:\TQRS\src\tqrs\parser\pdf.py:94-106`
- Impact: For large PDFs (50+ pages), regex operations become slow; O(n*m) complexity where n=fields and m=document length
- Improvement path: Compile regex patterns once (move to class initialization), use `re.compile()` with cached patterns

## Fragile Areas

**LLM Response Validation Resilience:**
- Issue: `C:\TQRS\src\tqrs\llm\evaluator.py` implements `_safe_parse()` with ValidationError fallback to `_parse_partial_response()`, but no version awareness
- Files: `C:\TQRS\src\tqrs\llm\evaluator.py:362-371`
- Why fragile: If OpenAI API response format changes, fallback parsing will provide degraded but non-obvious failures
- Safe modification: Add API response version tracking, log schema version mismatches, implement schema versioning in evaluation models
- Test coverage: Missing tests for partial response recovery scenarios

**PDF Field Extraction Patterns:**
- Issue: `C:\TQRS\src\tqrs\parser\pdf.py:20-48` uses hardcoded regex patterns for field extraction
- Files: `C:\TQRS\src\tqrs\parser\pdf.py:20-48`
- Why fragile: PDF structure variations from different ServiceNow configurations will cause extraction failures silently
- Safe modification: Add fallback extraction strategies, implement field presence validation before parsing, add PDF validation test suite with sample PDFs
- Test coverage: Only regex patterns tested, no integration tests with real PDF exports

**State Management Attribute Access:**
- Issue: `C:\TQRS\src\tqrs\ui\state.py:91-102` implements `update_state()` with `hasattr()` check that raises AttributeError for typos
- Files: `C:\TQRS\src\tqrs\ui\state.py:102`
- Why fragile: Runtime error (AttributeError) triggers on state key typos in update_state calls, no compile-time safety
- Safe modification: Use dataclass validation in Pydantic or TypedDict for type-safe state keys
- Test coverage: Missing tests for invalid state key updates

**Async Lock Pattern in Batch Processing:**
- Issue: `C:\TQRS\src\tqrs\scoring\batch.py:153-181` and `C:\TQRS\src\tqrs\llm\batch.py` implement asyncio.Semaphore and asyncio.Lock patterns
- Files: `C:\TQRS\src\tqrs\scoring\batch.py:153-181`
- Why fragile: Deadlock potential if coroutine is cancelled or exception occurs during lock hold
- Safe modification: Use async context managers consistently, add timeout to locks, implement circuit breaker for failed evaluations
- Test coverage: No tests for concurrency edge cases or cancellation scenarios

## Test Coverage Gaps

**LLM API Error Handling Untested:**
- What's not tested: Rate limit recovery, timeout handling, partial response parsing
- Files: `C:\TQRS\src\tqrs\llm\client.py` (lines 214-247), `C:\TQRS\src\tqrs\llm\evaluator.py` (lines 362-371)
- Risk: Production failures in retry logic or response validation go undetected until customer impact
- Priority: High - affects core evaluation functionality

**UI State Transitions:**
- What's not tested: Reset behavior between evaluations, template switching with active processing, error message clearing
- Files: `C:\TQRS\src\tqrs\ui\app.py`, `C:\TQRS\src\tqrs\ui\state.py`, `C:\TQRS\src\tqrs\ui\components/upload.py`
- Risk: UI inconsistencies or data loss during rapid state changes in concurrent operations
- Priority: Medium - affects user experience

**PDF Parsing Edge Cases:**
- What's not tested: Multi-page PDFs, missing required fields, corrupted PDF data, various ServiceNow export formats
- Files: `C:\TQRS\src\tqrs\parser\pdf.py`
- Risk: Silent failures (returning None) for malformed PDFs with no user feedback
- Priority: Medium - affects single-ticket upload feature

**Batch Processing with Empty Results:**
- What's not tested: Behavior when all tickets fail evaluation, progress callback with no tickets, concurrent evaluation with cancellation
- Files: `C:\TQRS\src\tqrs\scoring\batch.py:214-225`
- Risk: Edge cases may cause crashes or incorrect summary generation
- Priority: Low - affects rare edge cases

## Security Considerations

**API Key Exposure in Logs:**
- Risk: API keys may be logged in error messages or exception traces
- Files: Potentially `C:\TQRS\src\tqrs\llm\client.py`, `C:\TQRS\src\tqrs\ui\components\upload.py`
- Current mitigation: Streamlit uses password input field for API key (line 139, 136)
- Recommendations: Add API key sanitization in all logging statements, mask keys in error messages, audit log output for sensitive data

**Azure Endpoint URL in Logs:**
- Risk: Azure endpoint URLs are logged during configuration (line 143 in client.py), may leak internal infrastructure
- Files: `C:\TQRS\src\tqrs\llm\client.py:143`
- Current mitigation: Endpoints logged at INFO level only
- Recommendations: Mask sensitive parts of URLs (deployment names), log only sanitized versions in production

**CORS and Web Security in Streamlit:**
- Risk: Streamlit default configuration allows all origins, potentially vulnerable to CSRF attacks
- Files: `C:\TQRS\src\tqrs\ui\app.py`
- Current mitigation: Streamlit runs locally by default, admin mode requires URL parameter
- Recommendations: Document secure deployment practices, require explicit security configuration for production, implement request validation

**Credentials in Environment Variables:**
- Risk: Azure credentials stored in environment variables are accessible to all processes on the machine
- Files: `C:\TQRS\src\tqrs\config\settings.py:31-48`
- Current mitigation: Uses TQRS_ prefix to isolate from other apps
- Recommendations: Document that sensitive environment variables should use OS-level protection, implement credential rotation strategy

## Known Bugs

**PDF Date Parsing Failures Not Reported:**
- Symptoms: PDF upload returns None silently when date parsing fails
- Files: `C:\TQRS\src\tqrs\parser\pdf.py:224-258`
- Trigger: PDF with non-standard date formats (e.g., "16-Dec-2025" or without timezone)
- Workaround: None - requires PDF re-export from ServiceNow in standard format
- Fix: Add fallback to more date formats or extract partial data even if date parsing fails

**Template Change During Evaluation Not Blocked:**
- Symptoms: User can change evaluation template while results are loading, causing inconsistent results display
- Files: `C:\TQRS\src\tqrs\ui\components\upload.py:79-89` and `C:\TQRS\src\tqrs\ui\app.py:72-74`
- Trigger: Rapid template selection during batch processing
- Workaround: Disable template selection via UI when `is_processing=True`
- Fix: Add guard in template change handler to prevent changes during active evaluation

**Empty Tickets List Causes ZeroDivisionError Risk:**
- Symptoms: Potential division by zero in batch summary generation
- Files: `C:\TQRS\src\tqrs\scoring\batch.py:234-235` (mitigated by line 214 check)
- Trigger: Empty results list passed to `generate_summary()`
- Workaround: Check is in place (line 214-225) but not consistently applied in async path
- Fix: Add explicit validation in async path, ensure same guards in both sync/async variants

## Missing Critical Features

**No Evaluation Caching:**
- Problem: Re-evaluating the same ticket set requires full LLM re-processing, expensive and slow
- Blocks: Batch re-evaluation, result comparison, performance optimization
- Suggested approach: Implement simple file-based cache keyed by ticket number + template type + model version

**No Batch Resume/Recovery:**
- Problem: If batch evaluation fails halfway (API outage, network error), no way to resume from last successful ticket
- Blocks: Reliable evaluation of large datasets (1000+ tickets), enterprise use cases
- Suggested approach: Implement checkpoint system tracking completed ticket IDs, allow resume from last checkpoint

**No Result Versioning:**
- Problem: Multiple evaluation runs produce results with no version tracking or comparison capability
- Blocks: A/B testing LLM prompts, tracking quality improvements over time
- Suggested approach: Add evaluation run ID (timestamp + hash), track model version and prompt version with each result

**No Streaming Response Support:**
- Problem: LLM evaluations wait for full response completion before returning, no incremental results
- Blocks: Real-time feedback for large batches, faster time-to-first-result
- Suggested approach: Implement streaming response parsing, yield partial results as they arrive

## Scaling Limits

**Concurrent API Requests:**
- Current capacity: 5 concurrent requests (default), configurable to 15
- Limit: OpenAI rate limits (RPM and TPM) will be hit with 50+ concurrent requests
- Scaling path: Implement token bucket rate limiter, add queuing system for overload scenarios, support multiple API keys for distribution

**Memory Usage per Session:**
- Current capacity: 50 tickets safely cached, 100+ causes perceptible lag
- Limit: Streamlit session memory grows with ticket count, UI becomes unresponsive >1000 tickets
- Scaling path: Implement pagination for results display, use database backend instead of in-memory state

**PDF Parsing Performance:**
- Current capacity: PDFs up to 50 pages parse in <5 seconds
- Limit: 100+ page PDFs cause timeouts or memory exhaustion
- Scaling path: Implement streaming PDF parser, extract only relevant sections instead of full text

## Dependencies at Risk

**pdfplumber Maintenance:**
- Risk: Library has infrequent updates, may not handle new PDF variants
- Impact: PDF upload feature breaks with future ServiceNow PDF format changes
- Migration plan: Alternative options are PyPDF2 (more stable) or tabula-py (table-specific)

**Streamlit Reactive Model Limitations:**
- Risk: Streamlit's full-reruns-on-every-interaction model causes unexpected behavior with async operations
- Impact: Complex multi-step workflows are fragile and error-prone
- Migration plan: Consider moving to FastAPI + frontend framework for better control, or wait for Streamlit improvements

**OpenAI SDK Major Version Updates:**
- Risk: OpenAI SDK v2.0+ has breaking API changes
- Impact: Pinning to v1.0 risks missing security updates
- Migration plan: Plan upgrade to v2.0+ compatible API patterns, test thoroughly with test environment first

## Recommendations Summary

**High Priority (Immediate Action):**
1. Add specific exception handling instead of broad `except Exception`
2. Implement API key sanitization in all logging
3. Add tests for LLM error recovery scenarios
4. Add guard to prevent template change during processing

**Medium Priority (Next Sprint):**
1. Implement batch processing resume capability
2. Optimize PDF regex patterns with compiled expressions
3. Add more comprehensive PDF parsing tests
4. Implement request validation for security

**Low Priority (Future Planning):**
1. Add evaluation caching system
2. Implement result versioning
3. Add streaming response support
4. Plan for major dependency version upgrades

---

*Concerns audit: 2026-02-13*
