from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from pydantic import ValidationError
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Select, Static, TextArea

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import (
    EmploymentType,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    YearMonth,
)

VIEW_SESSION_BUTTON_PREFIX = "view-experience-session-"
EDIT_SESSION_BUTTON_PREFIX = "edit-experience-session-"
REQUIRED_MARKER = "[#f05f5f]*[/]"
MONTH_OPTIONS = [
    ("January", "1"),
    ("February", "2"),
    ("March", "3"),
    ("April", "4"),
    ("May", "5"),
    ("June", "6"),
    ("July", "7"),
    ("August", "8"),
    ("September", "9"),
    ("October", "10"),
    ("November", "11"),
    ("December", "12"),
]
EMPLOYMENT_TYPE_OPTIONS = [(value.value.title(), value.value) for value in EmploymentType]


def required_label(label: str) -> str:
    """Return a form label with a red required marker."""

    return f"{label} {REQUIRED_MARKER}"


def year_options() -> list[tuple[str, str]]:
    """Return practical year options for role date dropdowns."""

    current_year = datetime.now(UTC).year
    return [(str(year), str(year)) for year in range(current_year + 1, 1969, -1)]


def format_intake_status(status: object) -> str:
    """Format an intake workflow status for display."""

    return str(status).replace("_", " ").title()


def format_intake_session_title(session: ExperienceIntakeSession) -> str:
    """Return a compact title for an intake session."""

    if session.employer_name and session.job_title:
        return f"{session.job_title} at {session.employer_name}"

    if session.employer_name:
        return session.employer_name

    if session.job_title:
        return session.job_title

    return "Untitled Experience Intake"


def format_updated_at(session: ExperienceIntakeSession) -> str:
    """Return a stable UTC timestamp for display."""

    updated_at = session.updated_at.astimezone(UTC)
    return updated_at.strftime("%Y-%m-%d %H:%M UTC")


def format_year_month(value: YearMonth | None) -> str:
    """Format a YearMonth value for display."""

    if value is None:
        return "-"

    return f"{value.month:02d}/{value.year}"


def format_text_block(value: str | None, *, empty_message: str = "-") -> str:
    """Format optional multiline text for a read-only TUI panel."""

    if value is None:
        return empty_message

    normalized = value.strip()
    return normalized or empty_message


def format_string_list(values: list[str], *, empty_message: str = "-") -> str:
    """Format a list of strings for read-only display."""

    if not values:
        return empty_message

    return "\n".join(f"- {value}" for value in values)


def build_question_answer_blocks(session: ExperienceIntakeSession) -> list[str]:
    """Return display blocks pairing each generated question with its answer."""

    answer_by_question_id = {answer.question_id: answer.answer for answer in session.user_answers}
    blocks: list[str] = []
    for index, question in enumerate(session.follow_up_questions, start=1):
        answer = answer_by_question_id.get(question.id, "Not answered yet.")
        blocks.append(f"Question {index}: {question.question}\n\nAnswer: {answer}")

    return blocks


def sort_experience_sessions(
    sessions: list[ExperienceIntakeSession],
) -> list[ExperienceIntakeSession]:
    """Sort sessions by current role, role dates, then recent updates."""

    return sorted(sessions, key=_experience_session_sort_key, reverse=True)


def _experience_session_sort_key(
    session: ExperienceIntakeSession,
) -> tuple[int, int, tuple[int, int], datetime]:
    date_value = session.end_date or session.start_date
    return (
        1 if session.is_current_role else 0,
        1 if date_value is not None else 0,
        date_value.sort_key() if date_value is not None else (0, 0),
        session.updated_at,
    )


