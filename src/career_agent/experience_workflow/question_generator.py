from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator

from career_agent.errors import InvalidLLMOutputError
from career_agent.experience_roles.models import ExperienceRole
from career_agent.llm.client import LLMClient
from career_agent.llm.models import LLMRequest
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

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

    def generate_questions(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
    ) -> list[GeneratedSourceQuestion]:
        """Return proposed source clarification questions."""


class DeterministicSourceQuestionGenerator:
    """Deterministic source question generator for dev workflow validation."""

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

        return "deterministic"

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
                    "stakeholders, or scope details that should be captured before fact "
                    "generation?"
                ),
                relevant_source_ids=source_ids,
            ),
        ]


class LLMSourceQuestionGenerator:
    """LLM-backed source question generator with strict output validation."""

    _QUESTION_LIST_ADAPTER = TypeAdapter(list[GeneratedSourceQuestion])

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.llm_client = llm_client
        self.model = model
        self.temperature = temperature

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

        return "llm"

    def generate_questions(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
    ) -> list[GeneratedSourceQuestion]:
        """Generate source clarification questions from LLM JSON output."""

        request = LLMRequest(
            system_prompt=self._build_system_prompt(),
            user_prompt=self._build_user_prompt(role=role, sources=sources),
            model=self.model,
            temperature=self.temperature,
        )
        response = self.llm_client.complete(request)
        questions = self._parse_questions(response.content)
        self._validate_questions(questions=questions, sources=sources)
        return questions

    def _parse_questions(self, content: str) -> list[GeneratedSourceQuestion]:
        """Parse raw LLM response content into generated question proposals."""

        normalized_content = self._normalize_json_content(content)
        try:
            payload = json.loads(normalized_content)
        except json.JSONDecodeError as exc:
            msg = "LLM response must be valid JSON."
            raise InvalidLLMOutputError(msg) from exc

        if isinstance(payload, dict) and "questions" in payload:
            payload = payload["questions"]

        try:
            return self._QUESTION_LIST_ADAPTER.validate_python(payload)
        except ValidationError as exc:
            msg = "LLM response does not match the source question contract."
            raise InvalidLLMOutputError(msg) from exc

    def _normalize_json_content(self, content: str) -> str:
        """Normalize common model JSON wrappers before strict JSON parsing."""

        normalized = content.strip()
        lines = normalized.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"}:
            if lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return normalized

    def _validate_questions(
        self,
        questions: list[GeneratedSourceQuestion],
        sources: list[RoleSourceEntry],
    ) -> None:
        """Validate generated question proposals against source context."""

        if not questions:
            msg = "LLM response must include at least one question."
            raise InvalidLLMOutputError(msg)

        source_ids = {source.id for source in sources}
        for question in questions:
            for source_id in question.relevant_source_ids:
                if source_id not in source_ids:
                    msg = f"LLM response referenced unknown source id: {source_id}"
                    raise InvalidLLMOutputError(msg)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for source clarification question generation."""

        return (
            "You generate concise clarification questions for career source analysis. "
            "Return only JSON. The JSON must be an object with a 'questions' array. "
            "Each item must contain 'question_text' and 'relevant_source_ids'. "
            "Do not wrap the JSON in Markdown code fences."
        )

    def _build_user_prompt(self, role: ExperienceRole, sources: list[RoleSourceEntry]) -> str:
        """Build the user prompt from role facts and source material."""

        source_blocks = "\n\n".join(
            f"Source ID: {source.id}\nSource Text:\n{source.source_text}" for source in sources
        )
        return (
            f"Role ID: {role.id}\n"
            f"Employer: {role.employer_name}\n"
            f"Job Title: {role.job_title}\n"
            f"Role Focus: {role.role_focus or '-'}\n\n"
            "Generate clarification questions for the source material below. "
            "Questions should help turn vague duties into accurate, accomplishment-oriented "
            "career evidence.\n\n"
            f"{source_blocks}"
        )
