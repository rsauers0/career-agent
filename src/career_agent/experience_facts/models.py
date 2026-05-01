from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ExperienceFactStatus(StrEnum):
    """Lifecycle status for an experience fact."""

    DRAFT = "draft"
    NEEDS_CLARIFICATION = "needs_clarification"
    ACTIVE = "active"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class FactChangeActor(StrEnum):
    """Actor responsible for a fact change event."""

    USER = "user"
    LLM = "llm"
    SYSTEM = "system"


class FactChangeEventType(StrEnum):
    """Semantic event type for changes to experience facts."""

    CREATED = "created"
    REVISED = "revised"
    ACTIVATED = "activated"
    NEEDS_CLARIFICATION = "needs_clarification"
    RETURNED_TO_DRAFT = "returned_to_draft"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"
    EVIDENCE_ADDED = "evidence_added"


class ExperienceFact(BaseModel):
    """Durable experience fact derived from role context and source material."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this experience fact.",
    )
    role_id: str = Field(
        min_length=1,
        description="Identifier of the experience role this fact belongs to.",
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="Source entry identifiers used to support or derive this fact.",
    )
    question_ids: list[str] = Field(
        default_factory=list,
        description="Clarification question identifiers used to support or derive this fact.",
    )
    message_ids: list[str] = Field(
        default_factory=list,
        description="Clarification message identifiers used to support or derive this fact.",
    )
    text: str = Field(
        min_length=1,
        description="Normalized experience fact text for this role.",
    )
    details: list[str] = Field(
        default_factory=list,
        description=(
            "Optional second-level details that clarify the fact without changing its meaning."
        ),
    )
    systems: list[str] = Field(
        default_factory=list,
        description=(
            "Referenced systems, platforms, applications, or environments named by this fact."
        ),
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Referenced skills, tools, technologies, or methods named by this fact.",
    )
    functions: list[str] = Field(
        default_factory=list,
        description="Referenced duties, functions, or work categories named by this fact.",
    )
    supersedes_fact_id: str | None = Field(
        default=None,
        description="Prior fact identifier this fact replaces or revises.",
    )
    superseded_by_fact_id: str | None = Field(
        default=None,
        description="Later fact identifier that replaces or revises this fact.",
    )
    status: ExperienceFactStatus = Field(
        default=ExperienceFactStatus.DRAFT,
        description="Lifecycle status for this fact.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator(
        "role_id",
        "text",
        "supersedes_fact_id",
        "superseded_by_fact_id",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator(
        "source_ids",
        "question_ids",
        "message_ids",
        "details",
        "systems",
        "skills",
        "functions",
        mode="before",
    )
    @classmethod
    def normalize_list_values(cls, values: list[str] | None) -> list[str]:
        """Trim list values and discard blank entries."""

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


class FactChangeEvent(BaseModel):
    """Semantic history event for an experience fact."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this fact change event.",
    )
    fact_id: str = Field(
        min_length=1,
        description="Experience fact identifier this event belongs to.",
    )
    role_id: str = Field(
        min_length=1,
        description="Experience role identifier for this event.",
    )
    event_type: FactChangeEventType = Field(
        description="Semantic type of fact change recorded by this event.",
    )
    actor: FactChangeActor = Field(
        description="Actor responsible for the fact change.",
    )
    summary: str | None = Field(
        default=None,
        description="Human-readable reason or summary for the change.",
    )
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="Clarification message ids that caused or support this change.",
    )
    from_status: ExperienceFactStatus | None = Field(
        default=None,
        description="Prior fact lifecycle status, when applicable.",
    )
    to_status: ExperienceFactStatus | None = Field(
        default=None,
        description="New fact lifecycle status, when applicable.",
    )
    related_fact_id: str | None = Field(
        default=None,
        description="Related fact identifier, such as a superseded or superseding fact.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator(
        "fact_id",
        "role_id",
        "summary",
        "related_fact_id",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("source_message_ids", mode="before")
    @classmethod
    def normalize_source_message_ids(cls, values: list[str] | None) -> list[str]:
        """Trim source message ids and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]

    @field_validator("created_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value
