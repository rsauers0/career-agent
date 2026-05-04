from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.experience_facts.models import ExperienceFact, ExperienceFactStatus
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus
from career_agent.role_sources.repository import RoleSourceRepository
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceAnalysisStatus,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFinding,
    SourceFindingStatus,
    SourceFindingType,
)
from career_agent.source_analysis.repository import SourceAnalysisRepository
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
            "--role-focus",
            "Led internal reporting and automation improvements.",
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
    assert roles[0].role_focus == "Led internal reporting and automation improvements."
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
            role_focus="Led internal reporting and automation improvements.",
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
            role_focus="Led internal reporting and automation improvements.",
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
    assert "Led internal reporting and automation improvements." in result.output

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


def test_facts_list_reports_missing_facts(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "list"])

    assert result.exit_code == 0
    assert "No experience facts saved yet." in result.output

    get_settings.cache_clear()


def test_facts_add_writes_fact(monkeypatch, tmp_path) -> None:
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

    result = runner.invoke(
        app,
        [
            "facts",
            "add",
            "--role-id",
            "role-1",
            "--text",
            "Automated reporting workflows.",
            "--source-id",
            "source-1",
            "--question-id",
            "question-1",
            "--message-id",
            "message-1",
            "--detail",
            "Reduced monthly reconciliation effort.",
            "--system",
            "Power Platform",
            "--skill",
            "Power Automate",
            "--function",
            "workflow automation",
        ],
    )

    facts = ExperienceFactRepository(tmp_path).list(role_id="role-1")

    assert result.exit_code == 0
    assert "Saved experience fact." in result.output
    assert "Fact ID:" in result.output
    assert len(facts) == 1
    assert facts[0].text == "Automated reporting workflows."
    assert facts[0].source_ids == ["source-1"]
    assert facts[0].question_ids == ["question-1"]
    assert facts[0].message_ids == ["message-1"]
    assert facts[0].details == ["Reduced monthly reconciliation effort."]
    assert facts[0].systems == ["Power Platform"]
    assert facts[0].skills == ["Power Automate"]
    assert facts[0].functions == ["workflow automation"]

    get_settings.cache_clear()


def test_facts_add_reports_missing_role(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "facts",
            "add",
            "--role-id",
            "missing-role",
            "--text",
            "Automated reporting workflows.",
        ],
    )

    assert result.exit_code != 0
    assert "Experience role does not exist: missing-role" in result.output

    get_settings.cache_clear()


def test_facts_add_reports_missing_source(monkeypatch, tmp_path) -> None:
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
            "facts",
            "add",
            "--role-id",
            "role-1",
            "--text",
            "Automated reporting workflows.",
            "--source-id",
            "missing-source",
        ],
    )

    assert result.exit_code != 0
    assert "Role source does not exist: missing-source" in result.output

    get_settings.cache_clear()


def test_facts_add_reports_missing_superseded_fact(monkeypatch, tmp_path) -> None:
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
            "facts",
            "add",
            "--role-id",
            "role-1",
            "--text",
            "Automated reporting workflows.",
            "--supersedes-fact-id",
            "missing-fact",
        ],
    )

    assert result.exit_code != 0
    assert "Experience fact does not exist: missing-fact" in result.output

    get_settings.cache_clear()


def test_facts_list_renders_saved_facts(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceFactRepository(tmp_path).save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            source_ids=["source-1"],
            question_ids=["question-1"],
            message_ids=["message-1"],
            text="Automated reporting workflows.",
            details=["Reduced monthly reconciliation effort."],
            systems=["Power Platform"],
            skills=["Power Automate"],
            functions=["workflow automation"],
            supersedes_fact_id="fact-0",
            superseded_by_fact_id="fact-2",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "list"], env={"COLUMNS": "160"})

    assert result.exit_code == 0
    assert "Experience Facts" in result.output
    assert "fact-1" in result.output
    assert "role-1" in result.output
    assert "Automated reporting workflows." in result.output

    get_settings.cache_clear()


