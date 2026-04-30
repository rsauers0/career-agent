import pytest
from pydantic import ValidationError

from career_agent.llm.client import FakeLLMClient
from career_agent.llm.models import LLMRequest, LLMResponse


def test_llm_request_normalizes_prompt_fields() -> None:
    request = LLMRequest(
        system_prompt="  You are a careful assistant.  ",
        user_prompt="  Generate questions.  ",
        model="  qwen36  ",
        temperature=0.4,
    )

    assert request.system_prompt == "You are a careful assistant."
    assert request.user_prompt == "Generate questions."
    assert request.model == "qwen36"
    assert request.temperature == 0.4


def test_llm_request_treats_blank_model_as_unset() -> None:
    request = LLMRequest(
        system_prompt="You are a careful assistant.",
        user_prompt="Generate questions.",
        model="   ",
    )

    assert request.model is None


def test_llm_request_requires_prompts() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(system_prompt="", user_prompt="Generate questions.")

    with pytest.raises(ValidationError):
        LLMRequest(system_prompt="You are a careful assistant.", user_prompt="   ")


def test_llm_request_validates_temperature_range() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(
            system_prompt="You are a careful assistant.",
            user_prompt="Generate questions.",
            temperature=-0.1,
        )

    with pytest.raises(ValidationError):
        LLMRequest(
            system_prompt="You are a careful assistant.",
            user_prompt="Generate questions.",
            temperature=2.1,
        )


def test_llm_response_normalizes_fields() -> None:
    response = LLMResponse(content="  Response content.  ", model="  qwen36  ")

    assert response.content == "Response content."
    assert response.model == "qwen36"


def test_llm_response_requires_content() -> None:
    with pytest.raises(ValidationError):
        LLMResponse(content="   ")


def test_fake_llm_client_records_request_and_returns_configured_response() -> None:
    client = FakeLLMClient(response_content="Generated content.", response_model="fake-model")
    request = LLMRequest(
        system_prompt="You are a careful assistant.",
        user_prompt="Generate questions.",
        model="requested-model",
    )

    response = client.complete(request)

    assert response.content == "Generated content."
    assert response.model == "fake-model"
    assert client.requests == [request]


def test_fake_llm_client_uses_request_model_when_response_model_unset() -> None:
    client = FakeLLMClient(response_content="Generated content.")
    request = LLMRequest(
        system_prompt="You are a careful assistant.",
        user_prompt="Generate questions.",
        model="requested-model",
    )

    response = client.complete(request)

    assert response.model == "requested-model"
