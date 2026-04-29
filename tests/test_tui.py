from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from textual.widgets import Button, Checkbox, Input, Static, TextArea

from career_agent.application.dashboard import JobWorkflowState, JobWorkflowStatus
from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
from career_agent.config import Settings, get_settings
from career_agent.domain.models import (
    CandidateBullet,
    CareerProfile,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    ExperienceRoleStatus,
    IntakeAnswer,
    IntakeQuestion,
    UserPreferences,
    WorkArrangement,
)
from career_agent.infrastructure.repositories import (
    FileExperienceIntakeRepository,
    FileProfileRepository,
)
from career_agent.interfaces.tui import CareerAgentTUI, build_tui
from career_agent.interfaces.tui_dashboard import (
    StatusCard,
    format_component_name,
    get_status_detail,
    get_status_label,
)
from career_agent.interfaces.tui_experience import (
    CandidateBulletCard,
    SourceEntryCard,
    build_experience_entry_sections,
    build_question_answer_blocks,
    format_intake_session_title,
    format_intake_status,
    format_role_status,
    is_experience_session_editable,
    sort_experience_sessions,
)
from career_agent.interfaces.tui_preferences import (
    build_user_preferences_form_defaults,
    build_user_preferences_rows,
    format_form_list,
    format_list,
    format_optional_text,
    parse_form_list,
    required_label,
)
from career_agent.interfaces.tui_profile import build_career_profile_summary


class FakeExperienceIntakeAssistant:
    def generate_follow_up_questions(self, session):
        return []

    def generate_candidate_bullets(self, session, source_entries):
        return [
            CandidateBullet(
                id="bullet-1",
                text="Reduced manual reporting work by building reporting automation.",
                source_entry_ids=[source_entry.id for source_entry in source_entries],
            )
        ]

    def draft_experience_entry(self, session):
        return ExperienceEntry(
            employer_name=session.employer_name or "Acme Analytics",
            job_title=session.job_title or "Senior Data Engineer",
        )


def test_format_component_name_converts_internal_key_to_label() -> None:
    assert format_component_name("user_preferences") == "User Preferences"


def test_format_optional_text_handles_blank_values() -> None:
    assert format_optional_text(None) == "-"
    assert format_optional_text("") == "-"
    assert format_optional_text("America/Chicago") == "America/Chicago"


def test_format_list_handles_empty_and_populated_lists() -> None:
    assert format_list([]) == "-"
    assert format_list(["remote", "hybrid"]) == "remote, hybrid"


def test_format_form_list_handles_empty_and_populated_lists() -> None:
    assert format_form_list([], "No titles added.") == "No titles added."
    assert format_form_list(["Engineer", "Analyst"], "No titles added.") == (
        "- Engineer\n- Analyst"
    )


def test_parse_form_list_handles_comma_separated_values() -> None:
    assert parse_form_list("") == []
    assert parse_form_list("Senior Data Engineer, Analytics Engineer") == [
        "Senior Data Engineer",
        "Analytics Engineer",
    ]


def test_required_label_adds_red_required_marker() -> None:
    assert required_label("Full Name") == "Full Name [#f05f5f]*[/]"


def test_format_intake_status_formats_status_values() -> None:
    assert format_intake_status(ExperienceIntakeStatus.DRAFT_GENERATED) == "Draft Generated"


def test_format_role_status_formats_user_facing_status_values() -> None:
    assert format_role_status(ExperienceRoleStatus.REVIEW_REQUIRED) == "Review Required"


def test_format_intake_session_title_uses_best_available_role_context() -> None:
    assert (
        format_intake_session_title(
            ExperienceIntakeSession(
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
            )
        )
        == "Senior Data Engineer at Acme Analytics"
    )
    assert (
        format_intake_session_title(ExperienceIntakeSession(employer_name="Acme Analytics"))
        == "Acme Analytics"
    )
    assert format_intake_session_title(ExperienceIntakeSession()) == "Untitled Experience Intake"


