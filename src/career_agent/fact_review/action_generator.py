from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from career_agent.errors import InvalidLLMOutputError
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionType,
    FactReviewMessage,
    FactReviewRecommendedAction,
    FactReviewThread,
)
from career_agent.llm.client import LLMClient
from career_agent.llm.models import LLMRequest
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


class LLMFactReviewActionGenerator:
    """LLM-backed fact review action generator with strict output validation."""

    _ACTION_LIST_ADAPTER = TypeAdapter(list[GeneratedFactReviewAction])

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        self.llm_client = llm_client
        self.model = model
        self.temperature = temperature

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

        return "llm"

    def generate_actions(
        self,
        role: ExperienceRole,
        fact: ExperienceFact,
        thread: FactReviewThread,
        messages: list[FactReviewMessage],
        existing_actions: list[FactReviewAction],
        constraints: list[ScopedConstraint],
    ) -> list[GeneratedFactReviewAction]:
        """Generate fact review action proposals from LLM JSON output."""

        request = LLMRequest(
            system_prompt=self._build_system_prompt(),
            user_prompt=self._build_user_prompt(
                role=role,
                fact=fact,
                thread=thread,
                messages=messages,
                existing_actions=existing_actions,
                constraints=constraints,
            ),
            model=self.model,
            temperature=self.temperature,
        )
        response = self.llm_client.complete(request)
        actions = self._parse_actions(response.content)
        self._validate_actions(actions=actions, messages=messages)
        return actions

    def _parse_actions(self, content: str) -> list[GeneratedFactReviewAction]:
        """Parse raw LLM response content into generated action proposals."""

        normalized_content = self._normalize_json_content(content)
        try:
            payload = json.loads(normalized_content)
        except json.JSONDecodeError as exc:
            msg = "LLM response must be valid JSON."
            raise InvalidLLMOutputError(msg) from exc

        if isinstance(payload, dict) and "actions" in payload:
            payload = payload["actions"]

        try:
            return self._ACTION_LIST_ADAPTER.validate_python(payload)
        except ValidationError as exc:
            msg = "LLM response does not match the fact review action contract."
            raise InvalidLLMOutputError(msg) from exc

    def _normalize_json_content(self, content: str) -> str:
        """Normalize common model JSON wrappers before strict JSON parsing."""

        normalized = content.strip()
        lines = normalized.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"}:
            if lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return normalized

    def _validate_actions(
        self,
        actions: list[GeneratedFactReviewAction],
        messages: list[FactReviewMessage],
    ) -> None:
        """Validate generated action proposals against review message context."""

        message_ids = {message.id for message in messages}
        seen_keys: set[
            tuple[
                str,
                str | None,
                tuple[str, ...],
                tuple[str, ...],
                tuple[str, ...],
                str | None,
                str | None,
                str | None,
                str | None,
            ]
        ] = set()
        for action in actions:
            for message_id in action.source_message_ids:
                if message_id not in message_ids:
                    msg = f"LLM response referenced unknown review message id: {message_id}"
                    raise InvalidLLMOutputError(msg)

            key = self._action_key(action)
            if key in seen_keys:
                msg = "LLM response contains duplicate fact review actions."
                raise InvalidLLMOutputError(msg)
            seen_keys.add(key)

    def _action_key(
        self,
        action: GeneratedFactReviewAction,
    ) -> tuple[
        str,
        str | None,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        """Return a semantic duplicate key for a generated action proposal."""

        return (
            action.action_type.value,
            action.revised_text,
            tuple(action.source_ids),
            tuple(action.question_ids),
            tuple(action.message_ids),
            action.constraint_scope_type.value if action.constraint_scope_type else None,
            action.constraint_scope_id,
            action.constraint_type.value if action.constraint_type else None,
            action.rule_text,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for fact review action generation."""

        return (
            "You generate structured action proposals for reviewing normalized career "
            "experience facts. Return only JSON. The JSON must be an object with an "
            "'actions' array. Each action must include action_type, rationale, "
            "source_message_ids, revised_text, source_ids, question_ids, message_ids, "
            "constraint_scope_type, constraint_scope_id, constraint_type, and rule_text. "
            "Allowed action_type values are activate_fact, reject_fact, revise_fact, "
            "add_evidence, and propose_constraint. Do not output split_fact. Return "
            '{"actions": []} when no deterministic action is justified. Every action '
            "must reference at least one review message id in source_message_ids. This "
            "is fact normalization review, not resume writing. Do not add duties, "
            "metrics, scope, systems, tools, seniority, or complexity that are not "
            "grounded in the fact or review messages. Activation is appropriate only "
            "when the user clearly approves the fact or the thread clearly establishes "
            "that it is ready. Constraint proposals should be durable user rules or "
            "preferences, not ordinary wording suggestions. Do not wrap JSON in "
            "Markdown fences."
        )

    def _build_user_prompt(
        self,
        role: ExperienceRole,
        fact: ExperienceFact,
        thread: FactReviewThread,
        messages: list[FactReviewMessage],
        existing_actions: list[FactReviewAction],
        constraints: list[ScopedConstraint],
    ) -> str:
        """Build the user prompt from role, fact, review, and constraint context."""

        message_blocks = "\n\n".join(
            (
                f"Message ID: {message.id}\n"
                f"Author: {message.author.value}\n"
                f"Recommended Action: {message.recommended_action.value}\n"
                f"Message Text: {message.message_text}"
            )
            for message in messages
        )
        existing_action_blocks = "\n\n".join(
            (
                f"Action ID: {action.id}\n"
                f"Type: {action.action_type.value}\n"
                f"Status: {action.status.value}\n"
                f"Review Message IDs: {', '.join(action.source_message_ids) or '-'}\n"
                f"Rationale: {action.rationale or '-'}"
            )
            for action in existing_actions
        )
        constraint_blocks = "\n\n".join(
            (
                f"Constraint ID: {constraint.id}\n"
                f"Scope Type: {constraint.scope_type.value}\n"
                f"Scope ID: {constraint.scope_id or '-'}\n"
                f"Constraint Type: {constraint.constraint_type.value}\n"
                f"Rule Text: {constraint.rule_text}"
            )
            for constraint in constraints
        )
        return (
            f"Role ID: {role.id}\n"
            f"Employer: {role.employer_name}\n"
            f"Job Title: {role.job_title}\n"
            f"Role Focus: {role.role_focus or '-'}\n\n"
            f"Fact Review Thread ID: {thread.id}\n"
            f"Thread Status: {thread.status.value}\n\n"
            f"Fact ID: {fact.id}\n"
            f"Fact Status: {fact.status.value}\n"
            f"Fact Text: {fact.text}\n"
            f"Details: {' | '.join(fact.details) or '-'}\n"
            f"Source IDs: {', '.join(fact.source_ids) or '-'}\n"
            f"Question IDs: {', '.join(fact.question_ids) or '-'}\n"
            f"Message IDs: {', '.join(fact.message_ids) or '-'}\n"
            f"Systems: {', '.join(fact.systems) or '-'}\n"
            f"Skills: {', '.join(fact.skills) or '-'}\n"
            f"Functions: {', '.join(fact.functions) or '-'}\n\n"
            "Review messages:\n"
            f"{message_blocks or '-'}\n\n"
            "Existing review actions:\n"
            f"{existing_action_blocks or '-'}\n\n"
            "Applicable active constraints:\n"
            f"{constraint_blocks or '-'}"
        )
