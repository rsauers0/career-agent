from __future__ import annotations

from typing import ClassVar
from zoneinfo import available_timezones

from pydantic import ValidationError
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Select, Static

from career_agent.application.dashboard import (
    DashboardCard,
    DashboardSection,
    DashboardStatus,
    JobWorkflowState,
    build_dashboard_sections,
)
from career_agent.application.preferences_builder import (
    PreferenceWizardAnswers,
    build_user_preferences_from_answers,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
from career_agent.config import Settings, get_settings
from career_agent.domain.models import CommuteDistanceUnit, UserPreferences, WorkArrangement
from career_agent.infrastructure.repositories import FileProfileRepository

TIME_ZONE_OPTIONS = [(time_zone, time_zone) for time_zone in sorted(available_timezones())]
COMMUTE_DISTANCE_UNIT_OPTIONS = [
    ("miles", CommuteDistanceUnit.MILES.value),
    ("kilometers", CommuteDistanceUnit.KILOMETERS.value),
]
CURRENCY_OPTIONS = [
    ("USD", "USD"),
    ("CAD", "CAD"),
    ("EUR", "EUR"),
    ("GBP", "GBP"),
    ("AUD", "AUD"),
]
REQUIRED_MARKER = "[#f05f5f]*[/]"

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


def format_form_list(values: list[str], empty_message: str) -> str:
    """Format a dynamic form list with a clear empty state."""

    if not values:
        return empty_message
    return "\n".join(f"- {value}" for value in values)


def parse_form_list(value: str) -> list[str]:
    """Parse a comma-separated form value into display list items."""

    return [item.strip() for item in value.split(",") if item.strip()]


def required_label(label: str) -> str:
    """Return a form label with a red required marker."""

    return f"{label} {REQUIRED_MARKER}"


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
        ("Minimum Salary Desired", format_optional_text(preferences.desired_salary_min)),
        ("Salary Currency", preferences.salary_currency),
        ("Maximum Commute Distance", format_optional_text(preferences.max_commute_distance)),
        ("Commute Distance Unit", preferences.commute_distance_unit.value),
        ("Maximum Commute Time (minutes)", format_optional_text(preferences.max_commute_time)),
        ("Work Authorization", "Yes" if preferences.work_authorization else "No"),
        (
            "Requires Work Sponsorship",
            "Yes" if preferences.requires_work_sponsorship else "No",
        ),
    ]


