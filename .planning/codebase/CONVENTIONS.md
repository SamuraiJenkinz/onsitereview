# Coding Conventions

**Analysis Date:** 2026-02-13

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules
- Example: `src/tqrs/llm/client.py`, `src/tqrs/rules/evaluator.py`, `tests/test_models.py`
- Test files use `test_*.py` prefix, matching module structure under `tests/`

**Functions:**
- `snake_case` for all function and method names
- Examples: `evaluate_ticket()`, `get_line_of_business()`, `parse_json()`, `empty_string_to_none()`
- Private methods use leading underscore: `_create_error_result()`

**Variables:**
- `snake_case` for all variables and parameters
- Examples: `prompt_tokens`, `max_retries`, `assignment_group`, `total_deductions`
- Constants use `UPPER_SNAKE_CASE`: `TEMPLATE_EVALUATIONS`, `RESPONSE_SCHEMA`

**Types:**
- `PascalCase` for class names and type aliases
- Examples: `ServiceNowTicket`, `EvaluationResult`, `LLMEvaluator`, `TicketEvaluator`
- Enum values use `UPPER_SNAKE_CASE`: `PerformanceBand.BLUE`, `TemplateType.INCIDENT_LOGGING`

**Boolean fields/properties:**
- Prefix with `is_` or `has_`: `is_closed`, `is_resolved`, `has_validation`, `is_perfect`, `is_deduction`
- Computed properties use `@property` decorator

## Code Style

**Formatting:**
- Line length: 100 characters (configured in `pyproject.toml`)
- Tool: Ruff (isort for import sorting)
- Python version: 3.11+

**Linting:**
- Tool: Ruff with explicit rule selection
- Enabled rules: E (pycodestyle errors), W (warnings), F (pyflakes), I (isort), B (flake8-bugbear), C4 (comprehensions), UP (pyupgrade)
- Ignored: E501 (line too long - handled by formatter)

**Module docstrings:**
- Every module starts with module-level docstring in triple quotes
- Format: `"""Brief description of module purpose."""`
- Examples: `"""ServiceNow ticket data model."""`, `"""OpenAI API client with retry logic and error handling."""`

## Import Organization

**Order:**
1. Standard library imports (stdlib)
2. Third-party imports (external packages)
3. Local imports (tqrs modules)
4. Blank lines separate groups

**Examples:**
```python
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from openai import APIConnectionError, APIError, AzureOpenAI, OpenAI, RateLimitError
from pydantic import BaseModel, Field, field_validator

from tqrs.llm.client import OpenAIClient
from tqrs.models.evaluation import TemplateType
from tqrs.rules.base import RuleResult
```

**Path Aliases:**
- First-party imports use full module paths: `from tqrs.models.ticket import ServiceNowTicket`
- Configured in `pyproject.toml` under `tool.ruff.lint.isort` with `known-first-party = ["tqrs"]`

## Error Handling

**Patterns:**
- Custom exception hierarchy for domain-specific errors
- Exceptions located in module handling that domain
- Examples from `src/tqrs/llm/client.py`:
  - Base: `LLMError(Exception)` - all LLM-related errors inherit from this
  - Specific: `LLMRateLimitError(LLMError)`, `LLMAPIError(LLMError)`, `LLMValidationError(LLMError)`, `LLMTimeoutError(LLMError)`

**Docstring in exception class:**
```python
class LLMValidationError(LLMError):
    """Raised when response validation fails."""
    pass
```

**Error handling in methods:**
- Try-except blocks with specific exception handling
- Log errors at appropriate level (error, warning)
- Return default/error result rather than raising (when appropriate for business logic)
- Example from `src/tqrs/llm/evaluator.py`:
  ```python
  try:
      # evaluation logic
  except Exception as e:
      logger.error(f"Error in {eval_type} evaluation for {ticket.number}: {e}")
      results.append(self._create_error_result(eval_type, str(e)))
  ```

**Validation errors:**
- Use Pydantic `ValidationError` for model validation
- Catch and handle in appropriate layer
- Example from tests: `pytest.raises(ValidationError)` to verify field constraints

## Logging

**Framework:** Python's `logging` module

**Patterns:**
- Import at module level: `logger = logging.getLogger(__name__)`
- Use appropriate level:
  - `logger.debug()` - diagnostic info
  - `logger.info()` - informational messages
  - `logger.warning()` - warning messages for potential issues
  - `logger.error()` - error messages with context
  - `logger.exception()` - error with full traceback for unexpected exceptions

**Examples:**
```python
logger.info(f"Parsing ServiceNow JSON file: {path}")
logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
logger.error(f"LLM error evaluating {ticket.number}: {e}")
logger.exception(f"Unexpected error evaluating {ticket.number}: {e}")
```

**Configuration:**
- Log level set via `Settings.log_level`: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
- Default: "INFO"

## Comments

**When to Comment:**
- Complex business logic requiring explanation
- Non-obvious algorithmic choices
- Security-relevant decisions
- Workarounds and temporary solutions with reason

