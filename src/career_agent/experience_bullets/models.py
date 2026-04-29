from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ExperienceBulletStatus(StrEnum):
    """Lifecycle status for an experience bullet."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExperienceBullet(BaseModel):
    """Durable resume-style bullet derived from role context and source material."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this experience bullet.",
    )
    role_id: str = Field(
        min_length=1,
        description="Identifier of the experience role this bullet belongs to.",
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="Source entry identifiers used to support or derive this bullet.",
    )
    text: str = Field(
        min_length=1,
        description="Resume-style bullet text for this role.",
    )
    status: ExperienceBulletStatus = Field(
        default=ExperienceBulletStatus.DRAFT,
        description="Lifecycle status for this bullet.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("role_id", "text", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source_ids", mode="before")
    @classmethod
    def normalize_source_ids(cls, values: list[str] | None) -> list[str]:
        """Trim source ids and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value
