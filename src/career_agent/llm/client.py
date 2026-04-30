from __future__ import annotations

from typing import Protocol

from career_agent.llm.models import LLMRequest, LLMResponse


class LLMClient(Protocol):
    """Synchronous boundary for provider-neutral LLM completion."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return one completion response for a request."""


class FakeLLMClient:
    """Deterministic LLM client for tests and dev workflow validation."""

    def __init__(self, response_content: str, response_model: str | None = None) -> None:
        self.response_content = response_content
        self.response_model = response_model
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Record the request and return the configured response."""

        self.requests.append(request)
        return LLMResponse(
            content=self.response_content,
            model=self.response_model or request.model,
        )
