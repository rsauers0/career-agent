from __future__ import annotations

from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.domain.models import (
    CareerProfile,
    ExperienceEntry,
    UserPreferences,
    WorkArrangement,
)
from career_agent.infrastructure.repositories import FileProfileRepository

runner = CliRunner()


def build_user_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Chicago, IL"],
        time_zone="America/Chicago",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        desired_salary_min=150000,
        work_authorization=True,
        requires_work_sponsorship=False,
    )


def build_career_profile() -> CareerProfile:
    return CareerProfile(
        core_narrative_notes=["Position as a data platform leader."],
        experience_entries=[
            ExperienceEntry(
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                responsibilities=["Owned orchestration and reliability for ETL pipelines."],
            )
        ],
        skills=["data engineering", "technical leadership"],
        tools_and_technologies=["Python", "Airflow"],
        domains=["retail analytics"],
    )


def test_profile_show_reports_empty_state(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["profile", "show"])

    assert result.exit_code == 0
    assert "No profile data found." in result.output
    assert str(tmp_path) in result.output

    get_settings.cache_clear()


def test_profile_show_displays_stored_preferences_and_profile(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileProfileRepository(tmp_path)
    repository.save_user_preferences(build_user_preferences())
    repository.save_career_profile(build_career_profile())

    result = runner.invoke(app, ["profile", "show"])

    assert result.exit_code == 0
    assert "User Preferences" in result.output
    assert "Randy Example" in result.output
    assert "Career Profile" in result.output
    assert "Experience Entries" in result.output
    assert "1" in result.output
    assert "data engineering" in result.output

    get_settings.cache_clear()


def test_profile_init_creates_storage_scaffolding(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["profile", "init"])

    repository = FileProfileRepository(tmp_path)

    assert result.exit_code == 0
    assert "Initialized profile storage under" in result.output
    assert repository.profile_dir.exists()
    assert repository.profile_snapshot_dir.exists()
    assert repository.load_user_preferences() is None
    assert repository.load_career_profile() is None

    get_settings.cache_clear()


def test_profile_init_reports_existing_storage(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileProfileRepository(tmp_path)
    repository.initialize_profile_storage()

    result = runner.invoke(app, ["profile", "init"])

    assert result.exit_code == 0
    assert "Profile storage is already initialized." in result.output

    get_settings.cache_clear()


def test_preferences_show_reports_empty_state(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["preferences", "show"])

    assert result.exit_code == 0
    assert "No user preferences found." in result.output
    assert str(tmp_path) in result.output

    get_settings.cache_clear()


def test_preferences_status_reports_not_started(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["preferences", "status"])

    assert result.exit_code == 0
    assert "Component Status" in result.output
    assert "not_started" in result.output
    assert "preferred_work_arrangements" in result.output

    get_settings.cache_clear()


def test_preferences_status_reports_complete(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileProfileRepository(tmp_path)
    repository.save_user_preferences(build_user_preferences())

    result = runner.invoke(app, ["preferences", "status"])

    assert result.exit_code == 0
    assert "Component Status" in result.output
    assert "complete" in result.output

    get_settings.cache_clear()


def test_preferences_wizard_creates_preferences(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        ["preferences", "wizard"],
        input=(
            "Randy Example\n"
            "Aurora, IL 60504\n"
            "America/Chicago\n"
            "Senior Data Engineer, Analytics Engineer\n"
            "Chicago, IL\n"
            "remote, hybrid\n"
            "150000\n"
            "USD\n"
            "35\n"
            "miles\n"
            "50\n"
            "y\n"
            "n\n"
        ),
    )

    repository = FileProfileRepository(tmp_path)
    preferences = repository.load_user_preferences()

    assert result.exit_code == 0
    assert "Saved user preferences." in result.output
    assert preferences is not None
    assert preferences.full_name == "Randy Example"
    assert preferences.target_job_titles == [
        "Senior Data Engineer",
        "Analytics Engineer",
    ]
    assert [arrangement.value for arrangement in preferences.preferred_work_arrangements] == [
        "remote",
        "hybrid",
    ]
    assert preferences.desired_salary_min == 150000
    assert preferences.max_commute_time == 50

    get_settings.cache_clear()


def test_preferences_wizard_updates_existing_preferences(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileProfileRepository(tmp_path)
    repository.save_user_preferences(build_user_preferences())

    result = runner.invoke(
        app,
        ["preferences", "wizard"],
        input=("\n\n\nPrincipal Data Engineer\n\n\n\n\n\n\n\ny\nn\n"),
    )

    preferences = repository.load_user_preferences()

    assert result.exit_code == 0
    assert "Saved user preferences." in result.output
    assert preferences is not None
    assert preferences.full_name == "Randy Example"
    assert preferences.target_job_titles == ["Principal Data Engineer"]
    assert preferences.base_location == "Aurora, IL 60504"
    assert preferences.time_zone == "America/Chicago"

    get_settings.cache_clear()


def test_preferences_wizard_reprompts_invalid_time_zone(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        ["preferences", "wizard"],
        input=(
            "Randy Example\n"
            "Aurora, IL 60504\n"
            "Not/A_Real_Zone\n"
            "America/Chicago\n"
            "Senior Data Engineer\n"
            "Chicago, IL\n"
            "remote\n"
            "150000\n"
            "USD\n"
            "35\n"
            "miles\n"
            "50\n"
            "y\n"
            "n\n"
        ),
    )

    repository = FileProfileRepository(tmp_path)
    preferences = repository.load_user_preferences()

    assert result.exit_code == 0
    assert "valid IANA time zone identifier" in result.output
    assert preferences is not None
    assert preferences.time_zone == "America/Chicago"

    get_settings.cache_clear()