**DocString vs Comment:**
- Use docstrings for class/function/module public interface
- Use inline comments (# ...) for code block explanation
- Avoid redundant comments repeating code

**JSDoc/TSDoc:**
- Use NumPy/Google style docstrings for functions
- Include Args, Returns, Raises sections
- Example from `src/tqrs/config/settings.py`:
  ```python
  def get_settings() -> Settings:
      """Get cached settings instance.

      Raises:
          ValidationError: If required settings are missing or invalid.
      """
      return Settings()
  ```

## Function Design

**Size:** Keep functions focused and under 50 lines when practical

**Parameters:**
- Use type hints for all parameters
- Place required parameters before optional
- Use dataclasses or Pydantic models for multiple related parameters
- Example: `def evaluate_ticket(self, ticket: ServiceNowTicket, template: TemplateType) -> EvaluationResult:`

**Return Values:**
- Always include return type hint
- Return custom domain objects (Pydantic models) rather than dicts
- Examples: `RuleResult`, `EvaluationResult`, `TokenUsage`

**Class Methods:**
- Use `@classmethod` for factory constructors with `cls` parameter
- Example from `src/tqrs/scoring/evaluator.py`:
  ```python
  @classmethod
  def create(cls, api_key: str, ...) -> "TicketEvaluator":
      """Create a fully configured ticket evaluator."""
  ```

**Properties:**
- Use `@property` for computed attributes
- Example from `src/tqrs/models/ticket.py`:
  ```python
  @property
  def is_closed(self) -> bool:
      """Check if ticket is in closed state."""
      return self.state == "7" or self.incident_state == "7"
  ```

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` to define public API
- Example from `src/tqrs/llm/__init__.py`:
  ```python
  from tqrs.llm.client import (
      LLMError,
      LLMRateLimitError,
      OpenAIClient,
      TokenUsage,
  )
  ```

**Barrel Files:**
- `__init__.py` files aggregate and re-export key classes/functions
- Allows cleaner imports: `from tqrs.llm import OpenAIClient` vs `from tqrs.llm.client import OpenAIClient`
- Location: `src/tqrs/*/`

**Module Organization:**
- Group related functionality: llm/, models/, rules/, scoring/, parser/
- One main class per file when domain-specific
- Shared utilities grouped: client, schemas, prompts in llm/
- Tests mirror source structure: `src/tqrs/module.py` → `tests/test_module.py`

## Pydantic Models

**Pattern:**
- Inherit from `BaseModel` (from `tqrs.models.ticket` and `tqrs.models.evaluation`)
- Use `Field()` for documentation and validation
- Include docstrings on class describing purpose
- Field docstrings via `description` parameter in Field

**Example from `src/tqrs/models/ticket.py`:**
```python
class ServiceNowTicket(BaseModel):
    """Parsed ServiceNow incident ticket with relevant fields for evaluation."""

    number: str = Field(..., description="Ticket number (e.g., INC8924218)")
    sys_id: str = Field(..., description="Unique ServiceNow identifier")
    opened_at: datetime = Field(..., description="When ticket was opened")
```

**Field Validators:**
- Use `@field_validator` decorator with `mode="before"` or `mode="after"`
- Stack validators for related fields
- Example:
  ```python
  @field_validator("work_notes", "close_notes", "close_code", mode="before")
  @classmethod
  def empty_string_to_default(cls, v: str | None) -> str:
      """Convert None to empty string for optional text fields."""
      return v if v else ""
  ```

**Computed Fields:**
- Use `@computed_field` for derived values
- Located in evaluation models

**Configuration:**
- Use `model_config` for validation settings
- Example from settings: `SettingsConfigDict(env_file=".env", case_sensitive=False)`

## Type Hints

**Usage:**
- Type hints required for all function parameters and returns
- Use modern union syntax: `str | None` instead of `Optional[str]`
- Use `list[T]` instead of `List[T]`
- Use `dict[K, V]` instead of `Dict[K, V]`

**Examples:**
```python
def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
    """Evaluate a ticket and return the result."""

def add(self, usage: dict[str, int]) -> None:
    """Add token usage from a response."""

def get_criterion_by_id(self, criterion_id: str) -> Criterion | None:
```

## Protocol Usage

**Pattern:**
- Use `Protocol` from `typing` for structural typing contracts
- Located in base modules: `src/tqrs/rules/base.py`
- Example:
  ```python
  class RuleEvaluator(Protocol):
      """Protocol for rule evaluators."""

      def evaluate(self, ticket: ServiceNowTicket) -> RuleResult:
          """Evaluate a ticket and return the result."""
          ...
  ```

## Dataclasses

**Usage:**
- Use for data containers with no business logic
- Examples: `TokenUsage`, `ClientConfig` in `src/tqrs/llm/client.py`
- Use `@dataclass` from `dataclasses`

**Example:**
```python
@dataclass
class TokenUsage:
    """Tracks token usage across requests."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0

    def add(self, usage: dict[str, int]) -> None:
        """Add token usage from a response."""
```

## Testing Considerations

- Models must be testable with Pydantic validation
- Error types must be importable and catchable in tests
- Custom exceptions define the contract between components

---

*Convention analysis: 2026-02-13*
