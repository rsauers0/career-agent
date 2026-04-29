from __future__ import annotations

import json
from importlib import resources
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError

from career_agent.config import Settings
from career_agent.domain.models import (
    CandidateBullet,
    CandidateBulletStatus,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceSourceEntry,
    IntakeQuestion,
)


def _load_prompt(filename: str) -> str:
    """Load a versioned prompt template bundled with the package."""

    return (
        resources.files("career_agent.infrastructure.prompts")
        .joinpath(filename)
        .read_text(encoding="utf-8")
        .strip()
    )


FOLLOW_UP_QUESTIONS_PROMPT_VERSION = "experience_follow_up_questions.v1"
DRAFT_CANDIDATE_BULLETS_PROMPT_VERSION = "experience_candidate_bullets.v1"
DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION = "experience_draft_entry.v1"

FOLLOW_UP_QUESTIONS_SYSTEM_PROMPT = _load_prompt(f"{FOLLOW_UP_QUESTIONS_PROMPT_VERSION}.md")
DRAFT_CANDIDATE_BULLETS_SYSTEM_PROMPT = _load_prompt(f"{DRAFT_CANDIDATE_BULLETS_PROMPT_VERSION}.md")
DRAFT_EXPERIENCE_ENTRY_SYSTEM_PROMPT = _load_prompt(f"{DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION}.md")


class FollowUpQuestionsResponse(BaseModel):
    """Structured response expected from the follow-up question prompt."""

    questions: list[IntakeQuestion] = Field(min_length=1, max_length=7)


class DraftExperienceEntryResponse(BaseModel):
    """Structured response expected from the draft experience entry prompt."""

    experience_entry: ExperienceEntry


class DraftCandidateBulletsResponse(BaseModel):
    """Structured response expected from the candidate bullet prompt."""

    candidate_bullets: list[CandidateBullet] = Field(min_length=1, max_length=12)


