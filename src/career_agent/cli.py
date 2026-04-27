from __future__ import annotations

from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.application.preferences_builder import (
    PreferenceWizardAnswers,
    build_user_preferences_from_answers,
    parse_commute_distance_unit,
    parse_optional_int,
    parse_time_zone,
    parse_work_arrangements,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, format_status_field_names
from career_agent.config import get_settings
from career_agent.domain.models import (
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
)
from career_agent.infrastructure.llm import OpenAICompatibleExperienceIntakeAssistant
from career_agent.infrastructure.repositories import (
    FileExperienceIntakeRepository,
    FileProfileRepository,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: a local-first CLI for career profiles, job search, and tailored documents.",
)
preferences_app = typer.Typer(help="Manage user preferences.")
profile_app = typer.Typer(help="Manage the career profile.")
experience_app = typer.Typer(help="Manage experience intake sessions.")
console = Console()


@app.callback()
def cli() -> None:
    """CLI entrypoint for grouped commands."""


@app.command()
def doctor() -> None:
    """Confirm the CLI scaffold is wired correctly."""
    console.print(
        "[bold green]Career Agent[/bold green] is installed and ready for step-by-step development."
    )


@app.command()
def tui() -> None:
    """Launch the local Textual interface."""

    from career_agent.interfaces.tui import run_tui

    run_tui()


@profile_app.callback()
def profile_cli() -> None:
    """Commands for working with the career profile."""


@preferences_app.callback()
def preferences_cli() -> None:
    """Commands for working with user preferences."""


@experience_app.callback()
def experience_cli() -> None:
    """Commands for working with experience intake sessions."""


def _build_profile_service() -> ProfileService:
    settings = get_settings()
    return ProfileService(FileProfileRepository(settings.data_dir))


def _build_experience_intake_service(
    *,
    include_assistant: bool = False,
) -> ExperienceIntakeService:
    settings = get_settings()
    repository = FileExperienceIntakeRepository(settings.data_dir)
    profile_repository = FileProfileRepository(settings.data_dir)
    assistant = (
        OpenAICompatibleExperienceIntakeAssistant.from_settings(settings)
        if include_assistant
        else None
    )
    return ExperienceIntakeService(repository, assistant, profile_repository)


def _prompt_required_text(prompt_text: str, default: str = "") -> str:
    while True:
        value = typer.prompt(prompt_text, default=default).strip()
        if value:
            return value
        console.print(f"[red]{prompt_text} cannot be blank.[/red]")


def _prompt_validated_text(
    prompt_text: str,
    default: str,
    validator,
    hint: str | None = None,
) -> str:
    while True:
        value = typer.prompt(prompt_text, default=default)
        try:
            validator(value)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            if hint:
                console.print(hint)
            continue
        return value


def _render_user_preferences(preferences) -> None:
    preference_table = Table(title="User Preferences")
    preference_table.add_column("Field")
    preference_table.add_column("Value")
    preference_table.add_row("Full Name", preferences.full_name)
    preference_table.add_row("Base Location", preferences.base_location)
    preference_table.add_row("Time Zone", preferences.time_zone or "-")
    preference_table.add_row(
        "Target Roles",
        ", ".join(preferences.target_job_titles) or "-",
    )
    preference_table.add_row(
        "Preferred Locations",
        ", ".join(preferences.preferred_locations) or "-",
    )
    preference_table.add_row(
        "Work Arrangements",
        ", ".join(arrangement.value for arrangement in preferences.preferred_work_arrangements)
        or "-",
    )
    console.print(preference_table)


def _render_component_status(status: ComponentStatus) -> None:
    status_table = Table(title="Component Status")
    status_table.add_column("Field")
    status_table.add_column("Value")
    status_table.add_row("Component", status.component)
    status_table.add_row("State", status.state.value)
    status_table.add_row(
        "Missing Required",
        ", ".join(format_status_field_names(status.missing_required)) or "-",
    )
    status_table.add_row(
        "Missing Recommended",
        ", ".join(format_status_field_names(status.missing_recommended)) or "-",
    )
    console.print(status_table)


def _render_intake_session(session: ExperienceIntakeSession) -> None:
    session_table = Table(title="Experience Intake Session")
    session_table.add_column("Field")
    session_table.add_column("Value")
    session_table.add_row("Session ID", session.id)
    session_table.add_row("Status", session.status.value)
    session_table.add_row("Employer", session.employer_name or "-")
    session_table.add_row("Job Title", session.job_title or "-")
    session_table.add_row("Source Text", session.source_text or "-")
    session_table.add_row("Follow-Up Questions", str(len(session.follow_up_questions)))
    session_table.add_row("User Answers", str(len(session.user_answers)))
    session_table.add_row(
        "Draft Entry",
        "yes" if session.draft_experience_entry is not None else "no",
    )
    session_table.add_row("Created At", session.created_at.isoformat())
    session_table.add_row("Updated At", session.updated_at.isoformat())
    console.print(session_table)

    if session.follow_up_questions:
        _render_intake_questions(session)
    if session.user_answers:
        _render_intake_answers(session)
    if session.draft_experience_entry is not None:
        _render_experience_entry(session.draft_experience_entry)


def _render_intake_questions(session: ExperienceIntakeSession) -> None:
    questions_table = Table(title="Follow-Up Questions")
    questions_table.add_column("#", justify="right")
    questions_table.add_column("Question")
    questions_table.add_column("Rationale")

    for index, question in enumerate(session.follow_up_questions, start=1):
        questions_table.add_row(
            str(index),
            question.question,
            question.rationale or "-",
        )

    console.print(questions_table)


def _render_intake_answers(session: ExperienceIntakeSession) -> None:
    question_text_by_id = {
        question.id: question.question for question in session.follow_up_questions
    }
    answers_table = Table(title="Captured Answers")
    answers_table.add_column("#", justify="right")
    answers_table.add_column("Question")
    answers_table.add_column("Answer")

    for index, answer in enumerate(session.user_answers, start=1):
        answers_table.add_row(
            str(index),
            question_text_by_id.get(answer.question_id, answer.question_id),
            answer.answer,
        )

    console.print(answers_table)


def _render_experience_entry(entry: ExperienceEntry) -> None:
    entry_table = Table(title="Draft Experience Entry")
    entry_table.add_column("Field")
    entry_table.add_column("Value")
    entry_table.add_row("Entry ID", entry.id)
    entry_table.add_row("Employer", entry.employer_name)
    entry_table.add_row("Job Title", entry.job_title)
    entry_table.add_row("Role Summary", entry.role_summary or "-")
    entry_table.add_row("Responsibilities", "\n".join(entry.responsibilities) or "-")
    entry_table.add_row("Accomplishments", "\n".join(entry.accomplishments) or "-")
    entry_table.add_row("Metrics", "\n".join(entry.metrics) or "-")
    entry_table.add_row("Systems & Tools", ", ".join(entry.systems_and_tools) or "-")
    entry_table.add_row("Skills", ", ".join(entry.skills_demonstrated) or "-")
    entry_table.add_row("Domains", ", ".join(entry.domains) or "-")
    entry_table.add_row("Team Context", entry.team_context or "-")
    entry_table.add_row("Scope Notes", entry.scope_notes or "-")
    console.print(entry_table)


def _handle_experience_error(error: Exception) -> None:
    console.print(f"[red]{error}[/red]")
    raise typer.Exit(1) from error


@preferences_app.command("show")
def preferences_show() -> None:
    """Display the stored user preferences."""

    settings = get_settings()
    service = _build_profile_service()
    preferences = service.get_user_preferences()

    if preferences is None:
        console.print(
            f"No user preferences found. Expected files under [bold]{settings.data_dir}[/bold]."
        )
        return

    _render_user_preferences(preferences)


@preferences_app.command("status")
def preferences_status() -> None:
    """Display workflow completeness status for user preferences."""

    service = _build_profile_service()
    status = service.get_user_preferences_status()

    _render_component_status(status)


@preferences_app.command("wizard")
def preferences_wizard() -> None:
    """Create or update user preferences through a guided prompt flow."""

    service = _build_profile_service()
    existing = service.get_user_preferences()

    answers = PreferenceWizardAnswers(
        full_name=_prompt_required_text(
            "Full name",
            default=existing.full_name if existing else "",
        ),
        base_location=_prompt_required_text(
            "Base location (City, State ZIP)",
            default=existing.base_location if existing else "",
        ),
        time_zone=_prompt_validated_text(
            "Time zone (IANA, optional)",
            default=existing.time_zone or "" if existing else "",
            validator=parse_time_zone,
            hint="Use values like America/Chicago or leave blank.",
        ),
        target_job_titles=typer.prompt(
            "Target job titles (comma-separated)",
            default=", ".join(existing.target_job_titles) if existing else "",
        ),
        preferred_locations=typer.prompt(
            "Preferred locations (comma-separated)",
            default=", ".join(existing.preferred_locations) if existing else "",
        ),
        preferred_work_arrangements=_prompt_validated_text(
            "Preferred work arrangements (comma-separated: remote, hybrid, onsite)",
            default=(
                ", ".join(arrangement.value for arrangement in existing.preferred_work_arrangements)
                if existing
                else ""
            ),
            validator=parse_work_arrangements,
            hint="Allowed values are remote, hybrid, and onsite.",
        ),
        desired_salary_min=_prompt_validated_text(
            "Desired salary minimum (optional)",
            default=(
                str(existing.desired_salary_min) if existing and existing.desired_salary_min else ""
            ),
            validator=parse_optional_int,
        ),
        salary_currency=_prompt_required_text(
            "Salary currency",
            default=existing.salary_currency if existing else "USD",
        ),
        max_commute_distance=_prompt_validated_text(
            "Maximum commute distance (optional)",
            default=(
                str(existing.max_commute_distance)
                if existing and existing.max_commute_distance is not None
                else ""
            ),
            validator=parse_optional_int,
        ),
        commute_distance_unit=_prompt_validated_text(
            "Commute distance unit (miles or kilometers)",
            default=(existing.commute_distance_unit.value if existing else "miles"),
            validator=parse_commute_distance_unit,
            hint="Allowed values are miles or kilometers.",
        ),
        max_commute_time=_prompt_validated_text(
            "Maximum commute time in minutes (optional)",
            default=(
                str(existing.max_commute_time)
                if existing and existing.max_commute_time is not None
                else ""
            ),
            validator=parse_optional_int,
        ),
        work_authorization=typer.confirm(
            "Are you legally authorized to work?",
            default=existing.work_authorization if existing else True,
        ),
        requires_work_sponsorship=typer.confirm(
            "Do you require employer sponsorship to work?",
            default=existing.requires_work_sponsorship if existing else False,
        ),
    )

    preferences = build_user_preferences_from_answers(answers)
    service.save_user_preferences(preferences)
    console.print("Saved user preferences.")


@profile_app.command("show")
def profile_show() -> None:
    """Display the stored user preferences and career profile summary."""

    settings = get_settings()
    service = _build_profile_service()
    preferences = service.get_user_preferences()
    profile = service.get_career_profile()

    if preferences is None and profile is None:
        console.print(
            f"No profile data found. Expected files under [bold]{settings.data_dir}[/bold]."
        )
        return

    if preferences is not None:
        _render_user_preferences(preferences)

    if profile is not None:
        profile_table = Table(title="Career Profile")
        profile_table.add_column("Field")
        profile_table.add_column("Value")
        profile_table.add_row("Profile ID", profile.profile_id)
        profile_table.add_row("Experience Entries", str(len(profile.experience_entries)))
        profile_table.add_row("Skills", ", ".join(profile.skills) or "-")
        profile_table.add_row(
            "Tools & Technologies",
            ", ".join(profile.tools_and_technologies) or "-",
        )
        profile_table.add_row("Domains", ", ".join(profile.domains) or "-")
        profile_table.add_row(
            "Narrative Notes",
            str(len(profile.core_narrative_notes)),
        )
        console.print(profile_table)


@profile_app.command("init")
def profile_init() -> None:
    """Initialize profile storage scaffolding without creating profile data."""

    settings = get_settings()
    service = _build_profile_service()

    if service.profile_storage_initialized():
        console.print("Profile storage is already initialized.")
        return

    service.initialize_profile_storage()

    console.print(f"Initialized profile storage under [bold]{settings.data_dir}[/bold].")


@experience_app.command("create")
def experience_create(
    employer_name: str | None = typer.Option(
        None,
        "--employer-name",
        help="Employer or client name for the future experience entry.",
    ),
    job_title: str | None = typer.Option(
        None,
        "--job-title",
        help="Role title for the future experience entry.",
    ),
) -> None:
    """Create a draft experience intake session."""

    if (employer_name is None) != (job_title is None):
        console.print("[red]Both --employer-name and --job-title are required together.[/red]")
        raise typer.Exit(1)

    service = _build_experience_intake_service()
    session = service.create_session()
    if employer_name is not None or job_title is not None:
        try:
            session = service.capture_role_details(
                session.id,
                employer_name=employer_name,
                job_title=job_title,
            )
        except ValueError as error:
            _handle_experience_error(error)

    console.print(f"Created experience intake session [bold]{session.id}[/bold].")
    console.print("Next: add source text with `career-agent experience source SESSION_ID`.")


@experience_app.command("details")
def experience_details(
    session_id: str,
    employer_name: str | None = typer.Option(
        None,
        "--employer-name",
        help="Employer or client name for the future experience entry.",
    ),
    job_title: str | None = typer.Option(
        None,
        "--job-title",
        help="Role title for the future experience entry.",
    ),
) -> None:
    """Capture role metadata needed for the future experience entry."""

    if employer_name is None:
        employer_name = _prompt_required_text("Employer name")
    if job_title is None:
        job_title = _prompt_required_text("Job title")

    service = _build_experience_intake_service()
    try:
        session = service.capture_role_details(
            session_id,
            employer_name=employer_name,
            job_title=job_title,
        )
    except ValueError as error:
        _handle_experience_error(error)

    console.print(f"Saved role details for session [bold]{session.id}[/bold].")


@experience_app.command("list")
def experience_list() -> None:
    """List stored experience intake sessions."""

    service = _build_experience_intake_service()
    sessions = service.list_sessions()

    if not sessions:
        console.print("No experience intake sessions found.")
        return

    sessions_table = Table(title="Experience Intake Sessions")
    sessions_table.add_column("Session ID")
    sessions_table.add_column("Status")
    sessions_table.add_column("Questions", justify="right")
    sessions_table.add_column("Answers", justify="right")
    sessions_table.add_column("Draft")
    sessions_table.add_column("Updated At")

    for session in sessions:
        sessions_table.add_row(
            session.id,
            session.status.value,
            str(len(session.follow_up_questions)),
            str(len(session.user_answers)),
            "yes" if session.draft_experience_entry is not None else "no",
            session.updated_at.isoformat(),
        )

    console.print(sessions_table)


@experience_app.command("show")
def experience_show(session_id: str) -> None:
    """Show one experience intake session."""

    service = _build_experience_intake_service()
    session = service.get_session(session_id)

    if session is None:
        console.print(f"[red]Experience intake session not found: {session_id}.[/red]")
        raise typer.Exit(1)

    _render_intake_session(session)


@experience_app.command("source")
def experience_source(
    session_id: str,
    source_text: str | None = typer.Option(
        None,
        "--text",
        "-t",
        help="Raw bullets or notes for one role. If omitted, the CLI prompts for text.",
    ),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        "-f",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Read raw bullets or notes from a text file.",
    ),
    append: bool = typer.Option(
        False,
        "--append",
        help="Append source text instead of replacing existing source text.",
    ),
) -> None:
    """Capture raw source text for one role-specific intake session."""

    if source_text is not None and from_file is not None:
        console.print("[red]Use either --text or --from-file, not both.[/red]")
        raise typer.Exit(1)

    if from_file is not None:
        source_text = from_file.read_text(encoding="utf-8")
    elif source_text is None:
        source_text = typer.prompt("Source text")

    service = _build_experience_intake_service()
    try:
        session = service.capture_source_text(session_id, source_text, append=append)
    except ValueError as error:
        _handle_experience_error(error)

    console.print(f"Saved source text for session [bold]{session.id}[/bold].")
    console.print("Next: generate questions with `career-agent experience questions SESSION_ID`.")


