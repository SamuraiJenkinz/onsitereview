# Testing Patterns

**Analysis Date:** 2026-02-13

## Test Framework

**Runner:**
- pytest 8.0+ (configured in `pyproject.toml`)
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in assertions
- pytest.approx() for floating-point comparisons
- pytest.raises() for exception testing

**Run Commands:**
```bash
pytest tests/                          # Run all tests
pytest tests/test_models.py -v         # Run single test file
pytest tests/test_models.py::TestPerformanceBand -v  # Run specific test class
pytest --cov=src tests/                # Run with coverage report
pytest -k "test_create_ticket" -v      # Run tests matching keyword
pytest tests/ -v --tb=short            # Short traceback format (default)
```

**Configuration:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --tb=short"
```

## Test File Organization

**Location:**
- Tests are co-located with source in parallel structure
- Source: `src/tqrs/module_name.py` or `src/tqrs/package/file.py`
- Tests: `tests/test_module_name.py`
- Example: `src/tqrs/models/ticket.py` → `tests/test_models.py`

**Naming:**
- Test files: `test_*.py` prefix
- Test classes: `Test<FeatureName>` (e.g., `TestPerformanceBand`, `TestScoringCalculator`)
- Test methods: `test_<scenario_description>` (e.g., `test_blue_threshold`, `test_valid_4part_format_spaces`)

**Structure:**
```
tests/
├── conftest.py                # Global fixtures and configuration
├── test_models.py             # Tests for data models (evaluation, ticket, rubric)
├── test_rules.py              # Tests for rules engine
├── test_scoring.py            # Tests for scoring engine
├── test_llm.py                # Tests for LLM client and evaluator
├── test_parser.py             # Tests for parsers
└── __init__.py
```

## Test Structure

**Suite Organization:**
Test classes group related tests. Example from `tests/test_models.py`:

```python
class TestPerformanceBand:
    """Tests for PerformanceBand enum."""

    def test_blue_threshold(self):
        """Blue band should be >= 95%."""
        assert PerformanceBand.from_percentage(95) == PerformanceBand.BLUE

    def test_green_threshold(self):
        """Green band should be >= 90% and < 95%."""
        assert PerformanceBand.from_percentage(90) == PerformanceBand.GREEN
```

**Patterns:**

1. **Setup pattern:** Use pytest fixtures (defined in conftest.py or test file)
   ```python
   @pytest.fixture
   def sample_ticket() -> ServiceNowTicket:
       """Create a sample ticket for testing."""
       return ServiceNowTicket(
           number="INC1234567",
           sys_id="abc123",
           # ... required fields
       )
   ```

2. **Teardown pattern:** Fixtures handle cleanup automatically via yield
   ```python
   @pytest.fixture
   def resource():
       # Setup
       resource = create_resource()
       yield resource
       # Cleanup happens here
       resource.cleanup()
   ```

3. **Assertion pattern:** Direct assertions using pytest
   ```python
   assert result.passed is True
   assert result.percentage == pytest.approx(92.9, 0.1)
   assert result.band == PerformanceBand.GREEN
   ```

## Mocking

**Framework:** unittest.mock (from stdlib)

**Patterns:**

1. **MagicMock for object replacement:**
   ```python
   from unittest.mock import MagicMock

   mock_client = MagicMock()
   mock_client.complete.return_value = {
       "criterion_id": "test",
       "score": 20,
       # ... response fields
   }
   evaluator = LLMEvaluator(mock_client)
   ```

2. **patch decorator for function mocking:**
   ```python
   @patch("tqrs.llm.client.OpenAI")
   def test_uses_openai(mock_openai_class, sample_ticket):
       mock_client_instance = MagicMock()
       mock_openai_class.return_value = mock_client_instance
       # Test code using mocked client
   ```

3. **Fixture-based mocking responses:**
   ```python
   @pytest.fixture
   def mock_description_response() -> dict:
       """Mock response for description evaluation."""
       return {
           "criterion_id": "accurate_description",
           "score": 20,
           "max_score": 20,
           # ... other fields
       }
   ```

**What to Mock:**
- External API clients (OpenAI, Azure)
- File I/O operations
- Network calls
- Time-dependent operations (use freezegun if needed)

**What NOT to Mock:**
- Pydantic models (test with real instances)
- Business logic (test actual behavior)
- Data validators (test validation rules)
- Internal method calls within tested class
- Local computations

## Fixtures and Factories

**Test Data Locations:**
- Conftest fixtures: `tests/conftest.py` (shared across all tests)
- Local fixtures: Within test classes or test modules
- Sample data files: `prototype_samples.json`, `scoring_rubrics.json` in project root

**Fixture Examples from conftest.py:**

```python
@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def sample_tickets(parser: ServiceNowParser, sample_tickets_path: Path) -> list[ServiceNowTicket]:
    """Parse and return sample tickets."""
    return parser.parse_file(sample_tickets_path)

@pytest.fixture
def rubrics(rubrics_path: Path):
    """Load all scoring rubrics."""
    return load_rubrics(rubrics_path)

@pytest.fixture
def incident_logging_rubric(rubrics):
    """Get the Incident Logging rubric."""
    return rubrics[TemplateType.INCIDENT_LOGGING]
```

**Factory Function from test_rules.py:**

```python
def create_ticket(**kwargs) -> ServiceNowTicket:
    """Create a ticket with specified fields, filling in defaults."""
    defaults = {
        "number": "INC0000001",
        "sys_id": "abc123",
        "opened_at": "2025-12-10T10:00:00",
        # ... other defaults
    }
    defaults.update(kwargs)
    return ServiceNowTicket(**defaults)

