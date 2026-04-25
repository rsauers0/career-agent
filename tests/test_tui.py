from __future__ import annotations

from career_agent.application.dashboard import JobWorkflowState, JobWorkflowStatus
from career_agent.config import get_settings
from career_agent.domain.models import UserPreferences, WorkArrangement
from career_agent.interfaces.tui import (
    build_tui,
    build_user_preferences_rows,
    format_component_name,
    format_list,
    format_optional_text,
    get_status_label,
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
    assert rows["Work Authorization"] == "Yes"
    assert rows["Requires Work Sponsorship"] == "No"


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
