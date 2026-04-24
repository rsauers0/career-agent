from __future__ import annotations

from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.domain.models import CareerProfile, ExperienceEntry, UserPreferences
from career_agent.infrastructure.repositories import FileProfileRepository

runner = CliRunner()


def build_user_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Remote", "Chicago, IL"],
        time_zone="America/Chicago",
        desired_salary_min=150000,
        desired_salary_max=190000,
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


def test_profile_init_creates_starter_profile_files(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        ["profile", "init"],
        input="Randy Example\nAurora, IL 60504\ny\nn\n",
    )

    repository = FileProfileRepository(tmp_path)
    preferences = repository.load_user_preferences()
    profile = repository.load_career_profile()

    assert result.exit_code == 0
    assert "Initialized profile data under" in result.output
    assert preferences is not None
    assert preferences.full_name == "Randy Example"
    assert preferences.base_location == "Aurora, IL 60504"
    assert preferences.work_authorization is True
    assert preferences.requires_work_sponsorship is False
    assert profile is not None
    assert profile.experience_entries == []

    get_settings.cache_clear()


def test_profile_init_refuses_to_overwrite_existing_data(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileProfileRepository(tmp_path)
    repository.save_user_preferences(build_user_preferences())

    result = runner.invoke(app, ["profile", "init"])

    assert result.exit_code == 0
    assert "Profile data already exists." in result.output

    get_settings.cache_clear()