def test_facts_list_filters_by_role_id(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = ExperienceFactRepository(tmp_path)
    repository.save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            text="Automated reporting workflows.",
        )
    )
    repository.save(
        ExperienceFact(
            id="fact-2",
            role_id="role-2",
            text="Built a service trend dashboard.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["facts", "list", "--role-id", "role-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "fact-1" in result.output
    assert "fact-2" not in result.output

    get_settings.cache_clear()


def test_facts_show_renders_saved_fact(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    ExperienceFactRepository(tmp_path).save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            source_ids=["source-1"],
            question_ids=["question-1"],
            message_ids=["message-1"],
            text="Automated reporting workflows.",
            details=["Reduced monthly reconciliation effort."],
            systems=["Power Platform"],
            skills=["Power Automate"],
            functions=["workflow automation"],
            supersedes_fact_id="fact-0",
            superseded_by_fact_id="fact-2",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "show", "fact-1"])

    assert result.exit_code == 0
    assert "Experience Fact" in result.output
    assert "fact-1" in result.output
    assert "role-1" in result.output
    assert "source-1" in result.output
    assert "question-1" in result.output
    assert "message-1" in result.output
    assert "Power Platform" in result.output
    assert "Power Automate" in result.output
    assert "workflow automation" in result.output
    assert "fact-0" in result.output
    assert "fact-2" in result.output
    assert "Reduced monthly reconciliation effort." in result.output
    assert "Automated reporting workflows." in result.output

    get_settings.cache_clear()


def test_facts_show_reports_missing_fact(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "show", "missing-fact"])

    assert result.exit_code != 0
    assert "No experience fact found for id: missing-fact" in result.output

    get_settings.cache_clear()


def test_facts_delete_removes_saved_fact(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = ExperienceFactRepository(tmp_path)
    repository.save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            text="Automated reporting workflows.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "delete", "fact-1"])

    assert result.exit_code == 0
    assert "Deleted experience fact." in result.output
    assert repository.get("fact-1") is None

    get_settings.cache_clear()


def test_facts_activate_marks_draft_fact_active(monkeypatch, tmp_path) -> None:
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
    repository = ExperienceFactRepository(tmp_path)
    repository.save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            text="Automated reporting workflows.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "activate", "fact-1"])

    assert result.exit_code == 0
    assert "Activated experience fact." in result.output
    assert repository.get("fact-1").status == ExperienceFactStatus.ACTIVE
    events = repository.list_change_events(fact_id="fact-1")
    assert events[-1].event_type.value == "activated"
    assert events[-1].actor.value == "user"

    get_settings.cache_clear()


def test_facts_needs_clarification_marks_draft_fact(monkeypatch, tmp_path) -> None:
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
    repository = ExperienceFactRepository(tmp_path)
    repository.save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            text="Automated reporting workflows.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "facts",
            "needs-clarification",
            "fact-1",
            "--actor",
            "llm",
            "--reason",
            "Metric needs evidence.",
            "--source-message-id",
            "message-1",
        ],
    )

    assert result.exit_code == 0
    assert "Marked experience fact as needing clarification." in result.output
    assert "Metric needs evidence." in result.output
    assert repository.get("fact-1").status == ExperienceFactStatus.NEEDS_CLARIFICATION
    events = repository.list_change_events(fact_id="fact-1")
    assert events[-1].event_type.value == "needs_clarification"
    assert events[-1].actor.value == "llm"
    assert events[-1].summary == "Metric needs evidence."
    assert events[-1].source_message_ids == ["message-1"]

    get_settings.cache_clear()


def test_facts_reject_reports_invalid_transition(monkeypatch, tmp_path) -> None:
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
    ExperienceFactRepository(tmp_path).save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            text="Automated reporting workflows.",
            status=ExperienceFactStatus.ACTIVE,
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["facts", "reject", "fact-1"])

    assert result.exit_code != 0
    assert "active -> rejected" in result.output

    get_settings.cache_clear()


