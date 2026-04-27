from __future__ import annotations

from typer.testing import CliRunner

from career_agent.cli import app
from career_agent.config import get_settings
from career_agent.domain.models import (
    CareerProfile,
    ExperienceEntry,
    IntakeQuestion,
    UserPreferences,
    WorkArrangement,
)
from career_agent.infrastructure.repositories import (
    FileExperienceIntakeRepository,
    FileProfileRepository,
)

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


class FakeExperienceIntakeAssistant:
    def generate_follow_up_questions(self, session):
        return [
            IntakeQuestion(
                question="What measurable impact did this work have?",
                rationale="Impact helps convert duties into accomplishments.",
            )
        ]

    def draft_experience_entry(self, session):
        return ExperienceEntry(
            employer_name=session.employer_name or "Wrong Employer",
            job_title=session.job_title or "Wrong Job",
            role_summary="Built reporting automation for finance.",
            accomplishments=["Reduced manual reporting time by 10 hours per week."],
            systems_and_tools=["Python"],
        )


def test_profile_show_reports_empty_state(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["profile", "show"])

    assert result.exit_code == 0
    assert "No profile data found." in result.output
    assert str(tmp_path) in result.output

    get_settings.cache_clear()


def test_experience_create_creates_draft_intake_session(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["experience", "create"])

    repository = FileExperienceIntakeRepository(tmp_path)
    sessions = repository.list_sessions()

    assert result.exit_code == 0
    assert "Created experience intake session" in result.output
    assert len(sessions) == 1
    assert sessions[0].status.value == "draft"

    get_settings.cache_clear()


def test_experience_create_can_store_role_details(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        [
            "experience",
            "create",
            "--employer-name",
            "Acme Analytics",
            "--job-title",
            "Senior Data Engineer",
        ],
    )

    repository = FileExperienceIntakeRepository(tmp_path)
    session = repository.list_sessions()[0]

    assert result.exit_code == 0
    assert session.employer_name == "Acme Analytics"
    assert session.job_title == "Senior Data Engineer"

    get_settings.cache_clear()


def test_experience_create_rejects_partial_role_details(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        ["experience", "create", "--employer-name", "Acme Analytics"],
    )

    repository = FileExperienceIntakeRepository(tmp_path)

    assert result.exit_code == 1
    assert "Both --employer-name and --job-title are required together." in result.output
    assert repository.list_sessions() == []

    get_settings.cache_clear()


def test_experience_details_updates_role_details(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(
        app,
        [
            "experience",
            "details",
            session_id,
            "--employer-name",
            "Acme Analytics",
            "--job-title",
            "Senior Data Engineer",
        ],
    )

    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert "Saved role details" in result.output
    assert updated is not None
    assert updated.employer_name == "Acme Analytics"
    assert updated.job_title == "Senior Data Engineer"

    get_settings.cache_clear()


def test_experience_list_reports_empty_state(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["experience", "list"])

    assert result.exit_code == 0
    assert "No experience intake sessions found." in result.output

    get_settings.cache_clear()


def test_experience_source_captures_source_text(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileExperienceIntakeRepository(tmp_path)
    session = repository.load_session("session-123")
    assert session is None

    create_result = runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )
    updated = repository.load_session(session_id)

    assert create_result.exit_code == 0
    assert result.exit_code == 0
    assert "Saved source text" in result.output
    assert updated is not None
    assert updated.source_text == "- Built reporting pipeline"
    assert updated.status.value == "source_captured"

    get_settings.cache_clear()


def test_experience_source_reads_source_text_from_file(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    source_file = tmp_path / "bullets.md"
    source_file.write_text(
        "- Built reporting pipeline\n- Automated spreadsheet extracts\n",
        encoding="utf-8",
    )
    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(
        app,
        ["experience", "source", session_id, "--from-file", str(source_file)],
    )
    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert updated is not None
    assert updated.source_text == "- Built reporting pipeline\n- Automated spreadsheet extracts"

    get_settings.cache_clear()


def test_experience_source_can_append_source_text(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    source_file = tmp_path / "more-bullets.md"
    source_file.write_text("- Added alerting\n", encoding="utf-8")
    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id
    runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )

    result = runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--from-file",
            str(source_file),
            "--append",
        ],
    )
    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert updated is not None
    assert updated.source_text == "- Built reporting pipeline\n\n- Added alerting"

    get_settings.cache_clear()


def test_experience_source_rejects_text_and_file_together(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    source_file = tmp_path / "bullets.md"
    source_file.write_text("- Built reporting pipeline\n", encoding="utf-8")
    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Inline bullet",
            "--from-file",
            str(source_file),
        ],
    )
    updated = repository.load_session(session_id)

    assert result.exit_code == 1
    assert "Use either --text or --from-file, not both." in result.output
    assert updated is not None
    assert updated.source_text is None

    get_settings.cache_clear()


def test_experience_show_displays_session(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileExperienceIntakeRepository(tmp_path)

    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(app, ["experience", "show", session_id])

    assert result.exit_code == 0
    assert "Experience Intake Session" in result.output
    assert session_id in result.output
    assert "draft" in result.output

    get_settings.cache_clear()


def test_experience_questions_uses_configured_assistant(
    monkeypatch,
    tmp_path,
) -> None:
    import career_agent.cli as cli_module

    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "gemma4-doc")

    def fake_from_settings(settings):
        assert settings.effective_llm_extraction_base_url == "http://localhost:1234/v1"
        assert settings.effective_llm_extraction_model == "gemma4-doc"
        return FakeExperienceIntakeAssistant()

    monkeypatch.setattr(
        cli_module.OpenAICompatibleExperienceIntakeAssistant,
        "from_settings",
        fake_from_settings,
    )

    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id
    runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )

    result = runner.invoke(app, ["experience", "questions", session_id])
    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert "Generated follow-up questions" in result.output
    assert updated is not None
    assert updated.status.value == "questions_generated"
    assert len(updated.follow_up_questions) == 1
    assert updated.follow_up_questions[0].question == "What measurable impact did this work have?"

    get_settings.cache_clear()


