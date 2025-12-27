"""OpenAI API client with retry logic and error handling."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APIError, AzureOpenAI, OpenAI, RateLimitError

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded after retries."""

    pass


class LLMAPIError(LLMError):
    """Raised for API errors after retries."""

    pass


class LLMValidationError(LLMError):
    """Raised when response validation fails."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when request times out."""

    pass


@dataclass
class TokenUsage:
    """Tracks token usage across requests."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0

    def add(self, usage: dict[str, int]) -> None:
        """Add token usage from a response."""
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        self.request_count += 1

    @property
    def estimated_cost(self) -> float:
        """Estimate cost based on GPT-4o pricing ($2.50/1M input, $10/1M output)."""
        input_cost = (self.prompt_tokens / 1_000_000) * 2.50
        output_cost = (self.completion_tokens / 1_000_000) * 10.00
        return input_cost + output_cost


@dataclass
class ClientConfig:
    """Configuration for OpenAI client."""

    api_key: str
    base_url: str | None = None
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 30
    max_retries: int = 3
    retry_delays: tuple[float, ...] = field(default_factory=lambda: (1.0, 2.0, 4.0))
    # Azure OpenAI settings
    use_azure: bool = False
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    azure_api_version: str = "2023-05-15"


class OpenAIClient:
    """OpenAI API client with retry logic and structured output support."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        timeout: int = 30,
        max_retries: int = 3,
        use_azure: bool = False,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        azure_api_version: str = "2023-05-15",
    ):
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            base_url: Optional custom API base URL (for Enterprise)
            model: Model to use (default: gpt-4o)
            temperature: Sampling temperature (default: 0.1 for consistency)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            use_azure: Whether to use Azure OpenAI
            azure_endpoint: Azure OpenAI endpoint (e.g., https://xxx.openai.azure.com/)
            azure_deployment: Azure deployment name
            azure_api_version: Azure API version
        """
        self.config = ClientConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            use_azure=use_azure,
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            azure_api_version=azure_api_version,
        )

        # Initialize appropriate client
        if use_azure:
            logger.info(f"Using Azure OpenAI: endpoint={azure_endpoint}, deployment={azure_deployment}")
            self._client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                azure_deployment=azure_deployment,
                api_version=azure_api_version,
                timeout=timeout,
            )
            # For Azure, use deployment name as model
            if azure_deployment:
                self.config.model = azure_deployment
        else:
            # Standard OpenAI client
            client_kwargs: dict[str, Any] = {
                "api_key": api_key,
                "timeout": timeout,
            }
            if base_url:
                client_kwargs["base_url"] = base_url
            self._client = OpenAI(**client_kwargs)

        self.token_usage = TokenUsage()

    def complete(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a completion request with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Parsed JSON response as dict

        Raises:
            LLMRateLimitError: If rate limit exceeded after retries
            LLMAPIError: If API error after retries
            LLMValidationError: If response parsing fails
            LLMTimeoutError: If request times out
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                return self._make_request(messages, response_format)
            except RateLimitError as e:
                last_error = e
                delay = self._get_retry_delay(attempt)
                logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
            except APIConnectionError as e:
                last_error = e
                delay = self._get_retry_delay(attempt)
                logger.warning(f"Connection error, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
            except APIError as e:
                last_error = e
                if e.status_code and e.status_code >= 500:
                    delay = self._get_retry_delay(attempt)
                    logger.warning(f"Server error, retrying in {delay}s (attempt {attempt + 1})")
                    time.sleep(delay)
                else:
                    raise LLMAPIError(f"API error: {e}") from e
            except TimeoutError as e:
                last_error = e
                delay = self._get_retry_delay(attempt)
                logger.warning(f"Timeout, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)

        # All retries exhausted
        if isinstance(last_error, RateLimitError):
            raise LLMRateLimitError(f"Rate limit exceeded after {self.config.max_retries} retries")
        elif isinstance(last_error, TimeoutError):
            raise LLMTimeoutError(f"Request timed out after {self.config.max_retries} retries")
        else:
            raise LLMAPIError(f"API error after {self.config.max_retries} retries: {last_error}")

    def _make_request(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a single API request."""
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)

        # Track token usage
        if response.usage:
            self.token_usage.add({
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            })

        # Extract and parse content
        content = response.choices[0].message.content
        if not content:
            raise LLMValidationError("Empty response from API")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMValidationError(f"Failed to parse JSON response: {e}") from e

    def _get_retry_delay(self, attempt: int) -> float:
        """Get retry delay for given attempt (exponential backoff)."""
        if attempt < len(self.config.retry_delays):
            return self.config.retry_delays[attempt]
        return self.config.retry_delays[-1] * 2

    def reset_usage(self) -> TokenUsage:
        """Reset and return token usage stats."""
        usage = self.token_usage
        self.token_usage = TokenUsage()
        return usage

    @classmethod
    def from_settings(cls, settings: Any) -> "OpenAIClient":
        """Create client from Settings object.

        Args:
            settings: Settings instance with openai_api_key and openai_model

        Returns:
            Configured OpenAIClient
        """
        return cls(
            api_key=settings.openai_api_key,
            base_url=getattr(settings, "openai_base_url", None),
            model=settings.openai_model,
        )
