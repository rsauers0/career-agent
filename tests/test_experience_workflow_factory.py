import pytest

from career_agent.config import Settings
from career_agent.errors import LLMConfigurationError
from career_agent.experience_workflow.factory import (
    build_source_finding_generator,
    build_source_question_generator,
)
from career_agent.experience_workflow.finding_generator import (
    DeterministicSourceFindingGenerator,
    LLMSourceFindingGenerator,
)
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    LLMSourceQuestionGenerator,
)
from career_agent.llm.openai_compatible_client import OpenAICompatibleLLMClient


def test_build_source_question_generator_defaults_to_deterministic(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")

    settings = Settings(_env_file=None)

    generator = build_source_question_generator(settings)

    assert isinstance(generator, DeterministicSourceQuestionGenerator)


def test_build_source_question_generator_uses_default_llm_config(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "qwen36")

    settings = Settings(_env_file=None)
    generator = build_source_question_generator(settings)

    assert isinstance(generator, LLMSourceQuestionGenerator)
    assert generator.model == "qwen36"
    assert isinstance(generator.llm_client, OpenAICompatibleLLMClient)
    assert generator.llm_client.base_url == "http://localhost:1234/v1"
    assert generator.llm_client.default_model == "qwen36"


def test_build_source_question_generator_uses_extraction_override(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "default-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "qwen36")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "http://localhost:1235/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_API_KEY", "extraction-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", "gemma4-doc")

    settings = Settings(_env_file=None)
    generator = build_source_question_generator(settings)

    assert isinstance(generator, LLMSourceQuestionGenerator)
    assert generator.model == "gemma4-doc"
    assert isinstance(generator.llm_client, OpenAICompatibleLLMClient)
    assert generator.llm_client.base_url == "http://localhost:1235/v1"
    assert generator.llm_client.api_key == "extraction-key"
    assert generator.llm_client.default_model == "gemma4-doc"


def test_build_source_question_generator_ignores_blank_extraction_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "default-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "qwen36")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_API_KEY", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", "")

    settings = Settings(_env_file=None)
    generator = build_source_question_generator(settings)

    assert isinstance(generator, LLMSourceQuestionGenerator)
    assert generator.model == "qwen36"
    assert isinstance(generator.llm_client, OpenAICompatibleLLMClient)
    assert generator.llm_client.base_url == "http://localhost:1234/v1"
    assert generator.llm_client.api_key == "default-key"
    assert generator.llm_client.default_model == "qwen36"


def test_build_source_question_generator_requires_model_when_llm_configured(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.delenv("CAREER_AGENT_LLM_MODEL", raising=False)
    monkeypatch.delenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", raising=False)

    settings = Settings(_env_file=None)

    with pytest.raises(LLMConfigurationError, match="may override"):
        build_source_question_generator(settings)


def test_build_source_finding_generator_defaults_to_deterministic(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")

    settings = Settings(_env_file=None)

    generator = build_source_finding_generator(settings)

    assert isinstance(generator, DeterministicSourceFindingGenerator)


def test_build_source_finding_generator_uses_extraction_override(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "default-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "qwen36")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "http://localhost:1235/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_API_KEY", "extraction-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", "gemma4-doc")

    settings = Settings(_env_file=None)
    generator = build_source_finding_generator(settings)

    assert isinstance(generator, LLMSourceFindingGenerator)
    assert generator.model == "gemma4-doc"
    assert isinstance(generator.llm_client, OpenAICompatibleLLMClient)
    assert generator.llm_client.base_url == "http://localhost:1235/v1"
    assert generator.llm_client.api_key == "extraction-key"
    assert generator.llm_client.default_model == "gemma4-doc"


def test_build_source_finding_generator_requires_model_when_llm_configured(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.delenv("CAREER_AGENT_LLM_MODEL", raising=False)
    monkeypatch.delenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", raising=False)

    settings = Settings(_env_file=None)

    with pytest.raises(LLMConfigurationError, match="may override"):
        build_source_finding_generator(settings)
