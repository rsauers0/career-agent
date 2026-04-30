from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry


class GeneratedSourceQuestion(BaseModel):
    """Structured source clarification question proposal."""

    question_text: str = Field(
        min_length=1,
        description="Clarification question text to save for source analysis.",
    )
    relevant_source_ids: list[str] = Field(
        default_factory=list,
        description="Source ids that should be associated with this question.",
    )

    @field_validator("question_text", mode="before")
    @classmethod
    def normalize_question_text(cls, value: str) -> str:
        """Trim question text before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("relevant_source_ids", mode="before")
    @classmethod
    def normalize_relevant_source_ids(cls, values: list[str] | None) -> list[str]:
        """Trim source ids and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]


class SourceQuestionGenerator(Protocol):
    """Generates structured source clarification question proposals."""

    def generate_questions(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
    ) -> list[GeneratedSourceQuestion]:
        """Return proposed source clarification questions."""


class DeterministicSourceQuestionGenerator:
    """Deterministic source question generator for dev workflow validation."""

    def generate_questions(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
    ) -> list[GeneratedSourceQuestion]:
        """Return placeholder questions without calling an LLM."""

        source_ids = [source.id for source in sources]
        role_label = f"{role.job_title} at {role.employer_name}"
        return [
            GeneratedSourceQuestion(
                question_text=(
                    f"DEV PLACEHOLDER: For {role_label}, what measurable impact, "
                    "outcome, or business value should be clarified from this source material?"
                ),
                relevant_source_ids=source_ids,
            ),
            GeneratedSourceQuestion(
                question_text=(
                    f"DEV PLACEHOLDER: For {role_label}, are there tools, technologies, "
                    "stakeholders, or scope details that should be captured before bullet "
                    "generation?"
                ),
                relevant_source_ids=source_ids,
            ),
        ]
