from pathlib import Path

from career_agent.config import Settings, get_settings


def test_settings_default_data_dir(monkeypatch) -> None:
    monkeypatch.delenv("CAREER_AGENT_DATA_DIR", raising=False)

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path.home() / ".career-agent"
    assert settings.llm_base_url is None
    assert settings.llm_api_key is None
    assert settings.llm_model is None
    assert settings.llm_extraction_base_url is None
    assert settings.llm_extraction_api_key is None
    assert settings.llm_extraction_model is None
    assert settings.llm_eval_base_url is None
    assert settings.llm_eval_api_key is None
    assert settings.llm_eval_model is None


def test_settings_reads_data_dir_from_environment(monkeypatch, tmp_path: Path) -> None:
    expected = tmp_path / "career-agent-data"
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(expected))

    settings = Settings(_env_file=None)

    assert settings.data_dir == expected


def test_settings_expands_user_home_in_data_dir(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", "~/career-agent-data")

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path.home() / "career-agent-data"


def test_settings_reads_llm_configuration_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "test-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "local-model")

    settings = Settings(_env_file=None)

    assert settings.llm_base_url == "http://localhost:1234/v1"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "test-key"
    assert settings.llm_model == "local-model"
    assert settings.effective_llm_extraction_base_url == "http://localhost:1234/v1"
    assert settings.effective_llm_extraction_api_key is not None
    assert settings.effective_llm_extraction_api_key.get_secret_value() == "test-key"
    assert settings.effective_llm_extraction_model == "local-model"
    assert settings.effective_llm_eval_base_url == "http://localhost:1234/v1"
    assert settings.effective_llm_eval_api_key is not None
    assert settings.effective_llm_eval_api_key.get_secret_value() == "test-key"
    assert settings.effective_llm_eval_model == "local-model"


def test_settings_reads_role_specific_llm_configuration_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "default-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "qwen36")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "http://localhost:1235/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_API_KEY", "extraction-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", "gemma4-doc")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_BASE_URL", "http://localhost:1236/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_API_KEY", "eval-key")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_MODEL", "mistral-small-4-review")

    settings = Settings(_env_file=None)

    assert settings.effective_llm_extraction_base_url == "http://localhost:1235/v1"
    assert settings.effective_llm_extraction_api_key is not None
    assert settings.effective_llm_extraction_api_key.get_secret_value() == "extraction-key"
    assert settings.effective_llm_extraction_model == "gemma4-doc"
    assert settings.effective_llm_eval_base_url == "http://localhost:1236/v1"
    assert settings.effective_llm_eval_api_key is not None
    assert settings.effective_llm_eval_api_key.get_secret_value() == "eval-key"
    assert settings.effective_llm_eval_model == "mistral-small-4-review"


def test_settings_treats_blank_llm_configuration_as_unset(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", " ")
    monkeypatch.setenv("CAREER_AGENT_LLM_API_KEY", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", " ")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", " ")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_API_KEY", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", " ")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_BASE_URL", " ")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_API_KEY", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EVAL_MODEL", " ")

    settings = Settings(_env_file=None)

    assert settings.llm_base_url is None
    assert settings.llm_api_key is None
    assert settings.llm_model is None
    assert settings.llm_extraction_base_url is None
    assert settings.llm_extraction_api_key is None
    assert settings.llm_extraction_model is None
    assert settings.llm_eval_base_url is None
    assert settings.llm_eval_api_key is None
    assert settings.llm_eval_model is None


def test_get_settings_returns_cached_instance(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path / "first"))

    first = get_settings()

    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path / "second"))
    second = get_settings()

    assert first is second
    assert second.data_dir == tmp_path / "first"

    get_settings.cache_clear()