def test_build_experience_entry_sections_formats_draft_values() -> None:
    entry = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["Reduced reporting time by 10 hours per week."],
        systems_and_tools=["Python"],
    )

    sections = dict(build_experience_entry_sections(entry))

    assert sections["Employer"] == "Acme Analytics"
    assert sections["Accomplishments"] == "- Reduced reporting time by 10 hours per week."
    assert sections["Systems and Tools"] == "- Python"
    assert sections["Metrics"] == "-"


def test_sort_experience_sessions_uses_current_and_recent_dates() -> None:
    current = ExperienceIntakeSession(
        id="current",
        employer_name="Current Co",
        job_title="Engineer",
        start_date="01/2024",
        is_current_role=True,
    )
    recent_past = ExperienceIntakeSession(
        id="recent",
        employer_name="Recent Co",
        job_title="Engineer",
        start_date="01/2021",
        end_date="12/2023",
    )
    older_past = ExperienceIntakeSession(
        id="older",
        employer_name="Older Co",
        job_title="Engineer",
        start_date="01/2018",
        end_date="12/2020",
    )

    sorted_sessions = sort_experience_sessions([older_past, current, recent_past])

    assert [session.id for session in sorted_sessions] == ["current", "recent", "older"]


def test_is_experience_session_editable_excludes_locked_entries() -> None:
    unlocked_session = ExperienceIntakeSession(status=ExperienceIntakeStatus.SOURCE_CAPTURED)
    draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    locked_session = ExperienceIntakeSession(
        status=ExperienceIntakeStatus.LOCKED,
        draft_experience_entry=draft,
        accepted_experience_entry_id="entry-123",
        locked_at="2026-01-01T00:00:00Z",
    )

    assert is_experience_session_editable(unlocked_session) is True
    assert is_experience_session_editable(locked_session) is False


def test_build_question_answer_blocks_pairs_answers_under_questions() -> None:
    question = IntakeQuestion(id="question-1", question="What changed?")
    session = ExperienceIntakeSession(
        follow_up_questions=[question],
        user_answers=[
            IntakeAnswer(
                question_id="question-1",
                answer="Reduced reporting time by 10 hours per week.",
            )
        ],
    )

    assert build_question_answer_blocks(session) == [
        ("Question 1: What changed?\n\nAnswer: Reduced reporting time by 10 hours per week.")
    ]


def test_build_career_profile_summary_counts_profile_entries() -> None:
    profile = CareerProfile(
        experience_entries=[
            ExperienceEntry(
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
            )
        ],
        education_entries=["BS Information Systems"],
        certification_entries=["Security+"],
        skills=["automation", "analysis"],
        tools_and_technologies=["Python"],
    )

    summary = build_career_profile_summary(profile)

    assert summary.experience_count == 1
    assert summary.education_count == 1
    assert summary.certification_count == 1
    assert summary.skills_count == 2
    assert summary.tools_count == 1


def test_build_user_preferences_rows_formats_read_only_values() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE, WorkArrangement.HYBRID],
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    rows = dict(build_user_preferences_rows(preferences))

    assert rows["Full Name"] == "Randy Example"
    assert rows["Target Job Titles"] == "-"
    assert rows["Preferred Work Arrangements"] == "remote, hybrid"
    assert rows["Minimum Salary Desired"] == "-"
    assert rows["Work Authorization"] == "Yes"
    assert rows["Requires Work Sponsorship"] == "No"


def test_build_user_preferences_form_defaults_supports_missing_preferences() -> None:
    defaults = build_user_preferences_form_defaults(None)

    assert defaults["full_name"] == ""
    assert defaults["salary_currency"] == "USD"
    assert defaults["commute_distance_unit"] == "miles"


def test_build_user_preferences_form_defaults_prefills_existing_preferences() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer", "Analytics Engineer"],
        preferred_locations=["Chicago, IL"],
        preferred_work_arrangements=[WorkArrangement.REMOTE, WorkArrangement.HYBRID],
        desired_salary_min=150000,
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    defaults = build_user_preferences_form_defaults(preferences)

    assert defaults["full_name"] == "Randy Example"
    assert defaults["target_job_titles"] == "Senior Data Engineer, Analytics Engineer"
    assert defaults["preferred_work_arrangements"] == "remote, hybrid"
    assert defaults["desired_salary_min"] == "150000"