def test_experience_answer_captures_question_answers(
    monkeypatch,
    tmp_path,
) -> None:
    import career_agent.cli as cli_module

    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "gemma4-doc")

    monkeypatch.setattr(
        cli_module.OpenAICompatibleExperienceIntakeAssistant,
        "from_settings",
        lambda settings: FakeExperienceIntakeAssistant(),
    )

    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id
    runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )
    runner.invoke(app, ["experience", "questions", session_id])

    result = runner.invoke(
        app,
        ["experience", "answer", session_id],
        input="Reduced manual reporting time by 10 hours per week.\n",
    )
    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert "Saved answers" in result.output
    assert updated is not None
    assert updated.status.value == "answers_captured"
    assert len(updated.user_answers) == 1
    assert updated.user_answers[0].answer == "Reduced manual reporting time by 10 hours per week."

    get_settings.cache_clear()


def test_experience_draft_uses_configured_assistant(
    monkeypatch,
    tmp_path,
) -> None:
    import career_agent.cli as cli_module

    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "gemma4-doc")

    monkeypatch.setattr(
        cli_module.OpenAICompatibleExperienceIntakeAssistant,
        "from_settings",
        lambda settings: FakeExperienceIntakeAssistant(),
    )

    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(
        app,
        [
            "experience",
            "create",
            "--employer-name",
            "Acme Analytics",
            "--job-title",
            "Senior Data Engineer",
        ],
    )
    session_id = repository.list_sessions()[0].id
    runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )
    runner.invoke(app, ["experience", "questions", session_id])
    runner.invoke(
        app,
        ["experience", "answer", session_id],
        input="Reduced manual reporting time by 10 hours per week.\n",
    )

    result = runner.invoke(app, ["experience", "draft", session_id])
    updated = repository.load_session(session_id)

    assert result.exit_code == 0
    assert "Generated draft experience entry" in result.output
    assert updated is not None
    assert updated.status.value == "draft_generated"
    assert updated.draft_experience_entry is not None
    assert updated.draft_experience_entry.employer_name == "Acme Analytics"
    assert updated.draft_experience_entry.job_title == "Senior Data Engineer"
    assert updated.draft_experience_entry.accomplishments == [
        "Reduced manual reporting time by 10 hours per week."
    ]

    get_settings.cache_clear()


def test_experience_accept_saves_draft_to_career_profile(
    monkeypatch,
    tmp_path,
) -> None:
    import career_agent.cli as cli_module

    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAREER_AGENT_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("CAREER_AGENT_LLM_MODEL", "gemma4-doc")

    monkeypatch.setattr(
        cli_module.OpenAICompatibleExperienceIntakeAssistant,
        "from_settings",
        lambda settings: FakeExperienceIntakeAssistant(),
    )

    intake_repository = FileExperienceIntakeRepository(tmp_path)
    profile_repository = FileProfileRepository(tmp_path)
    runner.invoke(
        app,
        [
            "experience",
            "create",
            "--employer-name",
            "Acme Analytics",
            "--job-title",
            "Senior Data Engineer",
        ],
    )
    session_id = intake_repository.list_sessions()[0].id
    runner.invoke(
        app,
        [
            "experience",
            "source",
            session_id,
            "--text",
            "- Built reporting pipeline",
        ],
    )
    runner.invoke(app, ["experience", "questions", session_id])
    runner.invoke(
        app,
        ["experience", "answer", session_id],
        input="Reduced manual reporting time by 10 hours per week.\n",
    )
    runner.invoke(app, ["experience", "draft", session_id])

    result = runner.invoke(app, ["experience", "accept", session_id])
    session = intake_repository.load_session(session_id)
    profile = profile_repository.load_career_profile()

    assert result.exit_code == 0
    assert "Accepted draft experience entry" in result.output
    assert session is not None
    assert session.status.value == "accepted"
    assert session.accepted_experience_entry_id is not None
    assert profile is not None
    assert len(profile.experience_entries) == 1
    assert profile.experience_entries[0].id == session.accepted_experience_entry_id
    assert profile.experience_entries[0].employer_name == "Acme Analytics"
    assert profile.experience_entries[0].job_title == "Senior Data Engineer"

    get_settings.cache_clear()


def test_experience_answer_requires_generated_questions(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))
    repository = FileExperienceIntakeRepository(tmp_path)
    runner.invoke(app, ["experience", "create"])
    session_id = repository.list_sessions()[0].id

    result = runner.invoke(app, ["experience", "answer", session_id])

    assert result.exit_code == 1
    assert "Generate follow-up questions before capturing answers." in result.output

    get_settings.cache_clear()


def test_tui_command_launches_textual_interface(monkeypatch) -> None:
    import career_agent.interfaces.tui as tui_module

    launched = False

    def fake_run_tui() -> None:
        nonlocal launched
        launched = True

    monkeypatch.setattr(tui_module, "run_tui", fake_run_tui)

    result = runner.invoke(app, ["tui"])

    assert result.exit_code == 0
    assert launched is True


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
    assert "Preferred Work Arrangements" in result.output

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
