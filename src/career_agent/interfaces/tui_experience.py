from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from pydantic import ValidationError
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Select, Static, TextArea

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import (
    CandidateBullet,
    CandidateBulletStatus,
    EmploymentType,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    ExperienceSourceEntry,
    YearMonth,
)

VIEW_SESSION_BUTTON_PREFIX = "view-experience-session-"
EDIT_SESSION_BUTTON_PREFIX = "edit-experience-session-"
TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX = "toggle-source-entry-"
REVIEW_CANDIDATE_BULLET_BUTTON_PREFIX = "review-candidate-bullet-"
REMOVE_CANDIDATE_BULLET_BUTTON_PREFIX = "remove-candidate-bullet-"
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


def format_source_created_at(source_entry: ExperienceSourceEntry) -> str:
    """Return a stable UTC timestamp for source entry display."""

    created_at = source_entry.created_at.astimezone(UTC)
    return created_at.strftime("%Y-%m-%d %H:%M UTC")


def format_source_analysis_status(source_entry: ExperienceSourceEntry) -> str:
    """Return the source entry analysis status label."""

    if source_entry.analyzed_at is None:
        return "Not analyzed"

    return "Analyzed"


def format_source_preview(source_entry: ExperienceSourceEntry, *, max_length: int = 90) -> str:
    """Return a compact one-line preview for a source entry."""

    preview = " ".join(source_entry.content.split())
    if len(preview) <= max_length:
        return preview

    return f"{preview[: max_length - 3]}..."


def format_candidate_bullet_status(status: CandidateBulletStatus) -> str:
    """Format a candidate bullet status for display."""

    return status.value.replace("_", " ").title()


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


class SourceEntryCard(Static):
    """Compact, optionally expanded display for one append-only source entry."""

    def __init__(self, source_entry: ExperienceSourceEntry, *, expanded: bool = False) -> None:
        super().__init__()
        self.source_entry = source_entry
        self.expanded = expanded

    def compose(self) -> ComposeResult:
        with Horizontal(classes="source-entry-summary-row"):
            with Vertical(classes="source-entry-summary"):
                yield Static(
                    (
                        f"{format_source_created_at(self.source_entry)} · "
                        f"{format_source_analysis_status(self.source_entry)}"
                    ),
                    classes="source-entry-heading",
                )
                yield Static(
                    f"Preview: {format_source_preview(self.source_entry)}",
                    classes="status-detail",
                    markup=False,
                )
            yield Button(
                "Hide" if self.expanded else "View",
                id=f"{TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX}{self.source_entry.id}",
                classes="session-open-button source-entry-toggle",
            )
        if self.expanded:
            yield Static(
                self.source_entry.content,
                classes="read-only-panel",
                markup=False,
            )


