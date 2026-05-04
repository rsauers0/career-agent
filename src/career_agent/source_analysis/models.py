from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


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


class SourceFindingType(StrEnum):
    """Structured source analysis finding type."""

    SUPPORTS_FACT = "supports_fact"
    REVISES_FACT = "revises_fact"
    CONTRADICTS_FACT = "contradicts_fact"
    DUPLICATES_FACT = "duplicates_fact"
    NEW_FACT = "new_fact"
    UNCLEAR = "unclear"
    UNRELATED = "unrelated"


class SourceFindingStatus(StrEnum):
    """Lifecycle status for a structured source finding."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    APPLIED = "applied"
    REJECTED = "rejected"
    ARCHIVED = "archived"


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
    def normalize_role_id(cls, value: Any) -> Any:
        """Trim role ids before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source_ids", mode="before")
    @classmethod
    def normalize_source_ids(cls, values: Any) -> list[str]:
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
    def normalize_required_text(cls, value: Any) -> Any:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("relevant_source_ids", mode="before")
    @classmethod
    def normalize_relevant_source_ids(cls, values: Any) -> list[str]:
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
    def normalize_required_text(cls, value: Any) -> Any:
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


class SourceFinding(BaseModel):
    """Structured analysis finding about what a source appears to mean."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this source finding.",
    )
    analysis_run_id: str = Field(
        min_length=1,
        description="Identifier of the source analysis run that produced the finding.",
    )
    role_id: str = Field(
        min_length=1,
        description="Experience role identifier for this finding.",
    )
    source_id: str = Field(
        min_length=1,
        description="Source entry identifier evaluated by this finding.",
    )
    fact_id: str | None = Field(
        default=None,
        description="Existing experience fact identifier being compared, when applicable.",
    )
    finding_type: SourceFindingType = Field(
        description="Structured type for this source finding.",
    )
    proposed_fact_text: str | None = Field(
        default=None,
        description="Candidate normalized fact text when the finding proposes a new fact.",
    )
    rationale: str | None = Field(
        default=None,
        description="Brief explanation for the finding.",
    )
    applied_fact_id: str | None = Field(
        default=None,
        description="Experience fact id created or updated when this finding is applied.",
    )
    status: SourceFindingStatus = Field(
        default=SourceFindingStatus.PROPOSED,
        description="Lifecycle status for this source finding.",
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
        "analysis_run_id",
        "role_id",
        "source_id",
        "fact_id",
        "proposed_fact_text",
        "rationale",
        "applied_fact_id",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_finding_shape(self) -> SourceFinding:
        """Enforce the finding fields required by each finding type."""

        fact_comparison_types = {
            SourceFindingType.SUPPORTS_FACT,
            SourceFindingType.REVISES_FACT,
            SourceFindingType.CONTRADICTS_FACT,
            SourceFindingType.DUPLICATES_FACT,
        }
        if self.finding_type in fact_comparison_types and self.fact_id is None:
            msg = f"{self.finding_type.value} findings require fact_id."
            raise ValueError(msg)

        if self.finding_type == SourceFindingType.NEW_FACT:
            if self.fact_id is not None:
                msg = "new_fact findings cannot reference an existing fact_id."
                raise ValueError(msg)
            if self.proposed_fact_text is None:
                msg = "new_fact findings require proposed_fact_text."
                raise ValueError(msg)

        if self.status == SourceFindingStatus.APPLIED and self.applied_fact_id is None:
            msg = "applied findings require applied_fact_id."
            raise ValueError(msg)

        return self