def build_experience_entry_sections(entry: ExperienceEntry) -> list[tuple[str, str]]:
    """Return display sections for a draft experience entry."""

    return [
        ("Employer", entry.employer_name),
        ("Job Title", entry.job_title),
        ("Location", format_text_block(entry.location)),
        ("Employment Type", format_text_block(entry.employment_type)),
        ("Start Date", format_year_month(entry.start_date)),
        ("End Date", "Present" if entry.is_current_role else format_year_month(entry.end_date)),
        ("Role Summary", format_text_block(entry.role_summary)),
        ("Responsibilities", format_string_list(entry.responsibilities)),
        ("Accomplishments", format_string_list(entry.accomplishments)),
        ("Metrics", format_string_list(entry.metrics)),
        ("Systems and Tools", format_string_list(entry.systems_and_tools)),
        ("Skills Demonstrated", format_string_list(entry.skills_demonstrated)),
        ("Domains", format_string_list(entry.domains)),
        ("Team Context", format_text_block(entry.team_context)),
        ("Scope Notes", format_text_block(entry.scope_notes)),
        ("Keywords", format_string_list(entry.keywords)),
    ]


def is_experience_session_editable(session: ExperienceIntakeSession) -> bool:
    """Return whether an intake session can still be edited in the TUI."""

    return session.status not in {
        ExperienceIntakeStatus.LOCKED,
        ExperienceIntakeStatus.ACCEPTED,
    }


class ExperienceSessionCard(Static):
    """Read-only card for one experience intake session."""

    def __init__(self, session: ExperienceIntakeSession) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        end_date = (
            "Present" if self.session.is_current_role else format_year_month(self.session.end_date)
        )
        yield Static(format_intake_session_title(self.session), classes="card-title")
        yield Static(
            format_intake_status(self.session.status),
            classes=f"status-pill intake-status status-{self.session.status.value}",
        )
        yield Static(f"Updated: {format_updated_at(self.session)}", classes="status-detail")
        yield Static(
            f"{format_year_month(self.session.start_date)} - {end_date}",
            classes="status-detail",
        )
        yield Static(
            (
                f"Questions: {len(self.session.follow_up_questions)} | "
                f"Answers: {len(self.session.user_answers)} | "
                f"Draft: {'yes' if self.session.draft_experience_entry else 'no'}"
            ),
            classes="status-detail",
        )
        with Horizontal(classes="experience-action-row"):
            yield Button(
                "View",
                id=f"{VIEW_SESSION_BUTTON_PREFIX}{self.session.id}",
                classes="session-open-button",
            )
            if is_experience_session_editable(self.session):
                yield Button(
                    "Edit",
                    id=f"{EDIT_SESSION_BUTTON_PREFIX}{self.session.id}",
                    classes="session-open-button",
                )


class ExperienceIntakeScreen(Screen[None]):
    """Experience intake session list screen."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
        Binding("a", "add_experience", "Add"),
        Binding("r", "refresh_sessions", "Refresh"),
    ]

    def __init__(self, service: ExperienceIntakeService) -> None:
        super().__init__()
        self.service = service

    def compose(self) -> ComposeResult:
        sessions = sort_experience_sessions(self.service.list_sessions())

        yield Header(show_clock=True)
        with Container(id="experience-screen"):
            yield Static("Experience", id="screen-title")
            yield Static(
                (
                    "Review role entries and in-progress intake sessions. Draft editing will "
                    "build on this screen next."
                ),
                classes="help-text",
            )
            yield Button("Add Experience", id="add-experience", variant="primary")

            with VerticalScroll(id="experience-session-list"):
                if not sessions:
                    yield Static(
                        (
                            "No experience entries or intake sessions found. Choose Add "
                            "Experience to start one."
                        ),
                        classes="empty-state",
                    )
                else:
                    for session in sessions:
                        yield ExperienceSessionCard(session)
        yield Footer()

    def action_back(self) -> None:
        """Return to the previous screen."""

        self.app.pop_screen()

    def on_screen_resume(self) -> None:
        """Refresh sessions when returning from child screens."""

        self.refresh(recompose=True)

    def action_refresh_sessions(self) -> None:
        """Refresh the session list from storage."""

        self.refresh(recompose=True)

    def action_add_experience(self) -> None:
        """Open the Add Experience form."""

        self.app.push_screen(AddExperienceScreen(self.service))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Open the selected intake session workflow screen."""

        button_id = event.button.id or ""
        if button_id == "add-experience":
            self.action_add_experience()
            return

        if button_id.startswith(EDIT_SESSION_BUTTON_PREFIX):
            session_id = button_id.removeprefix(EDIT_SESSION_BUTTON_PREFIX)
            self.app.push_screen(AddExperienceScreen(self.service, session_id=session_id))
            return

        if button_id.startswith(VIEW_SESSION_BUTTON_PREFIX):
            session_id = button_id.removeprefix(VIEW_SESSION_BUTTON_PREFIX)
            self.app.push_screen(ExperienceSessionDetailScreen(self.service, session_id))


