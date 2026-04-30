from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SourceAnalysisStatus(StrEnum):
    """Lifecycle status for a source analysis run."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SourceClarificationQuestionStatus(StrEnum):
    """Resolution status for a source clarification question."""

    OPEN = "open"
    RESOLVED = "resolved"
    SKIPPED = "skipped"


class ClarificationMessageAuthor(StrEnum):
    """Author of a clarification thread message."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class SourceAnalysisRun(BaseModel):
    """One analysis attempt over source material for an experience role."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this source analysis run.",
    )
    role_id: str = Field(
        min_length=1,
        description="Identifier of the experience role being analyzed.",
    )
    source_ids: list[str] = Field(
        min_length=1,
        description="Source entry identifiers included in this analysis run.",
    )
    status: SourceAnalysisStatus = Field(
        default=SourceAnalysisStatus.ACTIVE,
        description="Lifecycle status for this source analysis run.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("role_id", mode="before")
    @classmethod
    def normalize_role_id(cls, value: str) -> str:
        """Trim role ids before normal Pydantic validation."""

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


class SourceClarificationQuestion(BaseModel):
    """Question created during a source analysis run."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this clarification question.",
    )
    analysis_run_id: str = Field(
        min_length=1,
        description="Identifier of the source analysis run this question belongs to.",
    )
    question_text: str = Field(
        min_length=1,
        description="Clarification question text.",
    )
    relevant_source_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Optional source entry identifiers that motivated this question. "
            "Empty means the question is general or source attribution was not provided."
        ),
    )
    status: SourceClarificationQuestionStatus = Field(
        default=SourceClarificationQuestionStatus.OPEN,
        description="Resolution status for this clarification question.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("analysis_run_id", "question_text", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("relevant_source_ids", mode="before")
    @classmethod
    def normalize_relevant_source_ids(cls, values: list[str] | None) -> list[str]:
        """Trim relevant source ids and discard blank entries."""

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


class SourceClarificationMessage(BaseModel):
    """One message in a source clarification question thread."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this clarification message.",
    )
    question_id: str = Field(
        min_length=1,
        description="Identifier of the clarification question this message belongs to.",
    )
    author: ClarificationMessageAuthor = Field(
        description="Original author of this clarification message.",
    )
    message_text: str = Field(
        min_length=1,
        description="Message text for this clarification thread entry.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("question_id", "message_text", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("created_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "created_at must be timezone-aware."
            raise ValueError(msg)
        return value
