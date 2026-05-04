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
from career_agent.llm.client import LLMClient
from career_agent.llm.models import LLMRequest
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.source_analysis.models import (
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceFindingType,
)


class GeneratedSourceFinding(BaseModel):
    """Structured source finding proposal returned by a generator."""

    source_id: str = Field(
        min_length=1,
        description="Source id evaluated by this finding.",
    )
    finding_type: SourceFindingType = Field(
        description="Structured source finding type.",
    )
    fact_id: str | None = Field(
        default=None,
        description="Existing fact id being compared, when applicable.",
    )
    proposed_fact_text: str | None = Field(
        default=None,
        description="Candidate normalized fact text for new_fact findings.",
    )
    rationale: str | None = Field(
        default=None,
        description="Brief rationale for the finding.",
    )

    @field_validator(
        "source_id",
        "fact_id",
        "proposed_fact_text",
        "rationale",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_finding_shape(self) -> GeneratedSourceFinding:
        """Enforce the finding fields required by each generated finding type."""

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

        return self


class SourceFindingGenerator(Protocol):
    """Generates structured source finding proposals."""

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

    def generate_findings(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
        questions: list[SourceClarificationQuestion],
        messages: list[SourceClarificationMessage],
        facts: list[ExperienceFact],
    ) -> list[GeneratedSourceFinding]:
        """Return proposed source findings."""


class DeterministicSourceFindingGenerator:
    """Deterministic source finding generator for local workflow validation only."""

    @property
    def generator_name(self) -> str:
        """Return a short display name for this generator."""

        return "deterministic"

    def generate_findings(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
        questions: list[SourceClarificationQuestion],
        messages: list[SourceClarificationMessage],
        facts: list[ExperienceFact],
    ) -> list[GeneratedSourceFinding]:
        """Return placeholder findings without semantic source parsing."""

        del role, questions, messages, facts
        return [
            GeneratedSourceFinding(
                source_id=source.id,
                finding_type=SourceFindingType.UNCLEAR,
                rationale=(
                    "Deterministic placeholder; use the LLM finding generator "
                    "for semantic source analysis."
                ),
            )
            for source in sources
        ]


class LLMSourceFindingGenerator:
    """LLM-backed source finding generator with strict output validation."""

    _FINDING_LIST_ADAPTER = TypeAdapter(list[GeneratedSourceFinding])

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

    def generate_findings(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
        questions: list[SourceClarificationQuestion],
        messages: list[SourceClarificationMessage],
        facts: list[ExperienceFact],
    ) -> list[GeneratedSourceFinding]:
        """Generate source findings from LLM JSON output."""

        request = LLMRequest(
            system_prompt=self._build_system_prompt(),
            user_prompt=self._build_user_prompt(
                role=role,
                sources=sources,
                questions=questions,
                messages=messages,
                facts=facts,
            ),
            model=self.model,
            temperature=self.temperature,
        )
        response = self.llm_client.complete(request)
        findings = self._parse_findings(response.content)
        self._validate_findings(findings=findings, sources=sources, facts=facts)
        return findings

    def _parse_findings(self, content: str) -> list[GeneratedSourceFinding]:
        """Parse raw LLM response content into generated finding proposals."""

        normalized_content = self._normalize_json_content(content)
        try:
            payload = json.loads(normalized_content)
        except json.JSONDecodeError as exc:
            msg = "LLM response must be valid JSON."
            raise InvalidLLMOutputError(msg) from exc

        if isinstance(payload, dict) and "findings" in payload:
            payload = payload["findings"]

        try:
            return self._FINDING_LIST_ADAPTER.validate_python(payload)
        except ValidationError as exc:
            msg = "LLM response does not match the source finding contract."
            raise InvalidLLMOutputError(msg) from exc

    def _normalize_json_content(self, content: str) -> str:
        """Normalize common model JSON wrappers before strict JSON parsing."""

        normalized = content.strip()
        lines = normalized.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"}:
            if lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return normalized

    def _validate_findings(
        self,
        findings: list[GeneratedSourceFinding],
        sources: list[RoleSourceEntry],
        facts: list[ExperienceFact],
    ) -> None:
        """Validate generated findings against available run context."""

        if not findings:
            msg = "LLM response must include at least one finding."
            raise InvalidLLMOutputError(msg)

        source_ids = {source.id for source in sources}
        fact_ids = {fact.id for fact in facts}
        seen_keys: set[tuple[str, str, str | None, str | None]] = set()
        for finding in findings:
            if finding.source_id not in source_ids:
                msg = f"LLM response referenced unknown source id: {finding.source_id}"
                raise InvalidLLMOutputError(msg)
            if finding.fact_id is not None and finding.fact_id not in fact_ids:
                msg = f"LLM response referenced unknown fact id: {finding.fact_id}"
                raise InvalidLLMOutputError(msg)

            key = (
                finding.source_id,
                finding.finding_type.value,
                finding.fact_id,
                finding.proposed_fact_text,
            )
            if key in seen_keys:
                msg = "LLM response contains duplicate source findings."
                raise InvalidLLMOutputError(msg)
            seen_keys.add(key)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for source finding generation."""

        return (
            "You perform grounded career evidence normalization. Return only JSON. "
            "The JSON must be an object with a 'findings' array. Each item must contain "
            "'source_id', 'finding_type', 'fact_id', 'proposed_fact_text', and 'rationale'. "
            "Allowed finding_type values are supports_fact, revises_fact, contradicts_fact, "
            "duplicates_fact, new_fact, unclear, and unrelated. This is not resume writing. "
            "Do not create persuasive bullets. Do not inflate scope, complexity, metrics, "
            "seniority, or impact. One source may produce many findings. Keep separate work "
            "items separate. Merge only when the source evidence clearly describes the same "
            "work, project or process, metric context, and outcome. Use generic terminology. "
            "Use unclear when evidence is insufficient. Do not wrap JSON in Markdown fences."
        )

    def _build_user_prompt(
        self,
        role: ExperienceRole,
        sources: list[RoleSourceEntry],
        questions: list[SourceClarificationQuestion],
        messages: list[SourceClarificationMessage],
        facts: list[ExperienceFact],
    ) -> str:
        """Build the user prompt from role, source, clarification, and fact context."""

        source_blocks = "\n\n".join(
            f"Source ID: {source.id}\nSource Text:\n{source.source_text}" for source in sources
        )
        question_blocks = "\n\n".join(
            (
                f"Question ID: {question.id}\n"
                f"Status: {question.status.value}\n"
                f"Relevant Source IDs: {', '.join(question.relevant_source_ids) or '-'}\n"
                f"Question Text: {question.question_text}"
            )
            for question in questions
        )
        message_blocks = "\n\n".join(
            (
                f"Message ID: {message.id}\n"
                f"Question ID: {message.question_id}\n"
                f"Author: {message.author.value}\n"
                f"Message Text: {message.message_text}"
            )
            for message in messages
        )
        fact_blocks = "\n\n".join(
            (
                f"Fact ID: {fact.id}\n"
                f"Status: {fact.status.value}\n"
                f"Source IDs: {', '.join(fact.source_ids) or '-'}\n"
                f"Question IDs: {', '.join(fact.question_ids) or '-'}\n"
                f"Message IDs: {', '.join(fact.message_ids) or '-'}\n"
                f"Fact Text: {fact.text}\n"
                f"Details: {' | '.join(fact.details) or '-'}"
            )
            for fact in facts
        )
        return (
            f"Role ID: {role.id}\n"
            f"Employer: {role.employer_name}\n"
            f"Job Title: {role.job_title}\n"
            f"Role Focus: {role.role_focus or '-'}\n\n"
            "Analyze the source evidence and clarification context. Produce structured "
            "source findings only. If an existing fact is supported, revised, contradicted, "
            "or duplicated, include fact_id. If the source supports a distinct new fact, "
            "use finding_type new_fact and provide grounded proposed_fact_text. If the "
            "relationship is not safe to classify, use unclear. If the source is unrelated "
            "to experience facts, use unrelated.\n\n"
            f"Sources:\n{source_blocks or '-'}\n\n"
            f"Clarification Questions:\n{question_blocks or '-'}\n\n"
            f"Clarification Messages:\n{message_blocks or '-'}\n\n"
            f"Existing Facts:\n{fact_blocks or '-'}"
        )
