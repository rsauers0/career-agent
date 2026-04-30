from __future__ import annotations

from typing import Any

import httpx

from career_agent.errors import LLMClientError
from career_agent.llm.models import LLMRequest, LLMResponse


class OpenAICompatibleLLMClient:
    """Synchronous OpenAI-compatible chat completions client."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout: float = 60,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.http_client = http_client or httpx.Client(timeout=timeout)

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Send one chat completion request to an OpenAI-compatible endpoint."""

        model = request.model or self.default_model
        if model is None:
            msg = "LLM model must be provided by the request or client default."
            raise LLMClientError(msg)

        payload = {
            "model": model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        headers = self._build_headers()

        try:
            response = self.http_client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            msg = f"LLM request failed with HTTP {exc.response.status_code}."
            raise LLMClientError(msg) from exc
        except httpx.HTTPError as exc:
            msg = "LLM request failed."
            raise LLMClientError(msg) from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            msg = "LLM response was not valid JSON."
            raise LLMClientError(msg) from exc

        return self._parse_response(response_payload=response_payload, model=model)

    def _build_headers(self) -> dict[str, str]:
        """Build request headers for OpenAI-compatible chat completions."""

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _parse_response(self, response_payload: dict[str, Any], model: str) -> LLMResponse:
        """Parse OpenAI-compatible chat completion response content."""

        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            msg = "LLM response did not include choices[0].message.content."
            raise LLMClientError(msg) from exc

        response_model = response_payload.get("model") or model
        return LLMResponse(content=content, model=response_model)