# Usage:
ticket = create_ticket(short_description="MMC - Wollongong - AD - Password reset")
```

**Fixture Dependencies:**
- Fixtures can depend on other fixtures
- Example: `sample_tickets` depends on `parser` and `sample_tickets_path`
- Order handled automatically by pytest

## Coverage

**Requirements:**
- No explicit coverage target configured in pyproject.toml
- Target coverage should be established per domain
- Critical paths: Error handling, validation rules, scoring logic

**View Coverage:**
```bash
pytest --cov=src --cov-report=html tests/
# Opens htmlcov/index.html for detailed coverage report

pytest --cov=src --cov-report=term-missing tests/
# Shows missing lines in terminal
```

**Coverage Configuration Location:**
- Could be added to `[tool.coverage.run]` in pyproject.toml if desired
- Currently relying on test quality to ensure coverage

## Test Types

**Unit Tests:**
- Scope: Single class or function
- Location: Primary test files (test_models.py, test_rules.py)
- Isolation: Heavy use of fixtures and mocks
- Example: Testing `RuleResult.numeric_score` property
- Frequency: 80% of test suite

**Integration Tests:**
- Scope: Multiple components working together
- Location: End of test files or test classes (e.g., `TestIntegration`)
- Example: `TestIntegration` in `tests/test_scoring.py`
- Tests actual rules + scoring calculator + result formatter together
- Mocking only external dependencies (API calls)

**E2E Tests:**
- Not explicitly present in current test suite
- Would test full evaluation pipeline with real data
- Marked with `@pytest.mark.slow` if added
- Could use prototype_samples.json as test data

## Common Patterns

**Boundary Testing:**
```python
def test_blue_threshold(self):
    """Blue band should be >= 95%."""
    assert PerformanceBand.from_percentage(95) == PerformanceBand.BLUE
    assert PerformanceBand.from_percentage(100) == PerformanceBand.BLUE
    assert PerformanceBand.from_percentage(95.5) == PerformanceBand.BLUE

def test_green_threshold(self):
    """Green band should be >= 90% and < 95%."""
    assert PerformanceBand.from_percentage(90) == PerformanceBand.GREEN
    assert PerformanceBand.from_percentage(94.9) == PerformanceBand.GREEN
```

**Async Testing:**
Not applicable - project doesn't use async/await extensively. If needed:
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

**Error Testing:**
```python
def test_evaluation_result_score_bounds(self):
    """Total score should be bounded 0-70."""
    with pytest.raises(ValidationError):
        EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=71,  # Over max - should raise
            criterion_scores=[],
            strengths=[],
            improvements=[],
        )
```

**Parametrized Tests (when multiple scenarios test same logic):**
```python
@pytest.mark.parametrize("percentage,expected_band", [
    (95, PerformanceBand.BLUE),
    (90, PerformanceBand.GREEN),
    (75, PerformanceBand.YELLOW),
    (50, PerformanceBand.RED),
    (25, PerformanceBand.PURPLE),
])
def test_band_from_percentage(percentage, expected_band):
    assert PerformanceBand.from_percentage(percentage) == expected_band
```

## Test Documentation

**Docstrings:**
- Every test method has docstring explaining what it tests
- Format: `"""What should happen in this test scenario."""`
- Examples:
  ```python
  def test_valid_4part_format_spaces(self, short_desc_validator):
      """Test valid 4-part format with ' - ' separators."""

  def test_blue_threshold(self):
      """Blue band should be >= 95%."""

  def test_create_ticket(**kwargs) -> ServiceNowTicket:
      """Create a ticket with specified fields, filling in defaults."""
  ```

## Test Classes and Organization

**Fixture scopes (usage in conftest.py):**
- `function` (default): Reset for each test
- `class`: Shared across test class
- `module`: Shared across test module
- `session`: Shared across entire test session

**Example test class with fixtures:**
```python
class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    @pytest.fixture
    def sample_criteria(self) -> list[CriterionScore]:
        """Create sample criterion scores."""
        return [
            CriterionScore(
                criterion_id="short_desc",
                criterion_name="Short Description",
                max_points=8,
                points_awarded=8,
                evidence="Good format",
                reasoning="Follows 4-part format",
            ),
        ]

    def test_create_passing_evaluation(self, sample_criteria: list[CriterionScore]):
        """Should create evaluation that passes."""
        result = EvaluationResult(
            ticket_number="INC123",
            template=TemplateType.INCIDENT_LOGGING,
            total_score=65,
            criterion_scores=sample_criteria,
            strengths=["Good documentation"],
            improvements=["Add more detail"],
        )
        assert result.passed is True
```

## Test Statistics

- **Total tests:** 196 (across all test files)
- **Test distribution:**
  - test_scoring.py: ~60 tests (scoring engine)
  - test_llm.py: ~50 tests (LLM client and evaluator)
  - test_rules.py: ~40 tests (rules engine)
  - test_models.py: ~30 tests (data models)
  - test_parser.py: ~16 tests (parsing)

## Key Testing Principles

1. **Isolation:** Each test should be independent, use fixtures for setup
2. **Clarity:** Test names describe the scenario being tested
3. **Completeness:** Test both happy path and error cases
4. **Documentation:** Docstrings explain what assertion verifies
5. **Fixtures over Setup:** Use pytest fixtures instead of setUp/tearDown
6. **Mocking External:** Mock API calls, file I/O; test business logic directly
7. **Real Models:** Use actual Pydantic models instead of dicts to verify validation
8. **Fast Execution:** Unit tests should run in <100ms each
9. **No State Sharing:** Each test gets clean fixtures, no shared mutable state
10. **Assertion Clarity:** Use explicit assertions with context, not implicit truthy checks

---

*Testing analysis: 2026-02-13*
