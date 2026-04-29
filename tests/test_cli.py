from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.role_sources.repository import RoleSourceRepository
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
            full_name="John Doe",
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
    assert "John Doe" in result.output
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
            "John Doe",
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
    assert preferences.full_name == "John Doe"
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
            "John Doe",
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


def test_roles_list_reports_missing_roles(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["roles", "list"], env={"COLUMNS": "160"})

    assert result.exit_code == 0
    assert "No experience roles saved yet." in result.output

    get_settings.cache_clear()


def test_roles_save_writes_past_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "roles",
            "save",
            "--employer-name",
            "Acme Analytics",
            "--job-title",
            "Senior Systems Analyst",
            "--start-date",
            "05/2021",
            "--end-date",
            "06/2024",
            "--location",
            "Chicago, IL",
            "--employment-type",
            "full-time",
        ],
    )

    roles = ExperienceRoleRepository(tmp_path).list()

    assert result.exit_code == 0
    assert "Saved experience role." in result.output
    assert "Role ID:" in result.output
    assert len(roles) == 1
    assert roles[0].employer_name == "Acme Analytics"
    assert roles[0].job_title == "Senior Systems Analyst"
    assert roles[0].location == "Chicago, IL"
    assert roles[0].is_current_role is False

    get_settings.cache_clear()


def test_roles_save_writes_current_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "roles",
            "save",
            "--employer-name",
            "Current Co",
            "--job-title",
            "Platform Engineer",
            "--start-date",
            "02/2024",
            "--current",
        ],
    )

    roles = ExperienceRoleRepository(tmp_path).list()

    assert result.exit_code == 0
    assert len(roles) == 1
    assert roles[0].is_current_role is True
    assert roles[0].end_date is None

    get_settings.cache_clear()


def test_roles_list_renders_saved_roles(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = ExperienceRoleRepository(tmp_path)
    repository.save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["roles", "list"], env={"COLUMNS": "160"})

    assert result.exit_code == 0
    assert "Experience Roles" in result.output
    assert "role-1" in result.output
    assert "Senior Systems Analyst" in result.output
    assert "Acme Analytics" in result.output
    assert "05/2021 - 06/2024" in result.output

    get_settings.cache_clear()


def test_roles_show_renders_saved_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = ExperienceRoleRepository(tmp_path)
    repository.save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["roles", "show", "role-1"])

    assert result.exit_code == 0
    assert "Experience Role" in result.output
    assert "Acme Analytics" in result.output
    assert "Senior Systems Analyst" in result.output

    get_settings.cache_clear()


def test_roles_show_reports_missing_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["roles", "show", "missing-role"])

    assert result.exit_code != 0
    assert "No experience role found for id: missing-role" in result.output

    get_settings.cache_clear()


def test_roles_delete_removes_saved_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = ExperienceRoleRepository(tmp_path)
    repository.save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["roles", "delete", "role-1"])

    assert result.exit_code == 0
    assert "Deleted experience role." in result.output
    assert repository.get("role-1") is None

    get_settings.cache_clear()


def test_sources_list_reports_missing_sources(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["sources", "list"])

    assert result.exit_code == 0
    assert "No role sources saved yet." in result.output

    get_settings.cache_clear()


def test_sources_add_writes_source_text(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceRoleRepository(tmp_path).save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "sources",
            "add",
            "--role-id",
            "role-1",
            "--source-text",
            "- Led a reporting automation project.",
        ],
    )

    sources = RoleSourceRepository(tmp_path).list(role_id="role-1")

    assert result.exit_code == 0
    assert "Saved role source." in result.output
    assert "Source ID:" in result.output
    assert len(sources) == 1
    assert sources[0].source_text == "- Led a reporting automation project."

    get_settings.cache_clear()


