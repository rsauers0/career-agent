from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Static

from career_agent.application.dashboard import build_dashboard_sections
from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.application.profile_service import ProfileService
from career_agent.config import Settings, get_settings
from career_agent.infrastructure.repositories import (
    FileExperienceIntakeRepository,
    FileProfileRepository,
)
from career_agent.interfaces.tui_dashboard import DashboardSectionView
from career_agent.interfaces.tui_preferences import PreferencesScreen
from career_agent.interfaces.tui_profile import CareerProfileScreen


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

    #experience-screen {
        padding: 1 2;
    }

    #experience-detail-screen {
        padding: 1 2;
    }

    #add-experience-screen {
        padding: 1 2;
    }

    #career-profile-screen {
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

    #preferences-form {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
    }

    Input {
        margin-bottom: 1;
    }

    Checkbox {
        margin-bottom: 1;
    }

    Button {
        margin-top: 1;
        width: auto;
    }

    Button.-primary {
        color: #f4efe6;
        background: #0f8ec7;
        text-style: bold;
    }

    Button.-primary:hover {
        color: #f4efe6;
        background: #18a8e6;
    }

    Button.-primary:focus {
        color: #f4efe6;
        background: #18a8e6;
        border: tall #f5c16c;
    }

    Button:disabled {
        color: #9fb8ad;
        background: #2d393d;
    }

    .danger-button {
        color: #f4efe6;
        background: #8a3f38;
        text-style: bold;
    }

    .danger-button:hover {
        color: #f4efe6;
        background: #a84d43;
    }

    .danger-button:focus {
        color: #f4efe6;
        background: #a84d43;
        border: tall #f5c16c;
    }

    Select {
        margin-bottom: 1;
    }

    TextArea {
        height: 10;
        margin-bottom: 1;
    }

    #pref-max-commute-distance {
        width: 12;
    }

    #pref-commute-distance-unit {
        width: 20;
        height: 3;
    }

    #pref-max-commute-time {
        width: 16;
    }

    #pref-desired-salary-min {
        width: 18;
    }

    #pref-salary-currency {
        width: 14;
    }

    .list-entry-row {
        height: auto;
    }

    .list-entry-row Input {
        width: 1fr;
    }

    .list-entry-row Button {
        margin-left: 1;
    }

    .list-display-panel {
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
    }

    .salary-row {
        height: auto;
    }

    .salary-row Input {
        margin-right: 1;
    }

    .checkbox-row {
        height: auto;
        margin-bottom: 1;
    }

    .checkbox-row Checkbox {
        width: 1fr;
        margin-right: 1;
    }

    .form-section {
        height: auto;
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
    }

    .commute-row {
        height: auto;
        width: auto;
        margin-bottom: 1;
    }

    .commute-distance-group {
        width: 36;
        height: auto;
        margin-right: 2;
    }

    .commute-time-group {
        width: 30;
        height: auto;
    }

    .commute-distance-row {
        height: auto;
    }

    .commute-row Input {
        margin-right: 1;
    }

    .commute-row Select {
        margin-right: 1;
    }

    .form-label {
        color: #f5c16c;
        text-style: bold;
    }

    .sub-label {
        color: #f5c16c;
    }

    .required-label {
        color: #f0d58c;
    }

    .required-legend {
        color: #c9d1c8;
        margin-bottom: 1;
    }

    .field-tip {
        color: #9fb8ad;
        margin-bottom: 1;
    }

    .form-message {
        color: #c9d1c8;
        margin-bottom: 1;
    }

    .message-error {
        color: #f0a79b;
        background: #2a1717;
        border-left: thick #9c4f42;
        padding: 1 2;
    }

    .message-warning {
        color: #f0a79b;
        background: #2a1717;
        border-left: thick #9c4f42;
        padding: 1 2;
        margin-bottom: 1;
    }

    .message-success {
        color: #b8d8c0;
        background: #14241b;
        border-left: thick #5d7b6f;
        padding: 1 2;
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

    .dashboard-card-button {
        margin-top: 1;
        color: #f4efe6;
        background: #0f8ec7;
        text-style: bold;
    }

    .dashboard-card-button:hover {
        color: #f4efe6;
        background: #18a8e6;
    }

    .dashboard-card-button:focus {
        color: #f4efe6;
        background: #18a8e6;
        border: tall #f5c16c;
    }

    #profile-metrics {
        height: auto;
        margin-bottom: 1;
    }

    ProfileMetricCard {
        width: 1fr;
        height: auto;
        border: round #5d7b6f;
        padding: 1 2;
        margin-right: 1;
        background: #172429;
    }

    .metric-value {
        text-style: bold;
        color: #f5c16c;
        text-align: center;
    }

    .metric-label {
        text-style: bold;
        color: #f4efe6;
        text-align: center;
        margin-bottom: 1;
    }

    #career-profile-actions {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
    }

    .profile-action-row {
        height: auto;
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
    }

    .profile-action-copy {
        width: 70%;
        height: auto;
        margin-right: 4;
    }

    .profile-action-button-container {
        width: 28;
        height: auto;
    }

    .profile-action-button {
        width: 26;
    }

    #experience-session-list {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
    }

    #experience-detail {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
        margin-top: 1;
    }

    ExperienceSessionCard {
        border: round #5d7b6f;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
        height: auto;
    }

    SourceEntryCard {
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
        height: auto;
    }

    .source-entry-heading {
        color: #f0d58c;
        text-style: bold;
    }

    .source-entry-summary-row {
        height: auto;
    }

    .source-entry-summary {
        width: 1fr;
        height: auto;
    }

    .source-entry-toggle {
        width: 16;
        margin-left: 2;
    }

    .session-open-button {
        margin-top: 1;
        color: #f4efe6;
        background: #0f8ec7;
        text-style: bold;
    }

    .session-open-button:hover {
        color: #f4efe6;
        background: #18a8e6;
    }

    .session-open-button:focus {
        color: #f4efe6;
        background: #18a8e6;
        border: tall #f5c16c;
    }

    .read-only-panel {
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
        color: #f4efe6;
    }

    .experience-entry-section {
        height: auto;
        border: round #355266;
        padding: 1 2;
        margin-bottom: 1;
        background: #111c20;
    }

    #add-experience-form {
        height: 1fr;
        border: round #5d7b6f;
        padding: 1 2;
        background: #172429;
    }

    .experience-date-row {
        height: auto;
        margin-bottom: 1;
    }

    .experience-date-row Select {
        width: 18;
        margin-right: 1;
    }

    .experience-date-row Checkbox {
        width: 24;
        margin-left: 1;
    }

    .experience-action-row {
        height: auto;
        margin-bottom: 1;
    }

    .experience-action-row Button {
        margin-right: 1;
    }

    .action-spacer {
        width: 1fr;
    }

    .status-draft {
        background: #4d5960;
        color: #f4efe6;
    }

    .status-source_captured {
        background: #355266;
        color: #f4efe6;
    }

    .status-questions_generated {
        background: #6f6690;
        color: #f4efe6;
    }

    .status-answers_captured {
        background: #b88746;
        color: #101820;
    }

    .status-draft_generated {
        background: #5d7b6f;
        color: #f4efe6;
    }

    .status-locked {
        background: #5d7b6f;
        color: #f4efe6;
    }

    .status-accepted {
        background: #5d7b6f;
        color: #f4efe6;
    }

    .status-abandoned {
        background: #9c4f42;
        color: #fff8ed;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("p", "open_preferences", "Preferences"),
        ("c", "open_career_profile", "Career Profile"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        settings: Settings,
        profile_service: ProfileService,
        experience_intake_service: ExperienceIntakeService | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.profile_service = profile_service
        self.experience_intake_service = experience_intake_service or ExperienceIntakeService(
            FileExperienceIntakeRepository(settings.data_dir)
        )

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
        """Open the editable user preferences screen."""

        self.push_screen(PreferencesScreen(self.profile_service))

    def action_open_career_profile(self) -> None:
        """Open the Career Profile overview screen."""

        self.push_screen(
            CareerProfileScreen(
                self.profile_service,
                self.experience_intake_service,
            )
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle dashboard card action buttons."""

        if event.button.id == "dashboard-action-preferences":
            self.action_open_preferences()
        elif event.button.id == "dashboard-action-career-profile":
            self.action_open_career_profile()


def build_tui() -> CareerAgentTUI:
    """Create the Textual app with production settings and infrastructure."""

    settings = get_settings()
    profile_repository = FileProfileRepository(settings.data_dir)
    profile_service = ProfileService(profile_repository)
    experience_intake_service = ExperienceIntakeService(
        FileExperienceIntakeRepository(settings.data_dir),
        profile_repository=profile_repository,
    )
    return CareerAgentTUI(
        settings=settings,
        profile_service=profile_service,
        experience_intake_service=experience_intake_service,
    )


def run_tui() -> None:
    """Run the Textual interface."""

    build_tui().run()