def build_user_preferences_form_defaults(preferences: UserPreferences | None) -> dict[str, str]:
    """Return initial string values for the editable preferences form."""

    if preferences is None:
        return {
            "full_name": "",
            "base_location": "",
            "time_zone": "",
            "target_job_titles": "",
            "preferred_locations": "",
            "preferred_work_arrangements": "",
            "desired_salary_min": "",
            "salary_currency": "USD",
            "max_commute_distance": "",
            "commute_distance_unit": "miles",
            "max_commute_time": "",
        }

    return {
        "full_name": preferences.full_name,
        "base_location": preferences.base_location,
        "time_zone": preferences.time_zone or "",
        "target_job_titles": ", ".join(preferences.target_job_titles),
        "preferred_locations": ", ".join(preferences.preferred_locations),
        "preferred_work_arrangements": ", ".join(
            arrangement.value for arrangement in preferences.preferred_work_arrangements
        ),
        "desired_salary_min": (
            str(preferences.desired_salary_min)
            if preferences.desired_salary_min is not None
            else ""
        ),
        "salary_currency": preferences.salary_currency,
        "max_commute_distance": (
            str(preferences.max_commute_distance)
            if preferences.max_commute_distance is not None
            else ""
        ),
        "commute_distance_unit": preferences.commute_distance_unit.value,
        "max_commute_time": (
            str(preferences.max_commute_time) if preferences.max_commute_time is not None else ""
        ),
    }


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
    """Editable user preferences screen."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, profile_service: ProfileService) -> None:
        super().__init__()
        self.profile_service = profile_service
        self.target_job_titles: list[str] = []
        self.preferred_locations: list[str] = []
        self._list_state_initialized = False

    def compose(self) -> ComposeResult:
        preferences = self.profile_service.get_user_preferences()
        status = self.profile_service.get_user_preferences_status()
        defaults = build_user_preferences_form_defaults(preferences)
        if not self._list_state_initialized:
            self.target_job_titles = parse_form_list(defaults["target_job_titles"])
            self.preferred_locations = parse_form_list(defaults["preferred_locations"])
            self._list_state_initialized = True

        yield Header(show_clock=True)
        with Container(id="preferences-screen"):
            yield Static("User Preferences", id="screen-title")
            yield Static(
                "Edit preferences, then save once when the form is ready.",
                classes="help-text",
            )
            yield StatusCard(
                DashboardCard(
                    title="User Preferences",
                    status=status,
                    detail=get_status_detail(status)[0],
                )
            )

            yield Static("", id="preference-message", classes="form-message")
            yield Static(
                f"{REQUIRED_MARKER} = required field",
                classes="required-legend",
            )

            with VerticalScroll(id="preferences-form"):
                yield Static(required_label("Full Name"), classes="form-label required-label")
                yield Input(value=defaults["full_name"], id="pref-full-name")

                yield Static(required_label("Base Location"), classes="form-label required-label")
                yield Static("City, State ZIP", classes="field-tip")
                yield Input(value=defaults["base_location"], id="pref-base-location")

                yield Static("Time Zone", classes="form-label")
                yield Select(
                    TIME_ZONE_OPTIONS,
                    prompt="Select time zone",
                    allow_blank=True,
                    value=defaults["time_zone"] or Select.NULL,
                    id="pref-time-zone",
                )

                yield Static("Target Job Titles", classes="form-label")
                yield Static("Add one title at a time.", classes="field-tip")
                with Horizontal(classes="list-entry-row"):
                    yield Input(
                        placeholder="Senior Data Engineer",
                        id="pref-target-job-title-input",
                    )
                    yield Button("Add", id="add-target-job-title")
                    yield Button("Clear", id="clear-target-job-titles")
                yield Static(
                    format_form_list(self.target_job_titles, "No titles added."),
                    id="pref-target-job-titles-panel",
                    classes="list-display-panel",
                )

                yield Static("Preferred Locations", classes="form-label")
                yield Static(
                    (
                        "Add one location at a time, such as Chicago, IL. "
                        "Use this when preferred work locations differ from your base location "
                        "or you are open to relocation."
                    ),
                    classes="field-tip",
                )
                with Horizontal(classes="list-entry-row"):
                    yield Input(
                        placeholder="Chicago, IL",
                        id="pref-preferred-location-input",
                    )
                    yield Button("Add", id="add-preferred-location")
                    yield Button("Clear", id="clear-preferred-locations")
                yield Static(
                    format_form_list(self.preferred_locations, "No locations added."),
                    id="pref-preferred-locations-panel",
                    classes="list-display-panel",
                )

                yield Static(
                    required_label("Preferred Work Arrangements"),
                    classes="form-label required-label",
                )
                selected_work_arrangements = set(
                    parse_form_list(defaults["preferred_work_arrangements"])
                )
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(
                        "Remote",
                        value=WorkArrangement.REMOTE.value in selected_work_arrangements,
                        id="pref-work-arrangement-remote",
                    )
                    yield Checkbox(
                        "Hybrid",
                        value=WorkArrangement.HYBRID.value in selected_work_arrangements,
                        id="pref-work-arrangement-hybrid",
                    )
                    yield Checkbox(
                        "Onsite",
                        value=WorkArrangement.ONSITE.value in selected_work_arrangements,
                        id="pref-work-arrangement-onsite",
                    )

                yield Static("Minimum Salary Desired", classes="form-label")
                with Horizontal(classes="salary-row"):
                    yield Input(value=defaults["desired_salary_min"], id="pref-desired-salary-min")
                    yield Select(
                        CURRENCY_OPTIONS,
                        allow_blank=False,
                        value=defaults["salary_currency"],
                        id="pref-salary-currency",
                    )

                with Vertical(classes="form-section commute-section"):
                    yield Static("Commute Preferences", classes="form-label")
                    yield Static(
                        "Distance with unit, plus maximum time in minutes.",
                        classes="field-tip",
                    )
                    with Horizontal(classes="commute-row"):
                        with Vertical(classes="commute-distance-group"):
                            yield Static("Max Commute Distance", classes="sub-label")
                            with Horizontal(classes="commute-distance-row"):
                                yield Input(
                                    value=defaults["max_commute_distance"],
                                    placeholder="50",
                                    id="pref-max-commute-distance",
                                )
                                yield Select(
                                    COMMUTE_DISTANCE_UNIT_OPTIONS,
                                    allow_blank=False,
                                    value=defaults["commute_distance_unit"],
                                    id="pref-commute-distance-unit",
                                )
                        with Vertical(classes="commute-time-group"):
                            yield Static("Max Commute Time (in minutes)", classes="sub-label")
                            yield Input(
                                value=defaults["max_commute_time"],
                                placeholder="Minutes",
                                id="pref-max-commute-time",
                            )

                yield Static("Work Authorization", classes="form-label")
                yield Static(
                    "Sponsorship may include visas such as H-1B.",
                    classes="field-tip",
                )
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(
                        "Legally authorized to work",
                        value=preferences.work_authorization if preferences else True,
                        id="pref-work-authorization",
                    )
                    yield Checkbox(
                        "Requires employer sponsorship (e.g. H-1B)",
                        value=preferences.requires_work_sponsorship if preferences else False,
                        id="pref-requires-work-sponsorship",
                    )

                yield Button("Save Preferences", id="save-preferences", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle form button actions."""

        if event.button.id == "save-preferences":
            self._save_preferences()
        elif event.button.id == "add-target-job-title":
            await self._add_list_item(
                input_id="pref-target-job-title-input",
                values=self.target_job_titles,
                panel_id="pref-target-job-titles-panel",
                empty_message="No titles added.",
            )
        elif event.button.id == "clear-target-job-titles":
            await self._clear_list(
                values=self.target_job_titles,
                panel_id="pref-target-job-titles-panel",
                empty_message="No titles added.",
            )
        elif event.button.id == "add-preferred-location":
            await self._add_list_item(
                input_id="pref-preferred-location-input",
                values=self.preferred_locations,
                panel_id="pref-preferred-locations-panel",
                empty_message="No locations added.",
            )
        elif event.button.id == "clear-preferred-locations":
            await self._clear_list(
                values=self.preferred_locations,
                panel_id="pref-preferred-locations-panel",
                empty_message="No locations added.",
            )

    def action_back(self) -> None:
        """Return to the dashboard."""

        self.app.pop_screen()
        self.app.refresh(recompose=True)

    def _save_preferences(self) -> None:
        try:
            preferences = build_user_preferences_from_answers(self._collect_answers())
        except (ValueError, ValidationError) as exc:
            self._set_message(f"Could not save preferences: {exc}")
            return

        self.profile_service.save_user_preferences(preferences)
        self._set_message("Saved user preferences. Press b or Esc to return to the dashboard.")

    def _collect_answers(self) -> PreferenceWizardAnswers:
        return PreferenceWizardAnswers(
            full_name=self._input_value("pref-full-name"),
            base_location=self._input_value("pref-base-location"),
            time_zone=self._select_value("pref-time-zone"),
            target_job_titles=", ".join(self.target_job_titles),
            preferred_locations=", ".join(self.preferred_locations),
            preferred_work_arrangements=", ".join(self._selected_work_arrangements()),
            desired_salary_min=self._input_value("pref-desired-salary-min"),
            salary_currency=self._select_value("pref-salary-currency"),
            max_commute_distance=self._input_value("pref-max-commute-distance"),
            commute_distance_unit=self._select_value("pref-commute-distance-unit"),
            max_commute_time=self._input_value("pref-max-commute-time"),
            work_authorization=self.query_one("#pref-work-authorization", Checkbox).value,
            requires_work_sponsorship=self.query_one(
                "#pref-requires-work-sponsorship",
                Checkbox,
            ).value,
        )

    def _input_value(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value

    def _select_value(self, widget_id: str) -> str:
        value = self.query_one(f"#{widget_id}", Select).value
        if value is Select.NULL or value is Select.BLANK:
            return ""
        return str(value)

    def _selected_work_arrangements(self) -> list[str]:
        selected: list[str] = []
        if self.query_one("#pref-work-arrangement-remote", Checkbox).value:
            selected.append(WorkArrangement.REMOTE.value)
        if self.query_one("#pref-work-arrangement-hybrid", Checkbox).value:
            selected.append(WorkArrangement.HYBRID.value)
        if self.query_one("#pref-work-arrangement-onsite", Checkbox).value:
            selected.append(WorkArrangement.ONSITE.value)
        return selected

    async def _add_list_item(
        self,
        input_id: str,
        values: list[str],
        panel_id: str,
        empty_message: str,
    ) -> None:
        input_widget = self.query_one(f"#{input_id}", Input)
        value = input_widget.value.strip()
        if not value:
            return
        if value not in values:
            values.append(value)
        input_widget.value = ""
        await self._update_list_display(
            panel_id=panel_id,
            values=values,
            empty_message=empty_message,
        )

    async def _clear_list(
        self,
        values: list[str],
        panel_id: str,
        empty_message: str,
    ) -> None:
        values.clear()
        await self._update_list_display(
            panel_id=panel_id,
            values=values,
            empty_message=empty_message,
        )

    async def _update_list_display(
        self,
        panel_id: str,
        values: list[str],
        empty_message: str,
    ) -> None:
        self.query_one(f"#{panel_id}", Static).update(format_form_list(values, empty_message))

    def _set_message(self, message: str) -> None:
        self.query_one("#preference-message", Static).update(message)


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

    Select {
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