def test_facts_revise_active_fact_creates_draft_revision(monkeypatch, tmp_path) -> None:
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
    repository = ExperienceFactRepository(tmp_path)
    repository.save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            source_ids=["source-1"],
            text="Automated reporting workflows.",
            status=ExperienceFactStatus.ACTIVE,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "facts",
            "revise",
            "fact-1",
            "--text",
            "Automated monthly reporting workflows.",
            "--question-id",
            "question-1",
            "--reason",
            "Added monthly reporting specificity.",
            "--source-message-id",
            "message-1",
        ],
    )
    facts = repository.list(role_id="role-1")
    draft_revisions = [
        fact
        for fact in facts
        if fact.supersedes_fact_id == "fact-1" and fact.status == ExperienceFactStatus.DRAFT
    ]

    assert result.exit_code == 0
    assert "Revised experience fact." in result.output
    assert len(draft_revisions) == 1
    assert draft_revisions[0].text == "Automated monthly reporting workflows."
    assert draft_revisions[0].source_ids == ["source-1"]
    assert draft_revisions[0].question_ids == ["question-1"]
    assert repository.get("fact-1").status == ExperienceFactStatus.ACTIVE
    events = repository.list_change_events(fact_id=draft_revisions[0].id)
    assert events[0].event_type.value == "revised"
    assert events[0].summary == "Added monthly reporting specificity."
    assert events[0].source_message_ids == ["message-1"]

    list_result = runner.invoke(
        app,
        ["facts", "events", "--role-id", "role-1"],
        env={"COLUMNS": "200"},
    )

    assert list_result.exit_code == 0
    assert "Fact Change Events" in list_result.output
    assert "revised" in list_result.output

    get_settings.cache_clear()


def test_source_analysis_runs_start_writes_run(monkeypatch, tmp_path) -> None:
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

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "runs",
            "start",
            "--role-id",
            "role-1",
            "--source-id",
            "source-1",
        ],
    )

    runs = SourceAnalysisRepository(tmp_path).list_runs(role_id="role-1")

    assert result.exit_code == 0
    assert "Started source analysis run." in result.output
    assert "Run ID:" in result.output
    assert len(runs) == 1
    assert runs[0].role_id == "role-1"
    assert runs[0].source_ids == ["source-1"]

    get_settings.cache_clear()


def test_source_analysis_runs_start_reports_source_role_mismatch(monkeypatch, tmp_path) -> None:
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
            role_id="role-2",
            source_text="- Led a reporting automation project.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "runs",
            "start",
            "--role-id",
            "role-1",
            "--source-id",
            "source-1",
        ],
    )

    assert result.exit_code != 0
    assert "Role source source-1 does not belong to role: role-1" in result.output

    get_settings.cache_clear()


def test_source_analysis_runs_start_reports_existing_active_run(monkeypatch, tmp_path) -> None:
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
    RoleSourceRepository(tmp_path).save(
        RoleSourceEntry(
            id="source-2",
            role_id="role-1",
            source_text="- Built a service trend dashboard.",
        )
    )
    SourceAnalysisRepository(tmp_path).save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
            status=SourceAnalysisStatus.ACTIVE,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "runs",
            "start",
            "--role-id",
            "role-1",
            "--source-id",
            "source-2",
        ],
    )

    assert result.exit_code != 0
    assert "Active source analysis run already exists for role role-1: run-1" in result.output

    get_settings.cache_clear()


def test_source_analysis_runs_list_renders_saved_runs(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    SourceAnalysisRepository(tmp_path).save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "runs", "list", "--role-id", "role-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Source Analysis Runs" in result.output
    assert "run-1" in result.output
    assert "role-1" in result.output
    assert "source-1" in result.output

    get_settings.cache_clear()


def test_source_analysis_questions_add_writes_question(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "questions",
            "add",
            "--run-id",
            "run-1",
            "--text",
            "What measurable impact did this automation have?",
            "--relevant-source-id",
            "source-1",
        ],
    )

    questions = repository.list_questions("run-1")

    assert result.exit_code == 0
    assert "Saved clarification question." in result.output
    assert "Question ID:" in result.output
    assert len(questions) == 1
    assert questions[0].question_text == "What measurable impact did this automation have?"
    assert questions[0].relevant_source_ids == ["source-1"]

    get_settings.cache_clear()


def test_source_analysis_questions_add_writes_question_from_file(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    question_file = tmp_path / "question.txt"
    question_file.write_text(
        "What measurable impact did this automation have?",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "questions",
            "add",
            "--run-id",
            "run-1",
            "--from-file",
            str(question_file),
        ],
    )

    questions = repository.list_questions("run-1")

    assert result.exit_code == 0
    assert len(questions) == 1
    assert questions[0].question_text == "What measurable impact did this automation have?"

    get_settings.cache_clear()


