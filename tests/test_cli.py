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


def test_preferences_save_writes_preferences(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "preferences",
            "save",
            "--full-name",
            "Randy Example",
            "--base-location",
            "Aurora, IL 60504",
            "--work-arrangement",
            "remote",
            "--work-arrangement",
            "hybrid",
            "--work-authorization",
            "--no-requires-work-sponsorship",
            "--time-zone",
            "America/Chicago",
            "--target-job-title",
            "Senior Systems Analyst",
            "--preferred-location",
            "Chicago, IL",
            "--desired-salary-min",
            "150000",
            "--max-commute-distance",
            "35",
            "--max-commute-time",
            "45",
        ],
    )

    repository = UserPreferencesRepository(tmp_path)
    preferences = repository.load()

    assert result.exit_code == 0
    assert "Saved user preferences." in result.output
    assert preferences is not None
    assert preferences.full_name == "Randy Example"
    assert preferences.base_location == "Aurora, IL 60504"
    assert preferences.preferred_work_arrangements == [
        WorkArrangement.REMOTE,
        WorkArrangement.HYBRID,
    ]
    assert preferences.time_zone == "America/Chicago"
    assert preferences.target_job_titles == ["Senior Systems Analyst"]
    assert preferences.preferred_locations == ["Chicago, IL"]
    assert preferences.desired_salary_min == 150000
    assert preferences.max_commute_distance == 35
    assert preferences.max_commute_time == 45
    assert preferences.work_authorization is True
    assert preferences.requires_work_sponsorship is False

    get_settings.cache_clear()


def test_preferences_save_reports_validation_error(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "preferences",
            "save",
            "--full-name",
            "Randy Example",
            "--base-location",
            "Aurora, IL 60504",
            "--work-arrangement",
            "remote",
            "--work-authorization",
            "--no-requires-work-sponsorship",
            "--time-zone",
            "Not/A_Zone",
        ],
    )

    assert result.exit_code != 0
    assert "time_zone must be a valid IANA time zone identifier." in result.output

    get_settings.cache_clear()
