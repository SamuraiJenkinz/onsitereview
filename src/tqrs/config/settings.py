"""Configuration settings for TQRS using Pydantic Settings."""

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration (for direct OpenAI API usage)
    openai_api_key: str = ""  # Optional - can use Azure instead
    openai_base_url: str | None = None  # For Enterprise API
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.1  # Low for consistent scoring
    openai_max_tokens: int = 2000
    openai_timeout: int = 30  # Seconds
    openai_max_retries: int = 3

    # Azure OpenAI Configuration (server-side credentials)
    # Uses TQRS_ prefix to avoid collisions with other apps
    azure_openai_endpoint: str | None = Field(
        default=None,
        validation_alias="TQRS_AZURE_OPENAI_ENDPOINT",
    )
    azure_openai_api_key: str | None = Field(
        default=None,
        validation_alias="TQRS_AZURE_OPENAI_API_KEY",
    )
    azure_openai_deployment: str | None = Field(
        default=None,
        validation_alias="TQRS_AZURE_OPENAI_DEPLOYMENT",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        validation_alias="TQRS_AZURE_OPENAI_API_VERSION",
    )

    # Processing Configuration
    batch_size: int = 50
    batch_concurrency: int = 5  # Max parallel LLM requests

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Paths
    temp_dir: Path = Path(tempfile.gettempdir())

    @property
    def is_configured(self) -> bool:
        """Check if required configuration is present (either OpenAI or Azure)."""
        return self.azure_credentials_configured or bool(
            self.openai_api_key and self.openai_api_key != "your-api-key-here"
        )

    @property
    def azure_credentials_configured(self) -> bool:
        """Check if Azure OpenAI credentials are configured via environment variables.

        Returns True only if all required Azure settings are present:
        - TQRS_AZURE_OPENAI_ENDPOINT
        - TQRS_AZURE_OPENAI_API_KEY
        - TQRS_AZURE_OPENAI_DEPLOYMENT
        """
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return Settings()