def test_source_analysis_questions_add_requires_exactly_one_text_input(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    SourceAnalysisRepository(tmp_path).save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    question_file = tmp_path / "question.txt"
    question_file.write_text("What measurable impact?", encoding="utf-8")
    runner = CliRunner()

    missing_input_result = runner.invoke(
        app,
        ["source-analysis", "questions", "add", "--run-id", "run-1"],
    )
    duplicate_input_result = runner.invoke(
        app,
        [
            "source-analysis",
            "questions",
            "add",
            "--run-id",
            "run-1",
            "--text",
            "What measurable impact?",
            "--from-file",
            str(question_file),
        ],
    )

    assert missing_input_result.exit_code != 0
    assert "Provide exactly one of --text or --from-file." in missing_input_result.output
    assert duplicate_input_result.exit_code != 0
    assert "Provide exactly one of --text or --from-file." in duplicate_input_result.output

    get_settings.cache_clear()


def test_source_analysis_questions_add_reports_source_outside_run(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    SourceAnalysisRepository(tmp_path).save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "questions",
            "add",
            "--run-id",
            "run-1",
            "--text",
            "What measurable impact did this automation have?",
            "--relevant-source-id",
            "source-2",
        ],
    )

    assert result.exit_code != 0
    assert "Source source-2 is not part of analysis run: run-1" in result.output

    get_settings.cache_clear()


def test_source_analysis_questions_list_renders_saved_questions(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    question_text = (
        "What measurable impact did this automation have across the full organization, "
        "including time saved, users affected, systems retired, and final unique detail?"
    )
    SourceAnalysisRepository(tmp_path).save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text=question_text,
            relevant_source_ids=["source-1", "source-2"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "questions", "list", "--run-id", "run-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Source Clarification Questions" in result.output
    assert "Question 1" in result.output
    assert "question-1" in result.output
    assert "run-1" in result.output
    assert "source-1" in result.output
    assert "source-2" in result.output
    assert "What measurable impact" in result.output
    assert "final unique detail" in result.output

    get_settings.cache_clear()


def test_source_analysis_questions_resolve_updates_status(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "questions", "resolve", "question-1"],
    )

    questions = repository.list_questions("run-1")

    assert result.exit_code == 0
    assert "Resolved clarification question." in result.output
    assert questions[0].status == SourceClarificationQuestionStatus.RESOLVED

    get_settings.cache_clear()


def test_source_analysis_questions_skip_updates_status(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "questions", "skip", "question-1"],
    )

    questions = repository.list_questions("run-1")

    assert result.exit_code == 0
    assert "Skipped clarification question." in result.output
    assert questions[0].status == SourceClarificationQuestionStatus.SKIPPED

    get_settings.cache_clear()


def test_source_analysis_messages_add_writes_message(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "messages",
            "add",
            "--question-id",
            "question-1",
            "--author",
            "user",
            "--text",
            "It reduced weekly reporting time from 6 hours to 2.",
        ],
    )

    messages = repository.list_messages("question-1")

    assert result.exit_code == 0
    assert "Saved clarification message." in result.output
    assert "Message ID:" in result.output
    assert len(messages) == 1
    assert messages[0].author == ClarificationMessageAuthor.USER
    assert messages[0].message_text == "It reduced weekly reporting time from 6 hours to 2."

    get_settings.cache_clear()


def test_source_analysis_messages_add_writes_message_from_file(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )
    )
    message_file = tmp_path / "message.txt"
    message_file.write_text(
        "It reduced weekly reporting time from 6 hours to 2.",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "messages",
            "add",
            "--question-id",
            "question-1",
            "--author",
            "user",
            "--from-file",
            str(message_file),
        ],
    )

    messages = repository.list_messages("question-1")

    assert result.exit_code == 0
    assert len(messages) == 1
    assert messages[0].message_text == "It reduced weekly reporting time from 6 hours to 2."

    get_settings.cache_clear()


