from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class FactReviewThreadStatus(StrEnum):
    """Lifecycle status for a fact review thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class FactReviewMessageAuthor(StrEnum):
    """Author of a fact review message."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class FactReviewRecommendedAction(StrEnum):
    """Optional action recommended by a fact review message."""

    REVISE_FACT = "revise_fact"
    ADD_EVIDENCE = "add_evidence"
    SPLIT_FACT = "split_fact"
    REJECT_FACT = "reject_fact"
    ACTIVATE_FACT = "activate_fact"
    PROPOSE_CONSTRAINT = "propose_constraint"
    NONE = "none"


class FactReviewActionType(StrEnum):
    """Structured fact mutation action proposed from review conversation."""

    ACTIVATE_FACT = "activate_fact"
    REJECT_FACT = "reject_fact"
    REVISE_FACT = "revise_fact"
    ADD_EVIDENCE = "add_evidence"


class FactReviewActionStatus(StrEnum):
    """Lifecycle status for a structured fact review action."""

    PROPOSED = "proposed"
    APPLIED = "applied"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class FactReviewThread(BaseModel):
    """Conversation thread for reviewing one experience fact."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this fact review thread.",
    )
    fact_id: str = Field(
        min_length=1,
        description="Experience fact identifier this thread reviews.",
    )
    role_id: str = Field(
        min_length=1,
        description="Experience role identifier for this review thread.",
    )
    status: FactReviewThreadStatus = Field(
        default=FactReviewThreadStatus.OPEN,
        description="Lifecycle status for this review thread.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("fact_id", "role_id", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value


class FactReviewMessage(BaseModel):
    """One message in a fact review thread."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this fact review message.",
    )
    thread_id: str = Field(
        min_length=1,
        description="Fact review thread identifier this message belongs to.",
    )
    author: FactReviewMessageAuthor = Field(
        description="Original author of this review message.",
    )
    message_text: str = Field(
        min_length=1,
        description="Message text for this review thread entry.",
    )
    recommended_action: FactReviewRecommendedAction = Field(
        default=FactReviewRecommendedAction.NONE,
        description="Optional recommended action from this message.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("thread_id", "message_text", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim text fields before normal Pydantic validation."""

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


class FactReviewAction(BaseModel):
    """Structured action proposed from a fact review thread."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this fact review action.",
    )
    thread_id: str = Field(
        min_length=1,
        description="Fact review thread identifier this action belongs to.",
    )
    fact_id: str = Field(
        min_length=1,
        description="Experience fact identifier this action targets.",
    )
    role_id: str = Field(
        min_length=1,
        description="Experience role identifier for this action.",
    )
    action_type: FactReviewActionType = Field(
        description="Structured deterministic action proposed by review.",
    )
    status: FactReviewActionStatus = Field(
        default=FactReviewActionStatus.PROPOSED,
        description="Lifecycle status for this action.",
    )
    rationale: str | None = Field(
        default=None,
        description="Human-readable rationale for the proposed action.",
    )
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="Fact review message ids that explain or caused this action.",
    )
    revised_text: str | None = Field(
        default=None,
        description="Replacement fact text for revise_fact actions.",
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="Role source ids to add or preserve while applying this action.",
    )
    question_ids: list[str] = Field(
        default_factory=list,
        description="Clarification question ids to add as evidence.",
    )
    message_ids: list[str] = Field(
        default_factory=list,
        description="Clarification message ids to add as evidence.",
    )
    applied_fact_id: str | None = Field(
        default=None,
        description="Fact id returned by deterministic application, when applied.",
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
        "thread_id",
        "fact_id",
        "role_id",
        "rationale",
        "revised_text",
        "applied_fact_id",
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
        "source_message_ids",
        "source_ids",
        "question_ids",
        "message_ids",
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

    @model_validator(mode="after")
    def validate_action_requirements(self) -> FactReviewAction:
        """Validate action-specific required fields."""

        if self.action_type == FactReviewActionType.REVISE_FACT and self.revised_text is None:
            msg = "revised_text is required for revise_fact actions."
            raise ValueError(msg)

        if (
            self.action_type == FactReviewActionType.ADD_EVIDENCE
            and not self.source_ids
            and not self.question_ids
            and not self.message_ids
        ):
            msg = "add_evidence actions require at least one evidence reference."
            raise ValueError(msg)

        if self.status == FactReviewActionStatus.APPLIED and self.applied_fact_id is None:
            msg = "applied_fact_id is required for applied actions."
            raise ValueError(msg)

        return self
