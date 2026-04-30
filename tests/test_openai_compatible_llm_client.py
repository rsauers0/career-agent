import json

import httpx
import pytest

from career_agent.errors import LLMClientError
from career_agent.llm.models import LLMRequest
from career_agent.llm.openai_compatible_client import OpenAICompatibleLLMClient


def build_request(model: str | None = "qwen36") -> LLMRequest:
    return LLMRequest(
        system_prompt="You are a careful assistant.",
        user_prompt="Generate clarification questions.",
        model=model,
        temperature=0.1,
    )


def test_openai_compatible_client_sends_chat_completion_request() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "qwen36",
                "choices": [{"message": {"content": "Generated content."}}],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1/",
        api_key="test-key",
        http_client=http_client,
    )

    response = client.complete(build_request())

    assert response.content == "Generated content."
    assert response.model == "qwen36"
    assert len(captured_requests) == 1
    assert str(captured_requests[0].url) == "http://localhost:8000/v1/chat/completions"
    assert captured_requests[0].headers["authorization"] == "Bearer test-key"
    payload = json.loads(captured_requests[0].content)
    assert payload == {
        "model": "qwen36",
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": "You are a careful assistant."},
            {"role": "user", "content": "Generate clarification questions."},
        ],
    }


def test_openai_compatible_client_uses_default_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "default-model"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Generated content."}}]},
        )

    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        default_model="default-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.complete(build_request(model=None))

    assert response.content == "Generated content."
    assert response.model == "default-model"


def test_openai_compatible_client_requires_model() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: None)),
    )

    with pytest.raises(LLMClientError, match="model"):
        client.complete(build_request(model=None))


def test_openai_compatible_client_wraps_http_status_error() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
    )

    with pytest.raises(LLMClientError, match="HTTP 500"):
        client.complete(build_request())


def test_openai_compatible_client_wraps_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMClientError, match="LLM request failed"):
        client.complete(build_request())


def test_openai_compatible_client_rejects_invalid_json_response() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not json"))
        ),
    )

    with pytest.raises(LLMClientError, match="valid JSON"):
        client.complete(build_request())


def test_openai_compatible_client_rejects_missing_message_content() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:8000/v1",
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        ),
    )

    with pytest.raises(LLMClientError, match="choices"):
        client.complete(build_request())
