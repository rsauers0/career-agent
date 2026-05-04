from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


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
