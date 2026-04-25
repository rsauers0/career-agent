from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from textual.widgets import Input, Static

from career_agent.application.dashboard import JobWorkflowState, JobWorkflowStatus
from career_agent.application.profile_service import ProfileService
from career_agent.config import Settings, get_settings
from career_agent.domain.models import UserPreferences, WorkArrangement
from career_agent.infrastructure.repositories import FileProfileRepository
from career_agent.interfaces.tui import (
    CareerAgentTUI,
    build_tui,
    build_user_preferences_form_defaults,
    build_user_preferences_rows,
    format_component_name,
    format_form_list,
    format_list,
    format_optional_text,
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
