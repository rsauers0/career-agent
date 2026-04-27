from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError

from career_agent.config import Settings
from career_agent.domain.models import ExperienceIntakeSession, IntakeQuestion

FOLLOW_UP_QUESTIONS_PROMPT_VERSION = "experience_follow_up_questions.v1"

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


class FollowUpQuestionsResponse(BaseModel):
    """Structured response expected from the follow-up question prompt."""

    questions: list[IntakeQuestion] = Field(min_length=1, max_length=7)


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