def test_source_analysis_messages_add_requires_exactly_one_text_input(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    SourceAnalysisRepository(tmp_path).save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )
    )
    message_file = tmp_path / "message.txt"
    message_file.write_text("It reduced weekly reporting time.", encoding="utf-8")
    runner = CliRunner()

    missing_input_result = runner.invoke(
        app,
        [
            "source-analysis",
            "messages",
            "add",
            "--question-id",
            "question-1",
            "--author",
            "user",
        ],
    )
    duplicate_input_result = runner.invoke(
        app,
        [
            "source-analysis",
            "messages",
            "add",
            "--question-id",
            "question-1",
            "--author",
            "user",
            "--text",
            "It reduced weekly reporting time.",
            "--from-file",
            str(message_file),
        ],
    )

    assert missing_input_result.exit_code != 0
    assert "Provide exactly one of --text or --from-file." in missing_input_result.output
    assert duplicate_input_result.exit_code != 0
    assert "Provide exactly one of --text or --from-file." in duplicate_input_result.output

    get_settings.cache_clear()


def test_source_analysis_messages_list_renders_saved_messages(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    message_text = (
        "It reduced weekly reporting time from 6 hours to 2, supported three teams, "
        "and preserved this final answer detail."
    )
    SourceAnalysisRepository(tmp_path).save_message(
        SourceClarificationMessage(
            id="message-1",
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text=message_text,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "messages", "list", "--question-id", "question-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Source Clarification Messages" in result.output
    assert "Message 1" in result.output
    assert "message-1" in result.output
    assert "question-1" in result.output
    assert "user" in result.output
    assert "It reduced weekly reporting time" in result.output
    assert "final answer detail" in result.output

    get_settings.cache_clear()


def test_source_analysis_findings_add_writes_new_fact_finding(monkeypatch, tmp_path) -> None:
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
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "findings",
            "add",
            "--run-id",
            "run-1",
            "--source-id",
            "source-1",
            "--finding-type",
            "new_fact",
            "--proposed-fact-text",
            "Led reporting automation for recurring team metrics.",
            "--rationale",
            "The source describes a distinct automation responsibility.",
        ],
    )

    findings = repository.list_findings(analysis_run_id="run-1")

    assert result.exit_code == 0
    assert "Saved source finding." in result.output
    assert "Finding ID:" in result.output
    assert len(findings) == 1
    assert findings[0].finding_type == SourceFindingType.NEW_FACT
    assert findings[0].role_id == "role-1"
    assert findings[0].source_id == "source-1"
    assert findings[0].fact_id is None
    assert findings[0].proposed_fact_text == "Led reporting automation for recurring team metrics."

    get_settings.cache_clear()


def test_source_analysis_findings_add_writes_fact_finding(monkeypatch, tmp_path) -> None:
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
    ExperienceFactRepository(tmp_path).save(
        ExperienceFact(
            id="fact-1",
            role_id="role-1",
            source_ids=["source-1"],
            text="Led a reporting automation project.",
        )
    )
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "findings",
            "add",
            "--run-id",
            "run-1",
            "--source-id",
            "source-1",
            "--finding-type",
            "supports_fact",
            "--fact-id",
            "fact-1",
            "--rationale",
            "The source directly supports the fact.",
        ],
    )

    findings = repository.list_findings(fact_id="fact-1")

    assert result.exit_code == 0
    assert len(findings) == 1
    assert findings[0].finding_type == SourceFindingType.SUPPORTS_FACT
    assert findings[0].fact_id == "fact-1"

    get_settings.cache_clear()


def test_source_analysis_findings_add_reports_source_outside_run(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    RoleSourceRepository(tmp_path).save(
        RoleSourceEntry(
            id="source-2",
            role_id="role-1",
            source_text="- Built a service trend dashboard.",
        )
    )
    SourceAnalysisRepository(tmp_path).save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "source-analysis",
            "findings",
            "add",
            "--run-id",
            "run-1",
            "--source-id",
            "source-2",
            "--finding-type",
            "new_fact",
            "--proposed-fact-text",
            "Built a service trend dashboard.",
        ],
    )

    assert result.exit_code != 0
    assert "Source source-2 is not part of analysis run: run-1" in result.output

    get_settings.cache_clear()


