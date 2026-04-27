from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="CAREER_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".career-agent",
        description="Base directory used for local Career Agent data storage.",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Optional OpenAI-compatible LLM API base URL.",
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for the configured LLM endpoint.",
    )
    llm_model: str | None = Field(
        default=None,
        description="Optional default model name for LLM-assisted workflows.",
    )
    llm_extraction_base_url: str | None = Field(
        default=None,
        description="Optional OpenAI-compatible LLM API base URL for extraction workflows.",
    )
    llm_extraction_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for the extraction LLM endpoint.",
    )
    llm_extraction_model: str | None = Field(
        default=None,
        description="Optional model name for extraction workflows.",
    )
    llm_eval_base_url: str | None = Field(
        default=None,
        description="Optional OpenAI-compatible LLM API base URL for evaluation workflows.",
    )
    llm_eval_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for the evaluation LLM endpoint.",
    )
    llm_eval_model: str | None = Field(
        default=None,
        description="Optional model name for evaluation workflows.",
    )

    @property
    def effective_llm_extraction_base_url(self) -> str | None:
        """Return the extraction endpoint, falling back to the default LLM endpoint."""

        return self.llm_extraction_base_url or self.llm_base_url

    @property
    def effective_llm_extraction_api_key(self) -> SecretStr | None:
        """Return the extraction API key, falling back to the default LLM API key."""

        return self.llm_extraction_api_key or self.llm_api_key

    @property
    def effective_llm_extraction_model(self) -> str | None:
        """Return the extraction model, falling back to the default LLM model."""

        return self.llm_extraction_model or self.llm_model

    @property
    def effective_llm_eval_base_url(self) -> str | None:
        """Return the evaluation endpoint, falling back to the default LLM endpoint."""

        return self.llm_eval_base_url or self.llm_base_url

    @property
    def effective_llm_eval_api_key(self) -> SecretStr | None:
        """Return the evaluation API key, falling back to the default LLM API key."""

        return self.llm_eval_api_key or self.llm_api_key

    @property
    def effective_llm_eval_model(self) -> str | None:
        """Return the evaluation model, falling back to the default LLM model."""

        return self.llm_eval_model or self.llm_model

    @field_validator("data_dir", mode="before")
    @classmethod
    def normalize_data_dir(cls, value: str | Path) -> Path:
        """Normalize string input into a `Path` and expand any user home shorthand."""

        return Path(value).expanduser()

    @field_validator(
        "llm_base_url",
        "llm_api_key",
        "llm_model",
        "llm_extraction_base_url",
        "llm_extraction_api_key",
        "llm_extraction_model",
        "llm_eval_base_url",
        "llm_eval_api_key",
        "llm_eval_model",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | SecretStr | None) -> str | SecretStr | None:
        """Treat blank optional environment values as unset."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""

    return Settings()