class OpenAICompatibleExperienceIntakeAssistant:
    """Experience intake assistant backed by an OpenAI-compatible chat API."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: SecretStr | str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30.0)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
    ) -> OpenAICompatibleExperienceIntakeAssistant:
        """Create an assistant from extraction LLM settings."""

        base_url = settings.effective_llm_extraction_base_url
        model = settings.effective_llm_extraction_model
        if not base_url:
            msg = "CAREER_AGENT_LLM_BASE_URL or CAREER_AGENT_LLM_EXTRACTION_BASE_URL is required."
            raise ValueError(msg)
        if not model:
            msg = "CAREER_AGENT_LLM_MODEL or CAREER_AGENT_LLM_EXTRACTION_MODEL is required."
            raise ValueError(msg)

        return cls(
            base_url=base_url,
            model=model,
            api_key=settings.effective_llm_extraction_api_key,
            client=client,
        )

    def generate_follow_up_questions(
        self,
        session: ExperienceIntakeSession,
    ) -> list[IntakeQuestion]:
        """Generate structured follow-up questions for one intake session."""

        if not session.source_text:
            msg = "Experience intake source text is required."
            raise ValueError(msg)

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._build_follow_up_questions_payload(session),
        )
        response.raise_for_status()

        content = self._extract_message_content(response.json())
        parsed = self._parse_follow_up_questions_response(content)
        return parsed.questions

    def generate_candidate_bullets(
        self,
        session: ExperienceIntakeSession,
        source_entries: list[ExperienceSourceEntry],
    ) -> list[CandidateBullet]:
        """Generate candidate bullets from pending source entries."""

        if not source_entries:
            msg = "Experience source entries are required."
            raise ValueError(msg)
        if not session.employer_name:
            msg = "Experience intake employer name is required."
            raise ValueError(msg)
        if not session.job_title:
            msg = "Experience intake job title is required."
            raise ValueError(msg)

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._build_candidate_bullets_payload(session, source_entries),
        )
        response.raise_for_status()

        content = self._extract_message_content(response.json())
        parsed = self._parse_candidate_bullets_response(content)
        return [
            bullet.model_copy(update={"status": CandidateBulletStatus.NEEDS_REVIEW})
            for bullet in parsed.candidate_bullets
        ]

    def draft_experience_entry(
        self,
        session: ExperienceIntakeSession,
    ) -> ExperienceEntry:
        """Draft a structured experience entry for one answered intake session."""

        if not session.source_text:
            msg = "Experience intake source text is required."
            raise ValueError(msg)
        if not session.employer_name:
            msg = "Experience intake employer name is required."
            raise ValueError(msg)
        if not session.job_title:
            msg = "Experience intake job title is required."
            raise ValueError(msg)
        if not session.user_answers:
            msg = "Experience intake answers are required."
            raise ValueError(msg)

        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._build_draft_experience_entry_payload(session),
        )
        response.raise_for_status()

        content = self._extract_message_content(response.json())
        parsed = self._parse_draft_experience_entry_response(content)
        return parsed.experience_entry

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            api_key = (
                self.api_key.get_secret_value()
                if isinstance(self.api_key, SecretStr)
                else self.api_key
            )
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    def _build_follow_up_questions_payload(
        self,
        session: ExperienceIntakeSession,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": FOLLOW_UP_QUESTIONS_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Prompt version: {FOLLOW_UP_QUESTIONS_PROMPT_VERSION}\n\n"
                        f"Experience intake session ID: {session.id}\n\n"
                        "Source text for one role:\n"
                        f"{session.source_text}"
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    def _build_candidate_bullets_payload(
        self,
        session: ExperienceIntakeSession,
        source_entries: list[ExperienceSourceEntry],
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": DRAFT_CANDIDATE_BULLETS_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Prompt version: {DRAFT_CANDIDATE_BULLETS_PROMPT_VERSION}\n\n"
                        f"Experience intake session ID: {session.id}\n\n"
                        "Role metadata:\n"
                        f"- Employer: {session.employer_name}\n"
                        f"- Job title: {session.job_title}\n"
                        f"- Location: {session.location or '-'}\n"
                        f"- Employment type: {session.employment_type or '-'}\n"
                        f"- Dates: {_format_session_dates(session)}\n\n"
                        "Existing candidate bullets:\n"
                        f"{_format_candidate_bullets(session)}\n\n"
                        "Pending source entries to analyze:\n"
                        f"{_format_source_entries(source_entries)}"
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    def _build_draft_experience_entry_payload(
        self,
        session: ExperienceIntakeSession,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": DRAFT_EXPERIENCE_ENTRY_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Prompt version: {DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION}\n\n"
                        f"Experience intake session ID: {session.id}\n\n"
                        "Role metadata:\n"
                        f"- Employer: {session.employer_name}\n"
                        f"- Job title: {session.job_title}\n\n"
                        "Source text for one role:\n"
                        f"{session.source_text}\n\n"
                        "Follow-up questions and user answers:\n"
                        f"{_format_question_answer_pairs(session)}"
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    def _extract_message_content(self, response_payload: dict[str, Any]) -> str:
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            msg = "LLM response did not contain choices[0].message.content."
            raise ValueError(msg) from error

        if not isinstance(content, str) or not content.strip():
            msg = "LLM response message content was empty."
            raise ValueError(msg)

        return content

    def _parse_follow_up_questions_response(
        self,
        content: str,
    ) -> FollowUpQuestionsResponse:
        try:
            payload = json.loads(_strip_json_fence(content))
            return FollowUpQuestionsResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            msg = "LLM response did not match the follow-up questions schema."
            raise ValueError(msg) from error

    def _parse_candidate_bullets_response(
        self,
        content: str,
    ) -> DraftCandidateBulletsResponse:
        try:
            payload = json.loads(_strip_json_fence(content))
            return DraftCandidateBulletsResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            msg = "LLM response did not match the candidate bullets schema."
            raise ValueError(msg) from error

    def _parse_draft_experience_entry_response(
        self,
        content: str,
    ) -> DraftExperienceEntryResponse:
        try:
            payload = json.loads(_strip_json_fence(content))
            return DraftExperienceEntryResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            msg = "LLM response did not match the draft experience entry schema."
            raise ValueError(msg) from error


def _format_question_answer_pairs(session: ExperienceIntakeSession) -> str:
    question_text_by_id = {
        question.id: question.question for question in session.follow_up_questions
    }
    lines = []
    for index, answer in enumerate(session.user_answers, start=1):
        question = question_text_by_id.get(answer.question_id, answer.question_id)
        lines.append(f"{index}. Question: {question}\n   Answer: {answer.answer}")

    return "\n".join(lines)


def _format_source_entries(source_entries: list[ExperienceSourceEntry]) -> str:
    lines = []
    for index, source_entry in enumerate(source_entries, start=1):
        lines.append(
            f"{index}. Source entry ID: {source_entry.id}\n   Content:\n{source_entry.content}"
        )

    return "\n\n".join(lines)


def _format_candidate_bullets(session: ExperienceIntakeSession) -> str:
    if not session.candidate_bullets:
        return "None."

    lines = []
    for index, bullet in enumerate(session.candidate_bullets, start=1):
        lines.append(
            f"{index}. ID: {bullet.id}\n"
            f"   Status: {bullet.status.value}\n"
            f"   Text: {bullet.text}\n"
            f"   Source entry IDs: {', '.join(bullet.source_entry_ids) or '-'}"
        )

    return "\n".join(lines)


def _format_session_dates(session: ExperienceIntakeSession) -> str:
    start_date = session.start_date.model_dump() if session.start_date else "-"
    if session.is_current_role:
        end_date = "Present"
    else:
        end_date = session.end_date.model_dump() if session.end_date else "-"

    return f"{start_date} to {end_date}"


def _strip_json_fence(content: str) -> str:
    """Remove common Markdown JSON fences from model output."""

    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()

    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()

    return stripped
