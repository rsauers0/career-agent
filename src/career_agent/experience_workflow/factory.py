from __future__ import annotations

from career_agent.config import Settings
from career_agent.errors import LLMConfigurationError
from career_agent.experience_workflow.finding_generator import (
    DeterministicSourceFindingGenerator,
    LLMSourceFindingGenerator,
    SourceFindingGenerator,
)
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    LLMSourceQuestionGenerator,
    SourceQuestionGenerator,
)
from career_agent.llm.openai_compatible_client import OpenAICompatibleLLMClient


def build_source_question_generator(settings: Settings) -> SourceQuestionGenerator:
    """Build the configured source question generator."""

    base_url = settings.effective_llm_extraction_base_url
    if base_url is None:
        return DeterministicSourceQuestionGenerator()

    model = settings.effective_llm_extraction_model
    if model is None:
        msg = (
            "CAREER_AGENT_LLM_MODEL is required when an LLM base URL is configured. "
            "CAREER_AGENT_LLM_EXTRACTION_MODEL may override it for extraction workflows."
        )
        raise LLMConfigurationError(msg)

    api_key = settings.effective_llm_extraction_api_key
    client = OpenAICompatibleLLMClient(
        base_url=base_url,
        api_key=api_key.get_secret_value() if api_key is not None else None,
        default_model=model,
    )
    return LLMSourceQuestionGenerator(llm_client=client, model=model)


def build_source_finding_generator(settings: Settings) -> SourceFindingGenerator:
    """Build the configured source finding generator."""

    base_url = settings.effective_llm_extraction_base_url
    if base_url is None:
        return DeterministicSourceFindingGenerator()

    model = settings.effective_llm_extraction_model
    if model is None:
        msg = (
            "CAREER_AGENT_LLM_MODEL is required when an LLM base URL is configured. "
            "CAREER_AGENT_LLM_EXTRACTION_MODEL may override it for extraction workflows."
        )
        raise LLMConfigurationError(msg)

    api_key = settings.effective_llm_extraction_api_key
    client = OpenAICompatibleLLMClient(
        base_url=base_url,
        api_key=api_key.get_secret_value() if api_key is not None else None,
        default_model=model,
    )
    return LLMSourceFindingGenerator(llm_client=client, model=model)
