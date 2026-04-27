from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError

from career_agent.config import Settings
from career_agent.domain.models import ExperienceEntry, ExperienceIntakeSession, IntakeQuestion

FOLLOW_UP_QUESTIONS_PROMPT_VERSION = "experience_follow_up_questions.v1"
DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION = "experience_draft_entry.v1"

FOLLOW_UP_QUESTIONS_SYSTEM_PROMPT = """
You are assisting with a career experience intake workflow.

The user provided raw notes or resume bullets for one specific role. Your job is
to generate focused follow-up questions that will help transform those notes
into a strong, accomplishment-focused experience entry.

Analyze the source text for:
- duty-style statements that need impact or outcome details
- missing metrics, scale, frequency, volume, cost, time, risk, quality, or reliability details
- unclear ownership, collaboration, leadership, or scope
- tools, systems, platforms, and technologies that may need clarification
- before/after improvements or business outcomes that are implied but not proven

Rules:
- Do not draft resume bullets.
- Do not invent facts.
- Do not assume metrics that were not provided.
- Do not ask questions already answered by the source text.
- Ask one concept per question.
- Prefer questions that help convert duties into accomplishments.
- Return 3 to 7 follow-up questions.

Return only valid JSON with this exact shape:
{
  "questions": [
    {
      "question": "The exact question to ask the user.",
      "rationale": "Why this question matters for improving the experience entry."
    }
  ]
}
""".strip()

DRAFT_EXPERIENCE_ENTRY_SYSTEM_PROMPT = """
You are assisting with a career experience intake workflow.

The user has provided raw source text and answers to follow-up questions for one
specific role. Your job is to draft a structured ExperienceEntry object that
can be reviewed by the user before it becomes canonical career profile data.

Focus on:
- turning duty-style statements into accomplishment-focused content
- preserving only facts supported by the source text or user answers
- separating responsibilities, accomplishments, metrics, tools, skills, domains, and scope notes
- using concise, resume-appropriate language

Rules:
- Do not invent facts.
- Do not invent metrics.
- Do not add employer or job title values beyond the role metadata provided.
- If a detail is not supported, omit it or leave the field empty/null.
- Prefer concrete accomplishments over generic duties when the provided facts support them.
- Keep list items concise and useful for later resume tailoring.

Return only valid JSON with this exact shape:
{
  "experience_entry": {
    "employer_name": "Provided employer name",
    "job_title": "Provided job title",
    "location": null,
    "employment_type": null,
    "start_date": null,
    "end_date": null,
    "is_current_role": false,
    "role_summary": "Short role summary, or null",
    "responsibilities": [],
    "accomplishments": [],
    "metrics": [],
    "systems_and_tools": [],
    "skills_demonstrated": [],
    "domains": [],
    "team_context": null,
    "scope_notes": null,
    "keywords": []
  }
}
""".strip()


class FollowUpQuestionsResponse(BaseModel):
    """Structured response expected from the follow-up question prompt."""

    questions: list[IntakeQuestion] = Field(min_length=1, max_length=7)


class DraftExperienceEntryResponse(BaseModel):
    """Structured response expected from the draft experience entry prompt."""

    experience_entry: ExperienceEntry


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
