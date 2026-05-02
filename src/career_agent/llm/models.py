from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class LLMRequest(BaseModel):
    """Provider-neutral request sent to an LLM client."""

    system_prompt: str = Field(
        min_length=1,
        description="Instructional prompt that defines model behavior.",
    )
    user_prompt: str = Field(
        min_length=1,
        description="User/task prompt containing the request payload.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model or route name for the downstream client.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0,
        le=2,
        description="Sampling temperature requested from the downstream client.",
    )

    @field_validator("system_prompt", "user_prompt", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Any) -> Any:
        """Trim required prompt fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("model", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        """Trim optional text fields and treat blanks as unset."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LLMResponse(BaseModel):
    """Provider-neutral response returned by an LLM client."""

    content: str = Field(
        min_length=1,
        description="Raw text content returned by the LLM client.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model or route name that handled the request.",
    )

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: Any) -> Any:
        """Trim response content before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("model", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        """Trim optional text fields and treat blanks as unset."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