@experience_app.command("questions")
def experience_questions(session_id: str) -> None:
    """Generate follow-up questions using the configured LLM assistant."""

    try:
        service = _build_experience_intake_service(include_assistant=True)
        session = service.generate_follow_up_questions(session_id)
    except (ValueError, RuntimeError, httpx.HTTPError) as error:
        _handle_experience_error(error)

    console.print(f"Generated follow-up questions for session [bold]{session.id}[/bold].")
    _render_intake_questions(session)


@experience_app.command("answer")
def experience_answer(session_id: str) -> None:
    """Capture answers to generated follow-up questions."""

    service = _build_experience_intake_service()
    session = service.get_session(session_id)
    if session is None:
        console.print(f"[red]Experience intake session not found: {session_id}.[/red]")
        raise typer.Exit(1)

    if session.status not in {
        ExperienceIntakeStatus.QUESTIONS_GENERATED,
        ExperienceIntakeStatus.ANSWERS_CAPTURED,
    }:
        console.print("[red]Generate follow-up questions before capturing answers.[/red]")
        raise typer.Exit(1)

    if not session.follow_up_questions:
        console.print("[red]No follow-up questions found for this session.[/red]")
        raise typer.Exit(1)

    answers_by_question_id: dict[str, str] = {}
    for index, question in enumerate(session.follow_up_questions, start=1):
        console.print(f"\n[bold]Question {index}[/bold]: {question.question}")
        if question.rationale:
            console.print(f"[dim]Why this matters: {question.rationale}[/dim]")
        answers_by_question_id[question.id] = _prompt_required_text("Answer")

    try:
        updated = service.capture_answers(session_id, answers_by_question_id)
    except ValueError as error:
        _handle_experience_error(error)

    console.print(f"Saved answers for session [bold]{updated.id}[/bold].")
    console.print(
        "Next: draft an experience entry with `career-agent experience draft SESSION_ID`."
    )
    _render_intake_answers(updated)


@experience_app.command("draft")
def experience_draft(session_id: str) -> None:
    """Generate a draft experience entry using the configured LLM assistant."""

    try:
        service = _build_experience_intake_service(include_assistant=True)
        session = service.generate_draft_entry(session_id)
    except (ValueError, RuntimeError, httpx.HTTPError) as error:
        _handle_experience_error(error)

    console.print(f"Generated draft experience entry for session [bold]{session.id}[/bold].")
    if session.draft_experience_entry is not None:
        _render_experience_entry(session.draft_experience_entry)


@experience_app.command("accept")
def experience_accept(session_id: str) -> None:
    """Accept a draft experience entry into the canonical career profile."""

    service = _build_experience_intake_service()
    try:
        session = service.accept_draft_entry(session_id)
    except (ValueError, RuntimeError) as error:
        _handle_experience_error(error)

    console.print(f"Accepted draft experience entry for session [bold]{session.id}[/bold].")
    console.print("Saved accepted entry to the canonical Career Profile.")
    if session.draft_experience_entry is not None:
        _render_experience_entry(session.draft_experience_entry)


app.add_typer(preferences_app, name="preferences")
app.add_typer(profile_app, name="profile")
app.add_typer(experience_app, name="experience")


def main() -> None:
    app()
