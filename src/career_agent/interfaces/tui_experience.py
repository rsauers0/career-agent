from __future__ import annotations

from datetime import UTC
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import ExperienceEntry, ExperienceIntakeSession

VIEW_SESSION_BUTTON_PREFIX = "view-experience-session-"


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


def build_experience_entry_sections(entry: ExperienceEntry) -> list[tuple[str, str]]:
    """Return display sections for a draft experience entry."""

    return [
        ("Employer", entry.employer_name),
        ("Job Title", entry.job_title),
        ("Location", format_text_block(entry.location)),
        ("Employment Type", format_text_block(entry.employment_type)),
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
        yield Static(format_intake_session_title(self.session), classes="card-title")
        yield Static(
            format_intake_status(self.session.status),
            classes=f"status-pill intake-status status-{self.session.status.value}",
        )
        yield Static(f"Updated: {format_updated_at(self.session)}", classes="status-detail")
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
        Binding("r", "refresh_sessions", "Refresh"),
    ]

    def __init__(self, service: ExperienceIntakeService) -> None:
        super().__init__()
        self.service = service

    def compose(self) -> ComposeResult:
        sessions = self.service.list_sessions()

        yield Header(show_clock=True)
        with Container(id="experience-screen"):
            yield Static("Experience Intake", id="screen-title")
            yield Static(
                (
                    "Review recoverable experience intake sessions. Draft editing will build "
                    "on this screen next."
                ),
                classes="help-text",
            )

            with VerticalScroll(id="experience-session-list"):
                if not sessions:
                    yield Static(
                        (
                            "No experience intake sessions found. For now, create one with "
                            "`career-agent experience create`."
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
        self.app.refresh(recompose=True)

    def action_refresh_sessions(self) -> None:
        """Refresh the session list from storage."""

        self.refresh(recompose=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Open a read-only detail screen for the selected intake session."""

        button_id = event.button.id or ""
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
                yield Static("Experience Intake", id="screen-title")
                yield Static(
                    f"Experience intake session not found: {self.session_id}",
                    classes="empty-state",
                )
            else:
                yield Static(format_intake_session_title(session), id="screen-title")
                yield Static(
                    f"Status: {format_intake_status(session.status)}",
                    classes="status-detail",
                )
                yield Static(f"Updated: {format_updated_at(session)}", classes="status-detail")

                with VerticalScroll(id="experience-detail"):
                    yield Static("Source Text", classes="section-title")
                    yield Static(
                        format_text_block(session.source_text, empty_message="No source text."),
                        classes="read-only-panel",
                        markup=False,
                    )

                    yield Static("Follow-Up Questions", classes="section-title")
                    if session.follow_up_questions:
                        for index, question in enumerate(session.follow_up_questions, start=1):
                            yield Static(
                                f"{index}. {question.question}",
                                classes="read-only-panel",
                                markup=False,
                            )
                    else:
                        yield Static("No questions generated.", classes="read-only-panel")

                    yield Static("Answers", classes="section-title")
                    if session.user_answers:
                        for answer in session.user_answers:
                            yield Static(
                                f"{answer.question_id}: {answer.answer}",
                                classes="read-only-panel",
                                markup=False,
                            )
                    else:
                        yield Static("No answers captured.", classes="read-only-panel")

                    yield Static("Draft Experience Entry", classes="section-title")
                    if session.draft_experience_entry is None:
                        yield Static("No draft generated.", classes="read-only-panel")
                    else:
                        yield ExperienceEntryDetail(session.draft_experience_entry)
        yield Footer()

    def action_back(self) -> None:
        """Return to the experience session list."""

        self.app.pop_screen()


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
