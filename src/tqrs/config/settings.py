"""Configuration settings for TQRS using Pydantic Settings."""

import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str
    openai_base_url: str | None = None  # For Enterprise API
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.1  # Low for consistent scoring
    openai_max_tokens: int = 2000
    openai_timeout: int = 30  # Seconds
    openai_max_retries: int = 3

    # Processing Configuration
    batch_size: int = 50
    batch_concurrency: int = 5  # Max parallel LLM requests

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Paths
    temp_dir: Path = Path(tempfile.gettempdir())

    @property
    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        return bool(self.openai_api_key and self.openai_api_key != "your-api-key-here")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return Settings()