def test_sources_add_writes_source_from_file(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceRoleRepository(tmp_path).save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    source_file = tmp_path / "source-notes.txt"
    source_file.write_text(
        "- Led a reporting automation project.\n- Built a dashboard.",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "sources",
            "add",
            "--role-id",
            "role-1",
            "--from-file",
            str(source_file),
        ],
    )

    sources = RoleSourceRepository(tmp_path).list(role_id="role-1")

    assert result.exit_code == 0
    assert len(sources) == 1
    assert sources[0].source_text == "- Led a reporting automation project.\n- Built a dashboard."

    get_settings.cache_clear()


def test_sources_add_requires_exactly_one_source_input(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceRoleRepository(tmp_path).save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    source_file = tmp_path / "source-notes.txt"
    source_file.write_text("- Built a dashboard.", encoding="utf-8")
    runner = CliRunner()

    missing_input_result = runner.invoke(
        app,
        [
            "sources",
            "add",
            "--role-id",
            "role-1",
        ],
    )
    duplicate_input_result = runner.invoke(
        app,
        [
            "sources",
            "add",
            "--role-id",
            "role-1",
            "--source-text",
            "- Led a reporting automation project.",
            "--from-file",
            str(source_file),
        ],
    )

    assert missing_input_result.exit_code != 0
    assert "Provide exactly one of --source-text or --from-file." in missing_input_result.output
    assert duplicate_input_result.exit_code != 0
    assert "Provide exactly one of --source-text or --from-file." in duplicate_input_result.output

    get_settings.cache_clear()


def test_sources_add_reports_missing_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "sources",
            "add",
            "--role-id",
            "missing-role",
            "--source-text",
            "- Led a reporting automation project.",
        ],
    )

    assert result.exit_code != 0
    assert "Experience role does not exist: missing-role" in result.output

    get_settings.cache_clear()


def test_sources_list_renders_saved_sources(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceRoleRepository(tmp_path).save(
        ExperienceRole(
            id="role-1",
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
        )
    )
    RoleSourceRepository(tmp_path).save(
        RoleSourceEntry(
            id="source-1",
            role_id="role-1",
            source_text="- Led a reporting automation project.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["sources", "list"], env={"COLUMNS": "160"})

    assert result.exit_code == 0
    assert "Role Sources" in result.output
    assert "source-1" in result.output
    assert "role-1" in result.output
    assert "Led a reporting automation project" in result.output

    get_settings.cache_clear()


def test_sources_list_filters_by_role_id(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = RoleSourceRepository(tmp_path)
    repository.save(
        RoleSourceEntry(
            id="source-1",
            role_id="role-1",
            source_text="- Led a reporting automation project.",
        )
    )
    repository.save(
        RoleSourceEntry(
            id="source-2",
            role_id="role-2",
            source_text="- Built a service trend dashboard.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["sources", "list", "--role-id", "role-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "source-1" in result.output
    assert "source-2" not in result.output

    get_settings.cache_clear()


def test_sources_show_renders_saved_source(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    RoleSourceRepository(tmp_path).save(
        RoleSourceEntry(
            id="source-1",
            role_id="role-1",
            source_text="- Led a reporting automation project.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["sources", "show", "source-1"])

    assert result.exit_code == 0
    assert "Role Source" in result.output
    assert "source-1" in result.output
    assert "role-1" in result.output
    assert "- Led a reporting automation project." in result.output

    get_settings.cache_clear()


def test_sources_show_reports_missing_source(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["sources", "show", "missing-source"])

    assert result.exit_code != 0
    assert "No role source found for id: missing-source" in result.output

    get_settings.cache_clear()


def test_sources_delete_removes_saved_source(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = RoleSourceRepository(tmp_path)
    repository.save(
        RoleSourceEntry(
            id="source-1",
            role_id="role-1",
            source_text="- Led a reporting automation project.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["sources", "delete", "source-1"])

    assert result.exit_code == 0
    assert "Deleted role source." in result.output
    assert repository.get("source-1") is None

    get_settings.cache_clear()
