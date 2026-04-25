from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Static

from career_agent.application.dashboard import (
    DashboardSection,
    JobWorkflowState,
    JobWorkflowStatus,
    build_dashboard_sections,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
from career_agent.config import Settings, get_settings
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

DashboardStatus = ComponentStatus | JobWorkflowStatus


def format_component_name(component: str) -> str:
    """Convert an internal component key into a display label."""

    return component.replace("_", " ").title()


def get_status_label(status: DashboardStatus) -> str:
    """Return the user-facing label for a dashboard status state."""

    if isinstance(status, ComponentStatus):
        return STATUS_LABELS[status.state]
    return JOB_STATUS_LABELS[status.state]


def get_status_class(status: DashboardStatus) -> str:
    """Return the CSS class suffix for a dashboard status state."""

    return status.state.value


def get_status_detail(status: DashboardStatus) -> tuple[str, str]:
    """Return detail text and CSS class for a dashboard card."""

    if isinstance(status, JobWorkflowStatus):
        return status.detail, "status-detail"

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

    def __init__(self, status: DashboardStatus) -> None:
        super().__init__()
        self.status = status

    def compose(self) -> ComposeResult:
        detail, detail_classes = get_status_detail(self.status)

        yield Static(format_component_name(self.status.component), classes="card-title")
        yield Static(
            get_status_label(self.status),
            classes=f"status-pill status-{get_status_class(self.status)}",
        )
        yield Static(detail, classes=detail_classes)


class DashboardSectionView(Static):
    """TUI section containing related dashboard status cards."""

    def __init__(self, section: DashboardSection) -> None:
        super().__init__()
        self.section = section

    def compose(self) -> ComposeResult:
        yield Static(self.section.title, classes="section-title")
        for status in self.section.items:
            yield StatusCard(status)


class CareerAgentTUI(App[None]):
    """Textual application shell for Career Agent."""

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

    .required-detail {
        color: #f0a79b;
    }

    .recommended-detail {
        color: #f5c16c;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
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


def build_tui() -> CareerAgentTUI:
    """Create the Textual app with production settings and infrastructure."""

    settings = get_settings()
    profile_service = ProfileService(FileProfileRepository(settings.data_dir))
    return CareerAgentTUI(settings=settings, profile_service=profile_service)


def run_tui() -> None:
    """Run the Textual interface."""

    build_tui().run()
