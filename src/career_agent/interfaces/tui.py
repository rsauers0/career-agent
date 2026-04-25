from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from career_agent.application.dashboard import (
    DashboardCard,
    DashboardSection,
    DashboardStatus,
    JobWorkflowState,
    build_dashboard_sections,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
from career_agent.config import Settings, get_settings
from career_agent.domain.models import UserPreferences
from career_agent.infrastructure.repositories import FileProfileRepository

STATUS_LABELS = {
    ComponentStatusState.NOT_STARTED: "Not Started",
    ComponentStatusState.INCOMPLETE: "Incomplete",
    ComponentStatusState.PARTIAL: "Partial",
    ComponentStatusState.COMPLETE: "Complete",
}

JOB_STATUS_LABELS = {
    JobWorkflowState.IDLE: "Idle",
    JobWorkflowState.QUEUED: "Queued",
    JobWorkflowState.PROCESSING: "Processing",
    JobWorkflowState.COMPLETED: "Completed",
    JobWorkflowState.FAILED: "Failed",
}


def format_component_name(component: str) -> str:
    """Convert an internal component key into a display label."""

    return component.replace("_", " ").title()


def format_optional_text(value: object | None) -> str:
    """Format an optional value for display."""

    if value is None:
        return "-"
    if isinstance(value, str):
        return value.strip() or "-"
    return str(value)


def format_list(values: list[object]) -> str:
    """Format a list value for display."""

    return ", ".join(str(value) for value in values) or "-"


def build_user_preferences_rows(preferences: UserPreferences) -> list[tuple[str, str]]:
    """Return read-only display rows for user preferences."""

    return [
        ("Full Name", preferences.full_name),
        ("Base Location", preferences.base_location),
        ("Time Zone", format_optional_text(preferences.time_zone)),
        ("Target Job Titles", format_list(preferences.target_job_titles)),
        ("Preferred Locations", format_list(preferences.preferred_locations)),
        (
            "Preferred Work Arrangements",
            format_list(
                [arrangement.value for arrangement in preferences.preferred_work_arrangements]
            ),
        ),
        ("Desired Salary Minimum", format_optional_text(preferences.desired_salary_min)),
        ("Salary Currency", preferences.salary_currency),
        ("Maximum Commute Distance", format_optional_text(preferences.max_commute_distance)),
        ("Commute Distance Unit", preferences.commute_distance_unit.value),
        ("Maximum Commute Time", format_optional_text(preferences.max_commute_time)),
        ("Work Authorization", "Yes" if preferences.work_authorization else "No"),
        (
            "Requires Work Sponsorship",
            "Yes" if preferences.requires_work_sponsorship else "No",
        ),
    ]


def get_status_label(status: DashboardStatus) -> str:
    """Return the user-facing label for a dashboard status state."""

    if isinstance(status, ComponentStatus):
        return STATUS_LABELS[status.state]
    return JOB_STATUS_LABELS[status.state]


def get_status_class(status: DashboardStatus) -> str:
    """Return the CSS class suffix for a dashboard status state."""

    return status.state.value


def get_status_detail(status: ComponentStatus) -> tuple[str, str]:
    """Return detail text and CSS class for a dashboard card."""

    if status.missing_required:
        return (
            f"Missing required: {', '.join(status.missing_required)}",
            "status-detail required-detail",
        )

    if status.missing_recommended:
        return (
            f"Recommended: {', '.join(status.missing_recommended)}",
            "status-detail recommended-detail",
        )

    return "Ready for the next workflow step.", "status-detail"


class StatusCard(Static):
    """Dashboard card for one workflow component."""

    def __init__(self, card: DashboardCard) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        detail_classes = get_dashboard_card_detail_class(self.card.status)

        yield Static(self.card.title, classes="card-title")
        yield Static(
            get_status_label(self.card.status),
            classes=f"status-pill status-{get_status_class(self.card.status)}",
        )
        yield Static(self.card.detail, classes=detail_classes)

        if self.card.shortcut:
            yield Static(f"Shortcut: {self.card.shortcut}", classes="shortcut-hint")


def get_dashboard_card_detail_class(status: DashboardStatus) -> str:
    """Return the CSS class for dashboard card detail text."""

    if isinstance(status, ComponentStatus) and status.missing_required:
        return "status-detail required-detail"

    if isinstance(status, ComponentStatus) and status.missing_recommended:
        return "status-detail recommended-detail"

    return "status-detail"


class DashboardSectionView(Static):
    """TUI section containing related dashboard status cards."""

    def __init__(self, section: DashboardSection) -> None:
        super().__init__()
        self.section = section

    def compose(self) -> ComposeResult:
        yield Static(self.section.title, classes="section-title")
        for card in self.section.cards:
            yield StatusCard(card)


class PreferencesScreen(Screen[None]):
    """Read-only user preferences screen."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, profile_service: ProfileService) -> None:
        super().__init__()
        self.profile_service = profile_service

    def compose(self) -> ComposeResult:
        preferences = self.profile_service.get_user_preferences()
        status = self.profile_service.get_user_preferences_status()

        yield Header(show_clock=True)
        with Container(id="preferences-screen"):
            yield Static("User Preferences", id="screen-title")
            yield Static(
                "Read-only view. Editing will be added in the next workflow slice.",
                classes="help-text",
            )
            yield StatusCard(
                DashboardCard(
                    title="User Preferences",
                    status=status,
                    detail=get_status_detail(status)[0],
                )
            )

            if preferences is None:
                yield Static(
                    "No user preferences have been saved yet.",
                    classes="empty-state",
                )
            else:
                with VerticalScroll(id="preferences-details"):
                    for label, value in build_user_preferences_rows(preferences):
                        with Horizontal(classes="preference-row"):
                            yield Static(label, classes="preference-label")
                            yield Static(value, classes="preference-value")
        yield Footer()

    def action_back(self) -> None:
        """Return to the dashboard."""

        self.app.pop_screen()


class CareerAgentTUI(App[None]):
    """Textual application shell for Career Agent."""

    TITLE: ClassVar[str] = "Career Agent"

    CSS: ClassVar[str] = """
    Screen {
        background: #101820;
        color: #f4efe6;
    }

    Header {
        background: #263b3f;
        color: #f4efe6;
    }

    Footer {
        background: #263b3f;
        color: #f4efe6;
    }

    #dashboard {
        padding: 1 2;
    }

    #preferences-screen {
        padding: 1 2;
    }

    #hero {
        height: auto;
        margin-bottom: 1;
    }

    #title {
        text-style: bold;
        text-align: center;
        color: #f5c16c;
        margin-bottom: 1;
    }

    #subtitle {
        text-align: center;
        color: #c9d1c8;
        margin-bottom: 1;
    }

    #data-dir {
        color: #9fb8ad;
        text-align: center;
    }

    #screen-title {
        text-style: bold;
        color: #f5c16c;
        margin-bottom: 1;
    }

    .help-text {
        color: #c9d1c8;
        margin-bottom: 1;
    }

    #main-content {
        height: 1fr;
    }

    #status-grid {
        width: 2fr;
        height: 1fr;
    }

    #assistant-panel {
        width: 1fr;
        min-width: 28;
        border: round #5d7b6f;
        padding: 1 2;
        margin-left: 1;
        background: #172429;
    }

    #preferences-details {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
    }

    .preference-row {
        height: auto;
        margin-bottom: 1;
    }

    .preference-label {
        width: 32;
        color: #f5c16c;
        text-style: bold;
    }

    .preference-value {
        width: 1fr;
        color: #f4efe6;
    }

    .empty-state {
        border: round #5d7b6f;
        padding: 1 2;
        color: #c9d1c8;
        background: #172429;
    }

    .section-title {
        text-style: bold;
        color: #f5c16c;
        margin-bottom: 1;
    }

    StatusCard {
        border: round #5d7b6f;
        padding: 1 2;
        margin-bottom: 1;
        background: #172429;
        height: auto;
    }

    .card-title {
        text-style: bold;
        color: #f4efe6;
    }

    .status-pill {
        width: auto;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
        text-style: bold;
    }

    .status-not_started {
        background: #4d5960;
        color: #f4efe6;
    }

    .status-incomplete {
        background: #9c4f42;
        color: #fff8ed;
    }

    .status-partial {
        background: #b88746;
        color: #101820;
    }

    .status-complete {
        background: #5d7b6f;
        color: #f4efe6;
    }

    .status-idle {
        background: #355266;
        color: #f4efe6;
    }

    .status-queued {
        background: #6f6690;
        color: #f4efe6;
    }

    .status-processing {
        background: #b88746;
        color: #101820;
    }

    .status-completed {
        background: #5d7b6f;
        color: #f4efe6;
    }

    .status-failed {
        background: #9c4f42;
        color: #fff8ed;
    }

    .status-detail {
        color: #c9d1c8;
    }

    .shortcut-hint {
        color: #9fb8ad;
    }

    .required-detail {
        color: #f0a79b;
    }

    .recommended-detail {
        color: #f5c16c;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("p", "open_preferences", "Preferences"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, settings: Settings, profile_service: ProfileService) -> None:
        super().__init__()
        self.settings = settings
        self.profile_service = profile_service

    def compose(self) -> ComposeResult:
        sections = build_dashboard_sections(self.profile_service)

        yield Header(show_clock=True)
        with Container(id="dashboard"):
            with Vertical(id="hero"):
                yield Static("Career Agent", id="title")
                yield Static(
                    "Local-first career profile, job search, and document workflows.",
                    id="subtitle",
                )
                yield Static(f"Data directory: {self.settings.data_dir}", id="data-dir")

            with Horizontal(id="main-content"):
                with VerticalScroll(id="status-grid"):
                    yield Static("Workflow Status", classes="section-title")
                    for section in sections:
                        yield DashboardSectionView(section)

                with Vertical(id="assistant-panel"):
                    yield Static("Assistant", classes="section-title")
                    yield Static("LLM assistant not configured yet.", classes="status-detail")
        yield Footer()

    def action_open_preferences(self) -> None:
        """Open the read-only user preferences screen."""

        self.push_screen(PreferencesScreen(self.profile_service))


def build_tui() -> CareerAgentTUI:
    """Create the Textual app with production settings and infrastructure."""

    settings = get_settings()
    profile_service = ProfileService(FileProfileRepository(settings.data_dir))
    return CareerAgentTUI(settings=settings, profile_service=profile_service)


def run_tui() -> None:
    """Run the Textual interface."""

    build_tui().run()
