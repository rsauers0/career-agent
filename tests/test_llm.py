from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from career_agent.config import Settings
from career_agent.domain.models import (
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
)
from career_agent.infrastructure.llm import (
    DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION,
    DRAFT_EXPERIENCE_ENTRY_SYSTEM_PROMPT,
    FOLLOW_UP_QUESTIONS_PROMPT_VERSION,
    FOLLOW_UP_QUESTIONS_SYSTEM_PROMPT,
    OpenAICompatibleExperienceIntakeAssistant,
)


def build_captured_session() -> ExperienceIntakeSession:
    return ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.SOURCE_CAPTURED,
        source_text="- Built reporting pipeline",
    )


def build_answered_session() -> ExperienceIntakeSession:
    return ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.ANSWERS_CAPTURED,
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        source_text="- Built reporting pipeline",
        follow_up_questions=[
            {
                "id": "question-1",
                "question": "What measurable impact did the pipeline have?",
            }
        ],
        user_answers=[
            {
                "question_id": "question-1",
                "answer": "Reduced manual reporting time by 10 hours per week.",
            }
        ],
    )


def build_chat_completion_response(content: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ]
    }


def test_prompt_templates_load_from_package_resources() -> None:
    assert "Return only valid JSON" in FOLLOW_UP_QUESTIONS_SYSTEM_PROMPT
    assert "Return only valid JSON" in DRAFT_EXPERIENCE_ENTRY_SYSTEM_PROMPT
    assert FOLLOW_UP_QUESTIONS_PROMPT_VERSION == "experience_follow_up_questions.v1"
    assert DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION == "experience_draft_entry.v1"


def test_generate_follow_up_questions_calls_openai_compatible_endpoint() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json=build_chat_completion_response(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question": "What measurable impact did the pipeline have?",
                                "rationale": "Impact turns the duty into an accomplishment.",
                            }
                        ]
                    }
                )
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        api_key="test-key",
        client=client,
    )

    questions = assistant.generate_follow_up_questions(build_captured_session())

    assert len(questions) == 1
    assert questions[0].question == "What measurable impact did the pipeline have?"
    assert questions[0].rationale == "Impact turns the duty into an accomplishment."

    request = captured_requests[0]
    payload = json.loads(request.content)
    assert str(request.url) == "http://localhost:1234/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "gemma4-doc"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0.2
    assert "Do not invent facts." in payload["messages"][0]["content"]
    assert FOLLOW_UP_QUESTIONS_PROMPT_VERSION in payload["messages"][1]["content"]
    assert "- Built reporting pipeline" in payload["messages"][1]["content"]


def test_generate_follow_up_questions_accepts_json_fenced_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=build_chat_completion_response(
                """```json
                {
                  "questions": [
                    {
                      "question": "Who used the reporting pipeline?",
                      "rationale": "Audience helps clarify scope and business value."
                    }
                  ]
                }
                ```"""
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=client,
    )

    questions = assistant.generate_follow_up_questions(build_captured_session())

    assert questions[0].question == "Who used the reporting pipeline?"


def test_generate_follow_up_questions_rejects_missing_source_text() -> None:
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
    )
    session = ExperienceIntakeSession(id="session-123")

    with pytest.raises(ValueError, match="source text is required"):
        assistant.generate_follow_up_questions(session)


def test_generate_follow_up_questions_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=build_chat_completion_response(json.dumps({"not_questions": []})),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=client,
    )

    with pytest.raises(ValueError, match="follow-up questions schema"):
        assistant.generate_follow_up_questions(build_captured_session())


def test_generate_follow_up_questions_rejects_missing_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=client,
    )

    with pytest.raises(ValueError, match="choices\\[0\\].message.content"):
        assistant.generate_follow_up_questions(build_captured_session())


def test_draft_experience_entry_calls_openai_compatible_endpoint() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json=build_chat_completion_response(
                json.dumps(
                    {
                        "experience_entry": {
                            "employer_name": "Acme Analytics",
                            "job_title": "Senior Data Engineer",
                            "role_summary": "Built reporting automation for finance.",
                            "responsibilities": [
                                "Owned reporting pipeline development and maintenance."
                            ],
                            "accomplishments": [
                                "Reduced manual reporting time by 10 hours per week."
                            ],
                            "metrics": ["10 hours saved per week"],
                            "systems_and_tools": ["Python"],
                            "skills_demonstrated": ["automation"],
                            "domains": ["finance reporting"],
                            "keywords": ["reporting", "automation"],
                        }
                    }
                )
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        api_key="test-key",
        client=client,
    )

    draft = assistant.draft_experience_entry(build_answered_session())

    assert draft.employer_name == "Acme Analytics"
    assert draft.job_title == "Senior Data Engineer"
    assert draft.accomplishments == ["Reduced manual reporting time by 10 hours per week."]
    assert draft.metrics == ["10 hours saved per week"]

    request = captured_requests[0]
    payload = json.loads(request.content)
    assert str(request.url) == "http://localhost:1234/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "gemma4-doc"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0.2
    assert "Do not invent facts." in payload["messages"][0]["content"]
    assert DRAFT_EXPERIENCE_ENTRY_PROMPT_VERSION in payload["messages"][1]["content"]
    assert "Acme Analytics" in payload["messages"][1]["content"]
    assert (
        "Reduced manual reporting time by 10 hours per week." in payload["messages"][1]["content"]
    )


def test_draft_experience_entry_rejects_missing_required_session_data() -> None:
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
    )

    with pytest.raises(ValueError, match="source text is required"):
        assistant.draft_experience_entry(ExperienceIntakeSession(id="session-123"))

    with pytest.raises(ValueError, match="employer name is required"):
        assistant.draft_experience_entry(
            ExperienceIntakeSession(
                id="session-123",
                source_text="- Built reporting pipeline",
            )
        )


def test_draft_experience_entry_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=build_chat_completion_response(json.dumps({"not_experience_entry": {}})),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAICompatibleExperienceIntakeAssistant(
        base_url="http://localhost:1234/v1",
        model="gemma4-doc",
        client=client,
    )

    with pytest.raises(ValueError, match="draft experience entry schema"):
        assistant.draft_experience_entry(build_answered_session())


def test_from_settings_uses_effective_extraction_settings() -> None:
    settings = Settings(
        data_dir="~/.career-agent",
        llm_base_url="http://localhost:1234/v1",
        llm_api_key="default-key",
        llm_model="qwen36",
        llm_extraction_base_url="http://localhost:1235/v1",
        llm_extraction_api_key="extraction-key",
        llm_extraction_model="gemma4-doc",
        _env_file=None,
    )

    assistant = OpenAICompatibleExperienceIntakeAssistant.from_settings(settings)

    assert assistant.base_url == "http://localhost:1235/v1"
    assert assistant.model == "gemma4-doc"
    assert assistant._headers()["Authorization"] == "Bearer extraction-key"


def test_from_settings_requires_base_url_and_model() -> None:
    settings = Settings(data_dir="~/.career-agent", _env_file=None)

    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        OpenAICompatibleExperienceIntakeAssistant.from_settings(settings)

    settings = Settings(
        data_dir="~/.career-agent",
        llm_base_url="http://localhost:1234/v1",
        _env_file=None,
    )

    with pytest.raises(ValueError, match="LLM_MODEL"):
        OpenAICompatibleExperienceIntakeAssistant.from_settings(settings)
