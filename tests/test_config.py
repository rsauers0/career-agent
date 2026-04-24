from pathlib import Path

from career_agent.config import Settings, get_settings


def test_settings_default_data_dir(monkeypatch) -> None:
    monkeypatch.delenv("CAREER_AGENT_DATA_DIR", raising=False)

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path.home() / ".career-agent"


def test_settings_reads_data_dir_from_environment(monkeypatch, tmp_path: Path) -> None:
    expected = tmp_path / "career-agent-data"
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(expected))

    settings = Settings(_env_file=None)

    assert settings.data_dir == expected


def test_settings_expands_user_home_in_data_dir(monkeypatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", "~/career-agent-data")

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path.home() / "career-agent-data"


def test_get_settings_returns_cached_instance(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path / "first"))

    first = get_settings()

    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path / "second"))
    second = get_settings()

    assert first is second
    assert second.data_dir == tmp_path / "first"

    get_settings.cache_clear()