class ExperienceSessionDetailScreen(Screen[None]):
    """Read-only detail screen for one experience intake session."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, service: ExperienceIntakeService, session_id: str) -> None:
        super().__init__()
        self.service = service
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        session = self.service.get_session(self.session_id)

        yield Header(show_clock=True)
        with Container(id="experience-detail-screen"):
            if session is None:
                yield Static("Experience", id="screen-title")
                yield Static(
                    f"Experience intake session not found: {self.session_id}",
                    classes="empty-state",
                )
            else:
                end_date = (
                    "Present" if session.is_current_role else format_year_month(session.end_date)
                )
                yield Static(format_intake_session_title(session), id="screen-title")
                yield Static(
                    f"Status: {format_intake_status(session.status)}",
                    classes="status-detail",
                )
                yield Static(f"Updated: {format_updated_at(session)}", classes="status-detail")

                with VerticalScroll(id="experience-detail"):
                    yield Static("Role Details", classes="section-title")
                    yield Static(
                        (
                            f"Employer: {session.employer_name or '-'}\n"
                            f"Job Title: {session.job_title or '-'}\n"
                            f"Location: {session.location or '-'}\n"
                            f"Employment Type: {session.employment_type or '-'}\n"
                            f"Dates: {format_year_month(session.start_date)} - {end_date}"
                        ),
                        classes="read-only-panel",
                    )

                    yield Static("Source Text", classes="section-title")
                    yield Static(
                        format_text_block(session.source_text, empty_message="No source text."),
                        classes="read-only-panel",
                        markup=False,
                    )

                    yield Static("Questions And Answers", classes="section-title")
                    if session.follow_up_questions:
                        for question_answer_block in build_question_answer_blocks(session):
                            yield Static(
                                question_answer_block,
                                classes="read-only-panel",
                                markup=False,
                            )
                    else:
                        yield Static("No questions generated.", classes="read-only-panel")

                    yield Static("Draft Experience Entry", classes="section-title")
                    if session.draft_experience_entry is None:
                        yield Static("No draft generated.", classes="read-only-panel")
                    else:
                        yield ExperienceEntryDetail(session.draft_experience_entry)
        yield Footer()

    def action_back(self) -> None:
        """Return to the experience session list."""

        self.app.pop_screen()


class DeleteExperienceSessionScreen(Screen[None]):
    """Confirmation screen for deleting an unlocked intake session."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Cancel"),
        ("escape", "back", "Cancel"),
    ]

    def __init__(self, service: ExperienceIntakeService, session_id: str) -> None:
        super().__init__()
        self.service = service
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        session = self.service.get_session(self.session_id)

        yield Header(show_clock=True)
        with Container(id="delete-experience-screen"):
            yield Static("Delete Experience", id="screen-title")
            yield Static("", id="delete-experience-message", classes="form-message")

            if session is None:
                yield Static(
                    f"Experience intake session not found: {self.session_id}",
                    classes="empty-state",
                )
            elif not is_experience_session_editable(session):
                yield Static(
                    "This experience entry is locked and cannot be deleted.",
                    classes="empty-state",
                )
            else:
                yield Static(
                    (
                        f"Delete {format_intake_session_title(session)}?\n\n"
                        "This removes the intake session from the active experience list. "
                        "A snapshot is kept before deletion."
                    ),
                    classes="read-only-panel",
                    markup=False,
                )
                with Horizontal(classes="experience-action-row"):
                    yield Button("Delete", id="confirm-delete-experience", classes="danger-button")
                    yield Button("Cancel", id="cancel-delete-experience")
        yield Footer()

    def action_back(self) -> None:
        """Cancel deletion and return to the experience list."""

        self.dismiss(False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle delete confirmation actions."""

        if event.button.id == "cancel-delete-experience":
            self.action_back()
            return

        if event.button.id != "confirm-delete-experience":
            return

        try:
            self.service.delete_session(self.session_id)
        except ValueError as exc:
            message_widget = self.query_one("#delete-experience-message", Static)
            message_widget.remove_class("message-success")
            message_widget.add_class("message-error")
            message_widget.update(str(exc))
            return

        self.dismiss(True)


class UnsavedExperienceChangesScreen(Screen[None]):
    """Prompt before leaving an experience form with unsaved changes."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="unsaved-experience-screen"):
            yield Static("Unsaved Changes", id="screen-title")
            yield Static(
                (
                    "Do you want to save this experience entry before leaving?\n\n"
                    "If you discard, the data entered since the last save will not be retained."
                ),
                classes="read-only-panel",
                markup=False,
            )
            with Horizontal(classes="experience-action-row"):
                yield Button("Save and Leave", id="save-unsaved-experience", variant="primary")
                yield Button("Discard Changes", id="discard-unsaved-experience")
                yield Button("Cancel", id="cancel-unsaved-experience")
        yield Footer()

    def action_cancel(self) -> None:
        """Stay on the experience form."""

        self.dismiss("cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Return the selected unsaved-change action."""

        if event.button.id == "save-unsaved-experience":
            self.dismiss("save")
        elif event.button.id == "discard-unsaved-experience":
            self.dismiss("discard")
        elif event.button.id == "cancel-unsaved-experience":
            self.action_cancel()


class AddExperienceScreen(Screen[None]):
    """Form for creating or editing a role-specific experience intake session."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(
        self,
        service: ExperienceIntakeService,
        *,
        session_id: str | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.session_id = session_id
        self._initial_form_state: dict[str, object] | None = None

    def compose(self) -> ComposeResult:
        years = year_options()
        session = self._editing_session()
        is_editing = self.session_id is not None

        yield Header(show_clock=True)
        with Container(id="add-experience-screen"):
            yield Static("Edit Experience" if is_editing else "Add Experience", id="screen-title")
            yield Static(
                (
                    "Enter known role facts and paste bullets or notes. Analysis will later "
                    "generate structured follow-up questions from this saved intake session."
                ),
                classes="help-text",
            )
            yield Static("", id="experience-form-message", classes="form-message")

            if is_editing and session is None:
                yield Static(
                    f"Experience intake session not found: {self.session_id}",
                    classes="empty-state",
                )

            elif session is not None and not is_experience_session_editable(session):
                yield Static(
                    "This experience entry is locked and cannot be edited from this screen.",
                    classes="empty-state",
                )

            else:
                with VerticalScroll(id="add-experience-form"):
                    yield Static(
                        f"{REQUIRED_MARKER} = required field",
                        classes="required-legend",
                    )

                    if session is not None and self._has_generated_outputs(session):
                        yield Static(
                            (
                                "Editing saved role facts or bullets may make existing questions "
                                "or draft content stale. Re-run analysis after saving changes."
                            ),
                            classes="message-warning",
                        )

                    yield Static(
                        required_label("Company / Employer"),
                        classes="form-label required-label",
                    )
                    yield Input(
                        value=session.employer_name if session else "",
                        placeholder="Acme Analytics",
                        id="experience-employer-name",
                    )

                    yield Static(required_label("Job Title"), classes="form-label required-label")
                    yield Input(
                        value=session.job_title if session else "",
                        placeholder="Senior Data Engineer",
                        id="experience-job-title",
                    )

                    yield Static("Location", classes="form-label")
                    yield Input(
                        value=session.location if session and session.location else "",
                        placeholder="Chicago, IL",
                        id="experience-location",
                    )

                    yield Static("Employment Type", classes="form-label")
                    employment_type_value = (
                        session.employment_type
                        if session is not None and session.employment_type is not None
                        else Select.NULL
                    )
                    yield Select(
                        EMPLOYMENT_TYPE_OPTIONS,
                        prompt="Select employment type",
                        allow_blank=True,
                        value=employment_type_value,
                        id="experience-employment-type",
                    )

                    yield Static(required_label("Start Date"), classes="form-label required-label")
                    start_date = session.start_date if session else None
                    with Horizontal(classes="experience-date-row"):
                        yield Select(
                            MONTH_OPTIONS,
                            prompt="Month",
                            allow_blank=True,
                            value=self._date_part_value(start_date, "month"),
                            id="experience-start-month",
                        )
                        yield Select(
                            years,
                            prompt="Year",
                            allow_blank=True,
                            value=self._date_part_value(start_date, "year"),
                            id="experience-start-year",
                        )

                    yield Static("End Date", classes="form-label")
                    end_date = session.end_date if session else None
                    with Horizontal(classes="experience-date-row"):
                        yield Select(
                            MONTH_OPTIONS,
                            prompt="Month",
                            allow_blank=True,
                            value=self._date_part_value(end_date, "month"),
                            id="experience-end-month",
                        )
                        yield Select(
                            years,
                            prompt="Year",
                            allow_blank=True,
                            value=self._date_part_value(end_date, "year"),
                            id="experience-end-year",
                        )
                        yield Checkbox(
                            "Current / Present",
                            value=session.is_current_role if session else False,
                            id="experience-current-role",
                        )

                    yield Static(
                        required_label("Bullets / Notes"),
                        classes="form-label required-label",
                    )
                    yield TextArea(id="experience-source-text")

                    with Horizontal(classes="experience-action-row"):
                        yield Button("Save", id="save-experience", variant="primary")
                        yield Button("Analyze with LLM", id="analyze-placeholder", disabled=True)
                        if session is not None:
                            yield Static("", classes="action-spacer")
                            yield Button(
                                "Delete",
                                id="delete-experience",
                                classes="danger-button",
                            )

                    yield Static("Assistant", classes="section-title")
                    yield Static(
                        (
                            "LLM analysis placeholder: the next workflow step will generate "
                            "follow-up questions from the saved role facts and source bullets."
                        ),
                        classes="read-only-panel",
                    )
        yield Footer()

    def on_mount(self) -> None:
        """Populate widgets that do not support value assignment at compose time."""

        session = self._editing_session()
        if session is None or not is_experience_session_editable(session):
            if self.session_id is None:
                self._initial_form_state = self._current_form_state()
            return

        self.query_one("#experience-source-text", TextArea).text = session.source_text or ""
        self._initial_form_state = self._current_form_state()

    def action_back(self) -> None:
        """Return to the experience list, prompting if the form has unsaved changes."""

        if self._has_unsaved_changes():
            self.app.push_screen(
                UnsavedExperienceChangesScreen(),
                callback=self._handle_unsaved_changes_action,
            )
            return
        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Add Experience form buttons."""

        if event.button.id == "save-experience":
            self._save_experience()
        elif event.button.id == "delete-experience" and self.session_id is not None:
            self.app.push_screen(
                DeleteExperienceSessionScreen(self.service, self.session_id),
                callback=self._handle_delete_result,
            )

    def _save_experience(self) -> bool:
        try:
            employer_name = self._required_input("experience-employer-name", "Company / Employer")
            job_title = self._required_input("experience-job-title", "Job Title")
            source_text = self._source_text()
            start_date = self._required_year_month(
                "experience-start-month",
                "experience-start-year",
                "Start Date",
            )
            is_current_role = self.query_one("#experience-current-role", Checkbox).value
            end_date = None
            if not is_current_role:
                end_date = self._required_year_month(
                    "experience-end-month",
                    "experience-end-year",
                    "End Date",
                )

            session_id = self._target_session_id()
            session = self.service.capture_role_details(
                session_id,
                employer_name=employer_name,
                job_title=job_title,
                location=self._optional_input("experience-location"),
                employment_type=self._select_value("experience-employment-type"),
                start_date=start_date,
                end_date=end_date,
                is_current_role=is_current_role,
            )
            session = self.service.capture_source_text(session.id, source_text)
        except (ValueError, ValidationError) as exc:
            self._set_message(str(exc), kind="error")
            return False

        self.session_id = session.id
        self._initial_form_state = self._current_form_state()

        self._set_message(
            (
                f"Saved experience intake session {session.id}. "
                "LLM analysis will generate follow-up questions in the next workflow slice."
            ),
            kind="success",
        )
        return True

    def _handle_unsaved_changes_action(self, action: str | None) -> None:
        if action == "save":
            if self._save_experience():
                self.app.pop_screen()
        elif action == "discard":
            self.app.pop_screen()

    def _handle_delete_result(self, deleted: bool | None) -> None:
        if deleted:
            self.app.pop_screen()

    def _target_session_id(self) -> str:
        if self.session_id is None:
            return self.service.create_session().id

        session = self.service.get_session(self.session_id)
        if session is None:
            msg = f"Experience intake session not found: {self.session_id}."
            raise ValueError(msg)

        if not is_experience_session_editable(session):
            msg = "Locked experience intake entries cannot be edited."
            raise ValueError(msg)

        return session.id

    def _editing_session(self) -> ExperienceIntakeSession | None:
        if self.session_id is None:
            return None

        return self.service.get_session(self.session_id)

    def _has_generated_outputs(self, session: ExperienceIntakeSession) -> bool:
        return bool(
            session.follow_up_questions
            or session.user_answers
            or session.draft_experience_entry is not None
        )

    def _has_unsaved_changes(self) -> bool:
        if self._initial_form_state is None:
            return False

        return self._current_form_state() != self._initial_form_state

    def _current_form_state(self) -> dict[str, object]:
        return {
            "employer_name": self._optional_input("experience-employer-name"),
            "job_title": self._optional_input("experience-job-title"),
            "location": self._optional_input("experience-location"),
            "employment_type": self._select_value("experience-employment-type"),
            "start_month": self._select_value("experience-start-month"),
            "start_year": self._select_value("experience-start-year"),
            "end_month": self._select_value("experience-end-month"),
            "end_year": self._select_value("experience-end-year"),
            "is_current_role": self.query_one("#experience-current-role", Checkbox).value,
            "source_text": self.query_one("#experience-source-text", TextArea).text.strip(),
        }

    def _required_input(self, widget_id: str, label: str) -> str:
        value = self._optional_input(widget_id)
        if value is None:
            msg = f"{label} is required."
            raise ValueError(msg)
        return value

    def _optional_input(self, widget_id: str) -> str | None:
        value = self.query_one(f"#{widget_id}", Input).value.strip()
        return value or None

    def _source_text(self) -> str:
        value = self.query_one("#experience-source-text", TextArea).text.strip()
        if not value:
            msg = "Bullets / Notes are required."
            raise ValueError(msg)
        return value

    def _select_value(self, widget_id: str) -> str | None:
        value = self.query_one(f"#{widget_id}", Select).value
        if value is Select.NULL or value is Select.BLANK:
            return None
        return str(value)

    def _date_part_value(self, value: YearMonth | None, part: str) -> str | object:
        if value is None:
            return Select.NULL

        if part == "month":
            return str(value.month)

        return str(value.year)

    def _required_year_month(
        self,
        month_widget_id: str,
        year_widget_id: str,
        label: str,
    ) -> YearMonth:
        month_value = self._select_value(month_widget_id)
        year_value = self._select_value(year_widget_id)
        if month_value is None or year_value is None:
            msg = f"{label} month and year are required."
            raise ValueError(msg)
        return YearMonth(year=int(year_value), month=int(month_value))

    def _set_message(self, message: str, *, kind: str = "info") -> None:
        message_widget = self.query_one("#experience-form-message", Static)
        message_widget.remove_class("message-error", "message-success")
        if kind == "error":
            message_widget.add_class("message-error")
        elif kind == "success":
            message_widget.add_class("message-success")
        message_widget.update(message)


class ExperienceEntryDetail(Static):
    """Read-only display for a draft experience entry."""

    def __init__(self, entry: ExperienceEntry) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        for label, value in build_experience_entry_sections(self.entry):
            with Vertical(classes="experience-entry-section"):
                with Horizontal(classes="preference-row"):
                    yield Static(label, classes="preference-label")
                    yield Static(value, classes="preference-value", markup=False)