class CandidateBulletCard(Static):
    """Display and review controls for one candidate bullet."""

    def __init__(self, bullet: CandidateBullet) -> None:
        super().__init__()
        self.bullet = bullet

    def compose(self) -> ComposeResult:
        yield Static(
            format_candidate_bullet_status(self.bullet.status),
            classes=f"status-pill status-{self.bullet.status.value}",
        )
        yield Static(self.bullet.text, classes="read-only-panel", markup=False)
        if self.bullet.review_notes:
            yield Static(
                "\n".join(f"- {note}" for note in self.bullet.review_notes),
                classes="status-detail",
                markup=False,
            )
        with Horizontal(classes="experience-action-row"):
            if self.bullet.status != CandidateBulletStatus.REVIEWED:
                yield Button(
                    "Mark Reviewed",
                    id=f"{REVIEW_CANDIDATE_BULLET_BUTTON_PREFIX}{self.bullet.id}",
                    classes="session-open-button",
                )
            if self.bullet.status != CandidateBulletStatus.REMOVED:
                yield Button(
                    "Remove",
                    id=f"{REMOVE_CANDIDATE_BULLET_BUTTON_PREFIX}{self.bullet.id}",
                    classes="danger-button",
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
            yield Button("Add New Role", id="add-experience", variant="primary")

            with VerticalScroll(id="experience-session-list"):
                if not sessions:
                    yield Static(
                        (
                            "No experience entries or intake sessions found. Choose Add "
                            "New Role to start one."
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
        """Open the New Role form."""

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
        self.expanded_source_entry_id: str | None = None

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

                    yield Static("Source Entries", classes="section-title")
                    if session.source_entries:
                        for source_entry in session.source_entries:
                            yield SourceEntryCard(
                                source_entry,
                                expanded=source_entry.id == self.expanded_source_entry_id,
                            )
                    else:
                        yield Static("No source entries added.", classes="read-only-panel")

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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle source entry expansion."""

        button_id = event.button.id or ""
        if not button_id.startswith(TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX):
            return

        source_entry_id = button_id.removeprefix(TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX)
        self.expanded_source_entry_id = (
            None if self.expanded_source_entry_id == source_entry_id else source_entry_id
        )
        self.refresh(recompose=True)


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
        self.expanded_source_entry_id: str | None = None
        self._form_message: tuple[str, str] | None = None

    def compose(self) -> ComposeResult:
        years = year_options()
        session = self._editing_session()
        is_editing = self.session_id is not None

        yield Header(show_clock=True)
        with Container(id="add-experience-screen"):
            yield Static("Edit Role" if is_editing else "New Role", id="screen-title")
            yield Static(
                (
                    "Save required role details first. After the role is saved, add source "
                    "entries as append-only evidence for future bullet generation."
                ),
                classes="help-text",
            )
            message_text = self._form_message[0] if self._form_message else ""
            message_class = (
                f"form-message message-{self._form_message[1]}"
                if self._form_message
                else "form-message"
            )
            yield Static(message_text, id="experience-form-message", classes=message_class)

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
                                "Editing saved role details after analysis may require generated "
                                "content to be reviewed again."
                            ),
                            classes="message-warning",
                        )

                    yield Static("Role Details", classes="section-title")
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

                    with Horizontal(classes="experience-action-row"):
                        yield Button("Save Role Details", id="save-experience", variant="primary")
                        if session is not None:
                            yield Static("", classes="action-spacer")
                            yield Button(
                                "Delete",
                                id="delete-experience",
                                classes="danger-button",
                            )

                    yield Static("Source Entries", classes="section-title")
                    yield Static(
                        (
                            "Source entries are retained as submitted for traceability. "
                            "To correct or add context later, add another source entry."
                        ),
                        classes="field-tip",
                    )
                    if session is None:
                        yield Static(
                            "Save role details before adding source entries.",
                            classes="read-only-panel",
                        )
                    else:
                        if session.source_entries:
                            for source_entry in session.source_entries:
                                yield SourceEntryCard(
                                    source_entry,
                                    expanded=source_entry.id == self.expanded_source_entry_id,
                                )
                        else:
                            yield Static("No source entries added.", classes="read-only-panel")

                        with Horizontal(classes="experience-action-row"):
                            yield Button(
                                "Analyze Sources",
                                id="analyze-source-entries",
                                variant="primary",
                                disabled=not any(
                                    source_entry.analyzed_at is None
                                    for source_entry in session.source_entries
                                ),
                            )

                        yield Static("Add Source Entry", classes="form-label")
                        yield Static(
                            (
                                "Paste resume bullets, project notes, duty lists, performance "
                                "review excerpts, or paragraphs."
                            ),
                            classes="field-tip",
                        )
                        yield TextArea(id="experience-source-text")

                        with Horizontal(classes="experience-action-row"):
                            yield Button(
                                "Add Source Entry",
                                id="add-source-entry",
                                variant="primary",
                            )

                    yield Static("Candidate Bullets", classes="section-title")
                    if session is None:
                        yield Static(
                            "Save role details and add source entries before generating bullets.",
                            classes="read-only-panel",
                        )
                    elif session.candidate_bullets:
                        for bullet in session.candidate_bullets:
                            yield CandidateBulletCard(bullet)
                    else:
                        yield Static(
                            "No candidate bullets generated yet.",
                            classes="read-only-panel",
                        )

                    yield Static("Assistant", classes="section-title")
                    yield Static(
                        (
                            "LLM analysis placeholder: a future workflow step will analyze "
                            "pending source entries against existing candidate bullets."
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
        """Handle role form buttons."""

        if event.button.id == "save-experience":
            self._save_experience()
        elif event.button.id == "add-source-entry":
            self._add_source_entry()
        elif event.button.id == "analyze-source-entries":
            self._analyze_source_entries()
        elif event.button.id == "delete-experience" and self.session_id is not None:
            self.app.push_screen(
                DeleteExperienceSessionScreen(self.service, self.session_id),
                callback=self._handle_delete_result,
            )
        elif (event.button.id or "").startswith(REVIEW_CANDIDATE_BULLET_BUTTON_PREFIX):
            bullet_id = (event.button.id or "").removeprefix(REVIEW_CANDIDATE_BULLET_BUTTON_PREFIX)
            self._mark_candidate_bullet_reviewed(bullet_id)
        elif (event.button.id or "").startswith(REMOVE_CANDIDATE_BULLET_BUTTON_PREFIX):
            bullet_id = (event.button.id or "").removeprefix(REMOVE_CANDIDATE_BULLET_BUTTON_PREFIX)
            self._remove_candidate_bullet(bullet_id)
        elif (event.button.id or "").startswith(TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX):
            source_entry_id = (event.button.id or "").removeprefix(
                TOGGLE_SOURCE_ENTRY_BUTTON_PREFIX
            )
            self.expanded_source_entry_id = (
                None if self.expanded_source_entry_id == source_entry_id else source_entry_id
            )
            self.refresh(recompose=True)

    def _save_experience(self) -> bool:
        try:
            employer_name = self._required_input("experience-employer-name", "Company / Employer")
            job_title = self._required_input("experience-job-title", "Job Title")
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
        except (ValueError, ValidationError) as exc:
            self._set_message(str(exc), kind="error")
            return False

        self.session_id = session.id
        self._initial_form_state = self._current_form_state()

        message = f"Saved role details for {format_intake_session_title(session)}."
        if self._source_text_area_exists():
            self._set_message(message, kind="success")
        else:
            self._form_message = (message, "success")
            self.refresh(recompose=True)
        return True

    def _handle_unsaved_changes_action(self, action: str | None) -> None:
        if action == "save":
            if self._save_experience() and self._save_unadded_source_entry():
                self.app.pop_screen()
        elif action == "discard":
            self.app.pop_screen()

    def _handle_delete_result(self, deleted: bool | None) -> None:
        if deleted:
            self.app.pop_screen()

    def _add_source_entry(self) -> bool:
        if self.session_id is None:
            self._set_message("Save role details before adding source entries.", kind="error")
            return False

        if self._role_details_have_unsaved_changes():
            self._set_message(
                "Save role details before adding a source entry.",
                kind="error",
            )
            return False

        try:
            source_text = self._source_text()
            session = self.service.add_source_entry(self.session_id, source_text)
        except (ValueError, ValidationError) as exc:
            self._set_message(str(exc), kind="error")
            return False

        self.session_id = session.id
        self._form_message = ("Added source entry.", "success")
        self._initial_form_state = self._current_form_state(source_text=None)
        self.refresh(recompose=True)
        return True

    def _analyze_source_entries(self) -> bool:
        if self.session_id is None:
            self._set_message("Save role details before analyzing source entries.", kind="error")
            return False

        if self._has_unsaved_changes():
            self._set_message(
                "Save role details and add or clear source text before analyzing.",
                kind="error",
            )
            return False

        try:
            session = self.service.analyze_pending_source_entries(self.session_id)
        except (RuntimeError, ValueError, ValidationError) as exc:
            self._set_message(str(exc), kind="error")
            return False

        self._form_message = (
            f"Generated {len(session.candidate_bullets)} candidate bullet(s).",
            "success",
        )
        self._initial_form_state = self._current_form_state(source_text=None)
        self.refresh(recompose=True)
        return True

    def _mark_candidate_bullet_reviewed(self, bullet_id: str) -> bool:
        if self.session_id is None:
            self._set_message("Save role details before reviewing bullets.", kind="error")
            return False

        try:
            self.service.mark_candidate_bullet_reviewed(self.session_id, bullet_id)
        except ValueError as exc:
            self._set_message(str(exc), kind="error")
            return False

        self._form_message = ("Marked candidate bullet reviewed.", "success")
        self.refresh(recompose=True)
        return True

    def _remove_candidate_bullet(self, bullet_id: str) -> bool:
        if self.session_id is None:
            self._set_message("Save role details before removing bullets.", kind="error")
            return False

        try:
            self.service.remove_candidate_bullet(self.session_id, bullet_id)
        except ValueError as exc:
            self._set_message(str(exc), kind="error")
            return False

        self._form_message = ("Removed candidate bullet from active use.", "success")
        self.refresh(recompose=True)
        return True

    def _save_unadded_source_entry(self) -> bool:
        source_text = self._optional_source_text()
        if source_text is None:
            return True

        return self._add_source_entry()

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
            or session.candidate_bullets
        )

    def _has_unsaved_changes(self) -> bool:
        if self._initial_form_state is None:
            return False

        return self._current_form_state() != self._initial_form_state

    def _role_details_have_unsaved_changes(self) -> bool:
        if self._initial_form_state is None:
            return False

        current_state = self._current_form_state()
        source_keys = {"source_text"}
        for key, value in current_state.items():
            if key in source_keys:
                continue
            if value != self._initial_form_state.get(key):
                return True

        return False

    def _current_form_state(
        self,
        *,
        source_text: str | None | object = Ellipsis,
    ) -> dict[str, object]:
        source_value = self._optional_source_text() if source_text is Ellipsis else source_text
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
            "source_text": source_value,
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
        value = self._optional_source_text()
        if not value:
            msg = "Source entry text is required."
            raise ValueError(msg)
        return value

    def _optional_source_text(self) -> str | None:
        if not self._source_text_area_exists():
            return None

        value = self.query_one("#experience-source-text", TextArea).text.strip()
        return value or None

    def _source_text_area_exists(self) -> bool:
        try:
            self.query_one("#experience-source-text", TextArea)
        except NoMatches:
            return False
        return True

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
        self._form_message = (message, kind)
        message_widget = self.query_one("#experience-form-message", Static)
        message_widget.remove_class("message-error", "message-success", "message-warning")
        if kind == "error":
            message_widget.add_class("message-error")
        elif kind == "success":
            message_widget.add_class("message-success")
        elif kind == "warning":
            message_widget.add_class("message-warning")
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
