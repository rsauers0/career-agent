from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Static

from career_agent.application.dashboard import build_dashboard_statuses
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


def format_component_name(component: str) -> str:
    """Convert an internal component key into a display label."""

    return component.replace("_", " ").title()


class StatusCard(Static):
    """Dashboard card for one workflow component."""

    def __init__(self, status: ComponentStatus) -> None:
        super().__init__()
        self.status = status

    def compose(self) -> ComposeResult:
        yield Static(format_component_name(self.status.component), classes="card-title")
        yield Static(
            STATUS_LABELS[self.status.state],
            classes=f"status-pill status-{self.status.state.value}",
        )

        if self.status.missing_required:
            yield Static(
                f"Missing required: {', '.join(self.status.missing_required)}",
                classes="status-detail required-detail",
            )
        elif self.status.missing_recommended:
            yield Static(
                f"Recommended: {', '.join(self.status.missing_recommended)}",
                classes="status-detail recommended-detail",
            )
        else:
            yield Static("Ready for the next workflow step.", classes="status-detail")


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
        statuses = build_dashboard_statuses(self.profile_service)

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
                    for status in statuses:
                        yield StatusCard(status)

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
