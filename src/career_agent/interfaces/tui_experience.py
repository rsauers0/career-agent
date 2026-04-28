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
    YearMonth,
)

VIEW_SESSION_BUTTON_PREFIX = "view-experience-session-"
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
        yield Button(
            "Open",
            id=f"{VIEW_SESSION_BUTTON_PREFIX}{self.session.id}",
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
        """Open a read-only detail screen for the selected intake session."""

        button_id = event.button.id or ""
        if button_id == "add-experience":
            self.action_add_experience()
            return

        if not button_id.startswith(VIEW_SESSION_BUTTON_PREFIX):
            return

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


class AddExperienceScreen(Screen[None]):
    """Form for starting a role-specific experience intake session."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, service: ExperienceIntakeService) -> None:
        super().__init__()
        self.service = service

    def compose(self) -> ComposeResult:
        years = year_options()

        yield Header(show_clock=True)
        with Container(id="add-experience-screen"):
            yield Static("Add Experience", id="screen-title")
            yield Static(
                (
                    "Enter known role facts and paste bullets or notes. Analysis will later "
                    "generate structured follow-up questions from this saved intake session."
                ),
                classes="help-text",
            )
            yield Static("", id="experience-form-message", classes="form-message")

            with VerticalScroll(id="add-experience-form"):
                yield Static(
                    f"{REQUIRED_MARKER} = required field",
                    classes="required-legend",
                )

                yield Static(
                    required_label("Company / Employer"),
                    classes="form-label required-label",
                )
                yield Input(placeholder="Acme Analytics", id="experience-employer-name")

                yield Static(required_label("Job Title"), classes="form-label required-label")
                yield Input(placeholder="Senior Data Engineer", id="experience-job-title")

                yield Static("Location", classes="form-label")
                yield Input(placeholder="Chicago, IL", id="experience-location")

                yield Static("Employment Type", classes="form-label")
                yield Select(
                    EMPLOYMENT_TYPE_OPTIONS,
                    prompt="Select employment type",
                    allow_blank=True,
                    id="experience-employment-type",
                )

                yield Static(required_label("Start Date"), classes="form-label required-label")
                with Horizontal(classes="experience-date-row"):
                    yield Select(
                        MONTH_OPTIONS,
                        prompt="Month",
                        allow_blank=True,
                        id="experience-start-month",
                    )
                    yield Select(
                        years,
                        prompt="Year",
                        allow_blank=True,
                        id="experience-start-year",
                    )

                yield Static("End Date", classes="form-label")
                with Horizontal(classes="experience-date-row"):
                    yield Select(
                        MONTH_OPTIONS,
                        prompt="Month",
                        allow_blank=True,
                        id="experience-end-month",
                    )
                    yield Select(
                        years,
                        prompt="Year",
                        allow_blank=True,
                        id="experience-end-year",
                    )
                    yield Checkbox("Current / Present", id="experience-current-role")

                yield Static(
                    required_label("Bullets / Notes"),
                    classes="form-label required-label",
                )
                yield TextArea(id="experience-source-text")

                with Horizontal(classes="experience-action-row"):
                    yield Button("Save", id="save-experience", variant="primary")
                    yield Button("Analyze with LLM", id="analyze-placeholder", disabled=True)

                yield Static("Assistant", classes="section-title")
                yield Static(
                    (
                        "LLM analysis placeholder: the next workflow step will generate "
                        "follow-up questions from the saved role facts and source bullets."
                    ),
                    classes="read-only-panel",
                )
        yield Footer()

    def action_back(self) -> None:
        """Return to the experience list."""

        self.app.pop_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Add Experience form buttons."""

        if event.button.id == "save-experience":
            self._save_experience()

    def _save_experience(self) -> None:
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

            session = self.service.create_session()
            session = self.service.capture_role_details(
                session.id,
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
            return

        self._set_message(
            (
                f"Saved experience intake session {session.id}. "
                "LLM analysis will generate follow-up questions in the next workflow slice."
            ),
            kind="success",
        )

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
