from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ConstraintScopeType(StrEnum):
    """Supported scopes for reusable workflow constraints."""

    GLOBAL = "global"
    ROLE = "role"
    FACT = "fact"


class ConstraintType(StrEnum):
    """How strongly a scoped constraint should guide generation."""

    HARD_RULE = "hard_rule"
    PREFERENCE = "preference"


class ScopedConstraintStatus(StrEnum):
    """Lifecycle status for a scoped constraint."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ScopedConstraint(BaseModel):
    """Durable user rule or preference scoped to a workflow context."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this scoped constraint.",
    )
    scope_type: ConstraintScopeType = Field(
        description="Scope where this constraint applies.",
    )
    scope_id: str | None = Field(
        default=None,
        description="Identifier for non-global scopes.",
    )
    constraint_type: ConstraintType = Field(
        description="Whether this constraint is a hard rule or preference.",
    )
    rule_text: str = Field(
        min_length=1,
        description="Plain-language rule or preference text.",
    )
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="Workflow message ids that caused or support this constraint.",
    )
    status: ScopedConstraintStatus = Field(
        default=ScopedConstraintStatus.PROPOSED,
        description="Lifecycle status for this scoped constraint.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("scope_id", "rule_text", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
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

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_scope_id(self) -> ScopedConstraint:
        """Validate scope id requirements for global and item scopes."""

        if self.scope_type == ConstraintScopeType.GLOBAL and self.scope_id is not None:
            msg = "global constraints cannot have scope_id."
            raise ValueError(msg)

        if self.scope_type != ConstraintScopeType.GLOBAL and self.scope_id is None:
            msg = f"{self.scope_type.value} constraints require scope_id."
            raise ValueError(msg)

        return self
