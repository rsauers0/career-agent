from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.user_preferences.models import UserPreferences, WorkArrangement
from career_agent.user_preferences.repository import UserPreferencesRepository


def test_doctor_command_runs() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Career Agent v2 foundation is ready." in result.output
    assert "Data directory:" in result.output


def test_preferences_show_reports_missing_preferences(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["preferences", "show"])

    assert result.exit_code == 0
    assert "No user preferences saved yet." in result.output

    get_settings.cache_clear()


def test_preferences_show_renders_saved_preferences(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = UserPreferencesRepository(tmp_path)
    repository.save(
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            work_authorization=True,
            requires_work_sponsorship=False,
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["preferences", "show"])

    assert result.exit_code == 0
    assert "User Preferences" in result.output
    assert "Randy Example" in result.output
    assert "Aurora, IL 60504" in result.output
    assert "remote" in result.output

    get_settings.cache_clear()
