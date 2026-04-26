from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from textual.widgets import Checkbox, Input, Static

from career_agent.application.dashboard import JobWorkflowState, JobWorkflowStatus
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
from career_agent.config import Settings, get_settings
from career_agent.domain.models import UserPreferences, WorkArrangement
from career_agent.infrastructure.repositories import FileProfileRepository
from career_agent.interfaces.tui import (
    CareerAgentTUI,
    StatusCard,
    build_tui,
    build_user_preferences_form_defaults,
    build_user_preferences_rows,
    format_component_name,
    format_form_list,
    format_list,
    format_optional_text,
    get_status_detail,
    get_status_label,
    parse_form_list,
    required_label,
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