def test_source_analysis_findings_list_renders_saved_findings(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    SourceAnalysisRepository(tmp_path).save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation for recurring team metrics.",
            rationale="The source describes a distinct automation responsibility.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-analysis", "findings", "list", "--run-id", "run-1"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Source Findings" in result.output
    assert "Finding 1" in result.output
    assert "finding-1" in result.output
    assert "new_fact" in result.output
    assert "Led reporting automation" in result.output

    get_settings.cache_clear()


def test_source_analysis_findings_accept_updates_status(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation for recurring team metrics.",
        )
    )
    runner = CliRunner()

    result = runner.invoke(app, ["source-analysis", "findings", "accept", "finding-1"])

    findings = repository.list_findings()

    assert result.exit_code == 0
    assert "Accepted source finding." in result.output
    assert findings[0].status == SourceFindingStatus.ACCEPTED

    get_settings.cache_clear()


def test_experience_workflow_analyze_sources_starts_run_and_questions(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
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
    RoleSourceRepository(tmp_path).save(
        RoleSourceEntry(
            id="source-2",
            role_id="role-1",
            source_text="- Built a service trend dashboard.",
            status=RoleSourceStatus.ANALYZED,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["experience-workflow", "analyze-sources", "--role-id", "role-1"],
    )

    analysis_repository = SourceAnalysisRepository(tmp_path)
    runs = analysis_repository.list_runs(role_id="role-1")
    questions = analysis_repository.list_questions(runs[0].id)

    assert result.exit_code == 0
    assert "Started experience source analysis." in result.output
    assert "Question Generator: deterministic" in result.output
    assert "Run ID:" in result.output
    assert "Question IDs:" in result.output
    assert len(runs) == 1
    assert runs[0].source_ids == ["source-1"]
    assert len(questions) == 2
    assert questions[0].question_text.startswith("DEV PLACEHOLDER:")

    get_settings.cache_clear()


def test_experience_workflow_analyze_sources_reports_no_unanalyzed_sources(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
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
            status=RoleSourceStatus.ANALYZED,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["experience-workflow", "analyze-sources", "--role-id", "role-1"],
    )

    assert result.exit_code != 0
    assert "Question Generator: deterministic" in result.output
    assert "No unanalyzed sources found for role: role-1" in result.output

    get_settings.cache_clear()


def test_experience_workflow_analyze_sources_reports_incomplete_llm_config(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_MODEL", "")
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

    result = runner.invoke(
        app,
        ["experience-workflow", "analyze-sources", "--role-id", "role-1"],
    )

    assert result.exit_code != 0
    assert "CAREER_AGENT_LLM_MODEL" in result.output

    get_settings.cache_clear()


def test_experience_workflow_generate_findings_writes_findings(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
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
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["experience-workflow", "generate-findings", "--run-id", "run-1"],
    )

    findings = repository.list_findings(analysis_run_id="run-1")

    assert result.exit_code == 0
    assert "Finding Generator: deterministic" in result.output
    assert "Generated source findings." in result.output
    assert "Finding IDs:" in result.output
    assert len(findings) == 1
    assert findings[0].finding_type == SourceFindingType.UNCLEAR
    assert findings[0].source_id == "source-1"

    get_settings.cache_clear()


def test_experience_workflow_generate_findings_reports_open_questions(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
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
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What was the impact?",
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["experience-workflow", "generate-findings", "--run-id", "run-1"],
    )

    assert result.exit_code != 0
    assert "Finding Generator: deterministic" in result.output
    assert "Cannot generate findings while clarification questions are open" in result.output
    assert "question-1" in result.output

    get_settings.cache_clear()


def test_experience_workflow_generate_findings_reports_existing_findings(
    monkeypatch,
    tmp_path,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "")
    monkeypatch.setenv("CAREER_AGENT_LLM_EXTRACTION_BASE_URL", "")
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
    repository = SourceAnalysisRepository(tmp_path)
    repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.UNCLEAR,
        )
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["experience-workflow", "generate-findings", "--run-id", "run-1"],
    )

    assert result.exit_code != 0
    assert "Source findings already exist for analysis run: run-1" in result.output

    get_settings.cache_clear()
