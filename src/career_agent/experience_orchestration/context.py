from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AnalysisRunContext(BaseModel):
    """Portable identifiers for one orchestrated source analysis run."""

    analysis_run_id: str = Field(
        min_length=1,
        description="Source analysis run identifier being orchestrated.",
    )
    role_id: str = Field(
        min_length=1,
        description="Experience role identifier for the analysis run.",
    )
    source_ids: list[str] = Field(
        min_length=1,
        description="Role source identifiers included in the analysis run.",
    )
    fact_ids: list[str] = Field(
        default_factory=list,
        description="Experience fact identifiers available for comparison.",
    )
    active_constraint_ids: list[str] = Field(
        default_factory=list,
        description="Active scoped constraint identifiers loaded for this context.",
    )
    question_ids: list[str] = Field(
        default_factory=list,
        description="Clarification question identifiers available for this run.",
    )
    message_ids: list[str] = Field(
        default_factory=list,
        description="Clarification message identifiers available for this run.",
    )
    summary: str | None = Field(
        default=None,
        description="Optional short context summary for logs or prompts.",
    )

    @field_validator("analysis_run_id", "role_id", "summary", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator(
        "source_ids",
        "fact_ids",
        "active_constraint_ids",
        "question_ids",
        "message_ids",
        mode="before",
    )
    @classmethod
    def normalize_id_lists(cls, values: list[str] | None) -> list[str]:
        """Trim id lists and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]
