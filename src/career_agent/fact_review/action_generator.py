from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionType,
    FactReviewMessage,
    FactReviewRecommendedAction,
    FactReviewThread,
)
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
)


class GeneratedFactReviewAction(BaseModel):
    """Structured fact review action proposal returned by a generator."""

    action_type: FactReviewActionType = Field(
        description="Structured deterministic action type to propose.",
    )
    rationale: str | None = Field(
        default=None,
        description="Brief rationale for the proposed action.",
    )
    source_message_ids: list[str] = Field(
        description="Fact review message ids that justify this action.",
    )
    revised_text: str | None = Field(
        default=None,
        description="Replacement fact text for revise_fact proposals.",
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
    constraint_scope_type: ConstraintScopeType | None = Field(
        default=None,
        description="Scope type for propose_constraint proposals.",
    )
    constraint_scope_id: str | None = Field(
        default=None,
        description="Scope id for role and fact propose_constraint proposals.",
    )
    constraint_type: ConstraintType | None = Field(
        default=None,
        description="Constraint type for propose_constraint proposals.",
    )
    rule_text: str | None = Field(
        default=None,
        description="Rule or preference text for propose_constraint proposals.",
    )

    @field_validator(
        "rationale",
        "revised_text",
        "constraint_scope_id",
        "rule_text",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim optional text fields before normal Pydantic validation."""

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
    def normalize_list_values(cls, values: Any) -> list[str]:
        """Trim list values and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]

    @model_validator(mode="after")
    def validate_action_shape(self) -> GeneratedFactReviewAction:
        """Enforce proposal fields required by each generated action type."""

        if not self.source_message_ids:
            msg = "Generated fact review actions require source_message_ids."
            raise ValueError(msg)

        if self.action_type == FactReviewActionType.REVISE_FACT and self.revised_text is None:
            msg = "revise_fact proposals require revised_text."
            raise ValueError(msg)

        if (
            self.action_type == FactReviewActionType.ADD_EVIDENCE
            and not self.source_ids
            and not self.question_ids
            and not self.message_ids
        ):
            msg = "add_evidence proposals require at least one evidence reference."
            raise ValueError(msg)

        if self.action_type == FactReviewActionType.PROPOSE_CONSTRAINT:
            self._validate_constraint_proposal()

        return self

    def _validate_constraint_proposal(self) -> None:
        """Validate constraint proposal fields."""

        if self.constraint_scope_type is None:
            msg = "propose_constraint proposals require constraint_scope_type."
            raise ValueError(msg)

        if self.constraint_type is None:
            msg = "propose_constraint proposals require constraint_type."
            raise ValueError(msg)

        if self.rule_text is None:
            msg = "propose_constraint proposals require rule_text."
            raise ValueError(msg)

        if (
            self.constraint_scope_type == ConstraintScopeType.GLOBAL
            and self.constraint_scope_id is not None
        ):
            msg = "global constraint proposals cannot have constraint_scope_id."
            raise ValueError(msg)

        if (
            self.constraint_scope_type != ConstraintScopeType.GLOBAL
            and self.constraint_scope_id is None
        ):
            msg = (
                f"{self.constraint_scope_type.value} constraint proposals "
                "require constraint_scope_id."
            )
            raise ValueError(msg)


class FactReviewActionGenerator(Protocol):
    """Generates structured fact review action proposals."""

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

    def generate_actions(
        self,
        role: ExperienceRole,
        fact: ExperienceFact,
        thread: FactReviewThread,
        messages: list[FactReviewMessage],
        existing_actions: list[FactReviewAction],
        constraints: list[ScopedConstraint],
    ) -> list[GeneratedFactReviewAction]:
        """Return proposed fact review actions."""


class DeterministicFactReviewActionGenerator:
    """Deterministic action generator for local review workflow validation."""

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

        return "deterministic"

    def generate_actions(
        self,
        role: ExperienceRole,
        fact: ExperienceFact,
        thread: FactReviewThread,
        messages: list[FactReviewMessage],
        existing_actions: list[FactReviewAction],
        constraints: list[ScopedConstraint],
    ) -> list[GeneratedFactReviewAction]:
        """Return a simple proposal from explicit message recommendation metadata."""

        del role, fact, thread, existing_actions, constraints
        recommendation_map = {
            FactReviewRecommendedAction.ACTIVATE_FACT: FactReviewActionType.ACTIVATE_FACT,
            FactReviewRecommendedAction.REJECT_FACT: FactReviewActionType.REJECT_FACT,
        }
        for message in reversed(messages):
            action_type = recommendation_map.get(message.recommended_action)
            if action_type is not None:
                return [
                    GeneratedFactReviewAction(
                        action_type=action_type,
                        rationale=(
                            "Deterministic proposal from fact review message "
                            "recommendation metadata."
                        ),
                        source_message_ids=[message.id],
                    )
                ]
        return []
