from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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

    @field_validator("data_dir", mode="before")
    @classmethod
    def normalize_data_dir(cls, value: str | Path) -> Path:
        """Normalize string input into a `Path` and expand any user home shorthand."""

        return Path(value).expanduser()


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""

    return Settings()
