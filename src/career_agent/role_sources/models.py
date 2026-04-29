from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class RoleSourceStatus(StrEnum):
    """Analysis status for a submitted role source entry."""

    NOT_ANALYZED = "not_analyzed"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"


class RoleSourceEntry(BaseModel):
    """Submitted source material for one saved experience role."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this source entry.",
    )
    role_id: str = Field(
        min_length=1,
        description="Identifier of the experience role this source belongs to.",
    )
    source_text: str = Field(
        min_length=1,
        description="Source material retained exactly as submitted by the user.",
    )
    status: RoleSourceStatus = Field(
        default=RoleSourceStatus.NOT_ANALYZED,
        description="Analysis status for this source entry.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("role_id", mode="before")
    @classmethod
    def normalize_role_id(cls, value: str) -> str:
        """Trim role ids before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source_text")
    @classmethod
    def validate_source_text_has_content(cls, value: str) -> str:
        """Require content while preserving the submitted source text."""

        if not value.strip():
            msg = "source_text must contain non-whitespace content."
            raise ValueError(msg)
        return value

    @field_validator("created_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "created_at must be timezone-aware."
            raise ValueError(msg)
        return value