def test_get_status_label_supports_job_workflow_status() -> None:
    status = JobWorkflowStatus(
        component="jobs",
        state=JobWorkflowState.IDLE,
    )

    assert get_status_label(status) == "Idle"


def test_get_status_detail_formats_field_labels() -> None:
    status = ComponentStatus(
        component="user_preferences",
        state=ComponentStatusState.PARTIAL,
        missing_recommended=["target_job_titles", "max_commute_time"],
    )

    detail, detail_class = get_status_detail(status)

    assert detail == "Recommended: Target Job Titles, Max Commute Time"
    assert detail_class == "status-detail recommended-detail"


def test_build_tui_uses_configured_data_dir(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CAREER_AGENT_DATA_DIR", str(tmp_path))

    app = build_tui()

    assert app.settings.data_dir == tmp_path

    get_settings.cache_clear()


def test_preferences_form_add_buttons_update_visible_lists() -> None:
    async def run_test() -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                title_input = app.screen.query_one("#pref-target-job-title-input", Input)
                title_input.value = "Senior Systems Analyst"
                await pilot.click("#add-target-job-title")
                await pilot.pause()

                location_input = app.screen.query_one("#pref-preferred-location-input", Input)
                location_input.value = "Chicago, IL"
                await pilot.click("#add-preferred-location")
                await pilot.pause()

                title_panel = app.screen.query_one("#pref-target-job-titles-panel", Static)
                location_panel = app.screen.query_one("#pref-preferred-locations-panel", Static)
                return str(title_panel.render()), str(location_panel.render())

    title_panel, location_panel = asyncio.run(run_test())

    assert title_panel == "- Senior Systems Analyst"
    assert location_panel == "- Chicago, IL"


def test_preferences_form_enter_adds_visible_list_items() -> None:
    async def run_test() -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                title_input = app.screen.query_one("#pref-target-job-title-input", Input)
                title_input.value = "Platform Engineer"
                title_input.focus()
                await pilot.press("enter")
                await pilot.pause()

                location_input = app.screen.query_one("#pref-preferred-location-input", Input)
                location_input.value = "Madison, WI"
                location_input.focus()
                await pilot.press("enter")
                await pilot.pause()

                title_panel = app.screen.query_one("#pref-target-job-titles-panel", Static)
                location_panel = app.screen.query_one("#pref-preferred-locations-panel", Static)
                return str(title_panel.render()), str(location_panel.render())

    title_panel, location_panel = asyncio.run(run_test())

    assert title_panel == "- Platform Engineer"
    assert location_panel == "- Madison, WI"


def test_preferences_form_save_validation_error_updates_message() -> None:
    async def run_test() -> tuple[str, bool]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                app.screen.query_one("#pref-full-name", Input).value = ""
                app.screen.query_one("#pref-base-location", Input).value = "Aurora, IL 60504"
                app.screen.query_one("#pref-work-arrangement-remote", Checkbox).value = True
                app.screen._save_preferences()
                await pilot.pause()

                message = app.screen.query_one("#preference-message", Static)
                return str(message.render()), message.has_class("message-error")

    message, has_error_class = asyncio.run(run_test())

    assert message == "Could not save preferences:\n- Full Name is required."
    assert has_error_class is True


def test_preferences_form_save_requires_work_arrangement() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                app.screen.query_one("#pref-full-name", Input).value = "Randy Example"
                app.screen.query_one("#pref-base-location", Input).value = "Aurora, IL 60504"
                app.screen.query_one("#pref-work-arrangement-remote", Checkbox).value = False
                app.screen.query_one("#pref-work-arrangement-hybrid", Checkbox).value = False
                app.screen.query_one("#pref-work-arrangement-onsite", Checkbox).value = False
                app.screen._save_preferences()
                await pilot.pause()

                message = app.screen.query_one("#preference-message", Static)
                return str(message.render())

    message = asyncio.run(run_test())

    assert message == (
        "Could not save preferences:\n- At least one Preferred Work Arrangement is required."
    )


def test_preferences_form_save_formats_invalid_number_message() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                app.screen.query_one("#pref-full-name", Input).value = "Randy Example"
                app.screen.query_one("#pref-base-location", Input).value = "Aurora, IL 60504"
                app.screen.query_one("#pref-work-arrangement-remote", Checkbox).value = True
                app.screen.query_one("#pref-desired-salary-min", Input).value = "not a number"
                app.screen._save_preferences()
                await pilot.pause()

                message = app.screen.query_one("#preference-message", Static)
                return str(message.render())

    message = asyncio.run(run_test())

    assert message == (
        "Could not save preferences:\n- Salary and commute preference values must be whole numbers."
    )


def test_preferences_form_ctrl_s_saves_preferences() -> None:
    async def run_test() -> tuple[str, bool]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                app.screen.query_one("#pref-full-name", Input).value = "Randy Example"
                app.screen.query_one("#pref-base-location", Input).value = "Aurora, IL 60504"
                app.screen.query_one("#pref-time-zone").value = "America/Chicago"
                app.screen.query_one("#pref-work-arrangement-remote", Checkbox).value = True
                app.screen.query_one("#pref-desired-salary-min", Input).value = "150000"
                app.screen.target_job_titles = ["Senior Systems Analyst"]
                await pilot.press("ctrl+s")
                await pilot.pause()

                message = app.screen.query_one("#preference-message", Static)
                preferences = profile_service.get_user_preferences()
                return str(message.render()), preferences is not None

    message, preferences_saved = asyncio.run(run_test())

    assert message == "Saved user preferences. Press b or Esc to return to the dashboard."
    assert preferences_saved is True


def test_preferences_dashboard_refreshes_after_save_and_back() -> None:
    async def run_test() -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_preferences()
                await pilot.pause()

                app.screen.query_one("#pref-full-name", Input).value = "Randy Example"
                app.screen.query_one("#pref-base-location", Input).value = "Aurora, IL 60504"
                app.screen.query_one("#pref-time-zone").value = "America/Chicago"
                app.screen.query_one("#pref-work-arrangement-remote", Checkbox).value = True
                app.screen.query_one("#pref-desired-salary-min", Input).value = "150000"
                app.screen.target_job_titles = ["Senior Systems Analyst"]
                app.screen._save_preferences()
                app.screen.action_back()
                await pilot.pause()

                user_preferences_card = app.screen.query(StatusCard).first()
                return [str(widget.render()) for widget in user_preferences_card.query(Static)]

    card_text = asyncio.run(run_test())

    assert "User Preferences" in card_text
    assert "Complete" in card_text
    assert "Press p to review or update preferences." in card_text


def test_dashboard_career_profile_button_opens_profile_screen() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                await pilot.click("#dashboard-action-career-profile")
                await pilot.pause()

                title = app.screen.query_one("#screen-title", Static)
                return str(title.render())

    assert asyncio.run(run_test()) == "Career Profile"


def test_new_role_screen_saves_role_details_then_adds_source_entry() -> None:
    async def run_test() -> tuple[str, int, str | None, str | None, bool]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#add-experience")
                await pilot.pause()

                app.screen.query_one("#experience-employer-name", Input).value = "Acme Analytics"
                app.screen.query_one("#experience-job-title", Input).value = "Senior Data Engineer"
                app.screen.query_one("#experience-location", Input).value = "Chicago, IL"
                app.screen.query_one("#experience-employment-type").value = "full-time"
                app.screen.query_one("#experience-start-month").value = "5"
                app.screen.query_one("#experience-start-year").value = "2021"
                app.screen.query_one("#experience-current-role", Checkbox).value = True
                await pilot.click("#save-experience")
                await pilot.pause()

                app.screen.query_one(
                    "#experience-source-text", TextArea
                ).text = "- Built reporting automation"
                app.screen._add_source_entry()
                await pilot.pause()

                message = app.screen.query_one("#experience-form-message", Static)
                sessions = experience_repository.list_sessions()
                session = sessions[0]
                return (
                    str(message.render()),
                    len(sessions),
                    session.employment_type,
                    session.source_entries[0].content,
                    session.is_current_role,
                )

    message, session_count, employment_type, source_text, is_current_role = asyncio.run(run_test())

    assert "Added source entry." in message
    assert session_count == 1
    assert employment_type == "full-time"
    assert source_text == "- Built reporting automation"
    assert is_current_role is True


def test_edit_role_screen_marks_ready_role_reviewed() -> None:
    async def run_test() -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            experience_service = ExperienceIntakeService(
                experience_repository,
                FakeExperienceIntakeAssistant(),
            )
            session = experience_service.create_session()
            session = experience_service.capture_role_details(
                session.id,
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                is_current_role=True,
            )
            session = experience_service.save_role_focus_statement(
                session.id,
                "I helped finance teams reduce manual reporting.",
            )
            session = experience_service.add_source_entry(
                session.id,
                "- Built reporting automation",
            )
            session = experience_service.analyze_pending_source_entries(session.id)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=experience_service,
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click(f"#edit-experience-session-{session.id}")
                await pilot.pause()
                app.screen._mark_role_reviewed()
                await pilot.pause()

                message = app.screen.query_one("#experience-form-message", Static)
                updated = experience_repository.load_session(session.id)
                assert updated is not None
                return str(message.render()), updated.role_status.value

    message, role_status = asyncio.run(run_test())

    assert message == "Marked role reviewed."
    assert role_status == "reviewed"


def test_edit_role_screen_shows_review_validation_message() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            experience_service = ExperienceIntakeService(experience_repository)
            session = experience_service.create_session()
            session = experience_service.capture_role_details(
                session.id,
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                is_current_role=True,
            )
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=experience_service,
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click(f"#edit-experience-session-{session.id}")
                await pilot.pause()
                app.screen._mark_role_reviewed()
                await pilot.pause()

                message = app.screen.query_one("#experience-form-message", Static)
                return str(message.render())

    message = asyncio.run(run_test())

    assert message == "Role focus statement is required before role review."


def test_add_experience_back_refreshes_experience_list() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#add-experience")
                await pilot.pause()

                app.screen.query_one("#experience-employer-name", Input).value = "Acme Analytics"
                app.screen.query_one("#experience-job-title", Input).value = "Senior Data Engineer"
                app.screen.query_one("#experience-start-month").value = "5"
                app.screen.query_one("#experience-start-year").value = "2021"
                app.screen.query_one("#experience-current-role", Checkbox).value = True
                await pilot.click("#save-experience")
                await pilot.pause()

                app.screen.action_back()
                await pilot.pause()

                card_title = app.screen.query_one(".card-title", Static)
                return str(card_title.render())

    assert asyncio.run(run_test()) == "Senior Data Engineer at Acme Analytics"


def test_edit_role_screen_expands_existing_source_entry() -> None:
    async def run_test() -> tuple[str, str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            experience_service = ExperienceIntakeService(experience_repository)
            session = experience_service.create_session()
            session = experience_service.capture_role_details(
                session.id,
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                is_current_role=True,
            )
            session = experience_service.add_source_entry(
                session.id,
                "- Built reporting automation for finance analysts",
            )
            source_id = session.source_entries[0].id
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=experience_service,
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click(f"#edit-experience-session-{session.id}")
                await pilot.pause()

                preview = app.screen.query_one(".source-entry-heading", Static)
                await pilot.click(f"#toggle-source-entry-{source_id}")
                await pilot.pause()

                expanded = app.screen.query_one(SourceEntryCard)
                panel = expanded.query_one(".read-only-panel", Static)
                return (
                    str(preview.render()),
                    str(panel.render()),
                    str(expanded.query_one(Button).label),
                )

    heading, source_text, button_label = asyncio.run(run_test())

    assert "Not analyzed" in heading
    assert source_text == "- Built reporting automation for finance analysts"
    assert button_label == "Hide"


def test_experience_list_uses_view_and_edit_actions() -> None:
    async def run_test() -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            session = ExperienceIntakeSession(
                id="session-123",
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                status=ExperienceIntakeStatus.SOURCE_CAPTURED,
                source_text="- Built reporting automation",
            )
            experience_repository.save_session(session)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()

                return [str(button.label) for button in app.screen.query(Button)]

    button_labels = asyncio.run(run_test())

    assert "View" in button_labels
    assert "Edit" in button_labels
    assert "Delete" not in button_labels


def test_edit_experience_delete_removes_unlocked_session() -> None:
    async def run_test() -> tuple[str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            session = ExperienceIntakeSession(
                id="session-123",
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                status=ExperienceIntakeStatus.SOURCE_CAPTURED,
                source_text="- Built reporting automation",
            )
            experience_repository.save_session(session)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#edit-experience-session-session-123")
                await pilot.pause()
                await pilot.click("#delete-experience")
                await pilot.pause()

                title = app.screen.query_one("#screen-title", Static)
                await pilot.click("#confirm-delete-experience")
                await pilot.pause()

                active_title = app.screen.query_one("#screen-title", Static)
                return (
                    str(title.render()),
                    str(active_title.render()),
                    len(experience_repository.list_sessions()),
                )

    confirmation_title, active_title, session_count = asyncio.run(run_test())

    assert confirmation_title == "Delete Experience"
    assert active_title == "Experience"
    assert session_count == 0


def test_add_experience_back_prompts_before_discarding_unsaved_changes() -> None:
    async def run_test() -> tuple[str, str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#add-experience")
                await pilot.pause()

                app.screen.query_one("#experience-employer-name", Input).value = "Acme Analytics"
                app.screen.action_back()
                await pilot.pause()

                prompt_title = app.screen.query_one("#screen-title", Static)
                await pilot.click("#discard-unsaved-experience")
                await pilot.pause()

                active_title = app.screen.query_one("#screen-title", Static)
                return (
                    str(prompt_title.render()),
                    str(active_title.render()),
                    len(experience_repository.list_sessions()),
                )

    prompt_title, active_title, session_count = asyncio.run(run_test())

    assert prompt_title == "Unsaved Changes"
    assert active_title == "Experience"
    assert session_count == 0


def test_add_experience_back_prompt_can_save_unsaved_changes() -> None:
    async def run_test() -> tuple[str, str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#add-experience")
                await pilot.pause()

                app.screen.query_one("#experience-employer-name", Input).value = "Acme Analytics"
                app.screen.query_one("#experience-job-title", Input).value = "Senior Data Engineer"
                app.screen.query_one("#experience-start-month").value = "5"
                app.screen.query_one("#experience-start-year").value = "2021"
                app.screen.query_one("#experience-current-role", Checkbox).value = True
                app.screen.action_back()
                await pilot.pause()

                prompt_title = app.screen.query_one("#screen-title", Static)
                await pilot.click("#save-unsaved-experience")
                await pilot.pause()

                active_title = app.screen.query_one("#screen-title", Static)
                return (
                    str(prompt_title.render()),
                    str(active_title.render()),
                    len(experience_repository.list_sessions()),
                )

    prompt_title, active_title, session_count = asyncio.run(run_test())

    assert prompt_title == "Unsaved Changes"
    assert active_title == "Experience"
    assert session_count == 1


def test_add_source_entry_then_back_does_not_prompt_for_saved_source() -> None:
    async def run_test() -> tuple[str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#add-experience")
                await pilot.pause()

                app.screen.query_one("#experience-employer-name", Input).value = "Acme Analytics"
                app.screen.query_one("#experience-job-title", Input).value = "Senior Data Engineer"
                app.screen.query_one("#experience-start-month").value = "5"
                app.screen.query_one("#experience-start-year").value = "2021"
                app.screen.query_one("#experience-current-role", Checkbox).value = True
                await pilot.click("#save-experience")
                await pilot.pause()

                app.screen.query_one(
                    "#experience-source-text", TextArea
                ).text = "- Built reporting automation"
                app.screen._add_source_entry()
                await pilot.pause()

                app.screen.action_back()
                await pilot.pause()

                active_title = app.screen.query_one("#screen-title", Static)
                session = experience_repository.list_sessions()[0]
                return str(active_title.render()), len(session.source_entries)

    active_title, source_count = asyncio.run(run_test())

    assert active_title == "Experience"
    assert source_count == 1


def test_analyze_sources_generates_candidate_bullets_for_review() -> None:
    async def run_test() -> tuple[str, str, str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            experience_service = ExperienceIntakeService(
                experience_repository,
                FakeExperienceIntakeAssistant(),
            )
            session = experience_service.create_session()
            session = experience_service.capture_role_details(
                session.id,
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                is_current_role=True,
            )
            session = experience_service.add_source_entry(
                session.id,
                "- Built reporting automation",
            )
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=experience_service,
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click(f"#edit-experience-session-{session.id}")
                await pilot.pause()
                await pilot.click("#analyze-source-entries")
                await pilot.pause()

                bullet_card = app.screen.query_one(CandidateBulletCard)
                bullet_text = bullet_card.query_one(".read-only-panel", Static)
                status = bullet_card.query_one(".status-pill", Static)
                app.screen._mark_candidate_bullet_reviewed("bullet-1")
                await pilot.pause()

                updated = experience_repository.load_session(session.id)
                assert updated is not None
                return (
                    str(status.render()),
                    str(bullet_text.render()),
                    updated.candidate_bullets[0].status.value,
                    str(updated.source_entries[0].analyzed_at is not None),
                )

    status_label, bullet_text, bullet_status, source_analyzed = asyncio.run(run_test())

    assert status_label == "Needs Review"
    assert bullet_text == "Reduced manual reporting work by building reporting automation."
    assert bullet_status == "reviewed"
    assert source_analyzed == "True"


def test_edit_experience_screen_updates_existing_session() -> None:
    async def run_test() -> tuple[str, str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            session = ExperienceIntakeSession(
                id="session-123",
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                status=ExperienceIntakeStatus.SOURCE_CAPTURED,
                source_text="- Built reporting automation",
                start_date="05/2021",
                is_current_role=True,
            )
            experience_repository.save_session(session)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 100)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()
                await pilot.click("#edit-experience-session-session-123")
                await pilot.pause()

                title = app.screen.query_one("#screen-title", Static)
                app.screen.query_one(
                    "#experience-job-title", Input
                ).value = "Principal Data Engineer"
                await pilot.click("#save-experience")
                await pilot.pause()

                updated = experience_repository.load_session("session-123")
                assert updated is not None
                return (
                    str(title.render()),
                    updated.job_title or "",
                    len(experience_repository.list_sessions()),
                )

    screen_title, job_title, session_count = asyncio.run(run_test())

    assert screen_title == "Edit Role"
    assert job_title == "Principal Data Engineer"
    assert session_count == 1


def test_experience_screen_back_returns_to_career_profile() -> None:
    async def run_test() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()
                await pilot.click("#open-experience-intake")
                await pilot.pause()

                app.screen.action_back()
                await pilot.pause()

                title = app.screen.query_one("#screen-title", Static)
                return str(title.render())

    assert asyncio.run(run_test()) == "Career Profile"


def test_career_profile_screen_opens_experience_sessions_and_detail() -> None:
    async def run_test() -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            profile_service = ProfileService(FileProfileRepository(data_dir))
            experience_repository = FileExperienceIntakeRepository(data_dir)
            draft = ExperienceEntry(
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                accomplishments=["Reduced reporting time by 10 hours per week."],
            )
            session = ExperienceIntakeSession(
                id="session-123",
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                status=ExperienceIntakeStatus.DRAFT_GENERATED,
                source_text="- Built reporting automation",
                draft_experience_entry=draft,
            )
            experience_repository.save_session(session)
            app = CareerAgentTUI(
                settings=Settings(data_dir=data_dir),
                profile_service=profile_service,
                experience_intake_service=ExperienceIntakeService(experience_repository),
            )

            async with app.run_test(size=(160, 80)) as pilot:
                app.action_open_career_profile()
                await pilot.pause()

                await pilot.click("#open-experience-intake")
                await pilot.pause()

                card_title = app.screen.query_one(".card-title", Static)
                await pilot.click("#view-experience-session-session-123")
                await pilot.pause()

                detail_title = app.screen.query_one("#screen-title", Static)
                return str(card_title.render()), str(detail_title.render())

    card_title, detail_title = asyncio.run(run_test())

    assert card_title == "Senior Data Engineer at Acme Analytics"
    assert detail_title == "Senior Data Engineer at Acme Analytics"
