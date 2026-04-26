from __future__ import annotations

from typing import ClassVar
from zoneinfo import available_timezones

from pydantic import ValidationError
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Select, Static

from career_agent.application.dashboard import DashboardCard
from career_agent.application.preferences_builder import (
    PreferenceWizardAnswers,
    build_user_preferences_from_answers,
)
from career_agent.application.profile_service import ProfileService
from career_agent.domain.models import CommuteDistanceUnit, UserPreferences, WorkArrangement
from career_agent.interfaces.tui_dashboard import StatusCard, get_status_detail

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
PREFERENCE_FIELD_LABELS = {
    "full_name": "Full Name",
    "base_location": "Base Location",
    "preferred_work_arrangements": "Preferred Work Arrangements",
    "desired_salary_min": "Minimum Salary Desired",
    "max_commute_distance": "Max Commute Distance",
    "max_commute_time": "Max Commute Time",
}


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


def format_validation_messages(messages: list[str]) -> str:
    """Format validation feedback for the preferences form."""

    return "Could not save preferences:\n" + "\n".join(f"- {message}" for message in messages)


def format_preferences_error(error: ValueError | ValidationError) -> str:
    """Convert low-level validation errors into user-facing form feedback."""

    if isinstance(error, ValidationError):
        return format_validation_messages(
            [_format_pydantic_error(error_detail) for error_detail in error.errors()]
        )

    message = str(error)
    if "invalid literal for int()" in message:
        return format_validation_messages(
            ["Salary and commute preference values must be whole numbers."]
        )

    return format_validation_messages([message])


def _format_pydantic_error(error_detail: dict[str, object]) -> str:
    location = error_detail.get("loc", ())
    field_name = str(location[0]) if isinstance(location, tuple) and location else ""
    field_label = PREFERENCE_FIELD_LABELS.get(field_name, field_name or "Field")
    error_type = str(error_detail.get("type", ""))

    if error_type in {"string_too_short", "missing"}:
        return f"{field_label} is required."

    if error_type == "greater_than_equal":
        return f"{field_label} must be 0 or greater."

    return f"{field_label}: {error_detail.get('msg', 'Invalid value.')}"


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


class PreferencesScreen(Screen[None]):
    """Editable user preferences screen."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
        Binding("ctrl+s", "save_preferences", "Save", key_display="Ctrl+S"),
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

            yield Static("", id="preference-message", classes="form-message", markup=False)
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

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Add list items when Enter is pressed in list inputs."""

        if event.input.id == "pref-target-job-title-input":
            event.stop()
            await self._add_list_item(
                input_id="pref-target-job-title-input",
                values=self.target_job_titles,
                panel_id="pref-target-job-titles-panel",
                empty_message="No titles added.",
            )
        elif event.input.id == "pref-preferred-location-input":
            event.stop()
            await self._add_list_item(
                input_id="pref-preferred-location-input",
                values=self.preferred_locations,
                panel_id="pref-preferred-locations-panel",
                empty_message="No locations added.",
            )

    def action_back(self) -> None:
        """Return to the dashboard."""

        self.app.pop_screen()
        self.app.refresh(recompose=True)

    def action_save_preferences(self) -> None:
        """Save preferences from the keyboard shortcut."""

        self._save_preferences()

    def _save_preferences(self) -> None:
        answers = self._collect_answers()
        required_errors = self._required_preferences_errors(answers)
        if required_errors:
            self._set_message(format_validation_messages(required_errors), kind="error")
            return

        try:
            preferences = build_user_preferences_from_answers(answers)
        except (ValueError, ValidationError) as exc:
            self._set_message(format_preferences_error(exc), kind="error")
            return

        self.profile_service.save_user_preferences(preferences)
        self._set_message(
            "Saved user preferences. Press b or Esc to return to the dashboard.",
            kind="success",
        )

    def _required_preferences_errors(self, answers: PreferenceWizardAnswers) -> list[str]:
        errors: list[str] = []

        if not answers.full_name.strip():
            errors.append("Full Name is required.")
        if not answers.base_location.strip():
            errors.append("Base Location is required.")
        if not answers.preferred_work_arrangements.strip():
            errors.append("At least one Preferred Work Arrangement is required.")

        return errors

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

    def _set_message(self, message: str, *, kind: str = "info") -> None:
        message_widget = self.query_one("#preference-message", Static)
        message_widget.remove_class("message-error", "message-success")
        if kind == "error":
            message_widget.add_class("message-error")
        elif kind == "success":
            message_widget.add_class("message-success")
        message_widget.update(message)
