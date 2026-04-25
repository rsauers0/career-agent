from __future__ import annotations

from career_agent.config import get_settings
from career_agent.interfaces.tui import build_tui, format_component_name


def test_format_component_name_converts_internal_key_to_label() -> None:
    assert format_component_name("user_preferences") == "User Preferences"


def test_build_tui_uses_configured_data_dir(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    app = build_tui()

    assert app.settings.data_dir == tmp_path

    get_settings.cache_clear()
