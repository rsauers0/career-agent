from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from career_agent.application.preferences_builder import (
    PreferenceWizardAnswers,
    build_user_preferences_from_answers,
    parse_commute_distance_unit,
    parse_optional_int,
    parse_time_zone,
    parse_work_arrangements,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus
from career_agent.config import get_settings
from career_agent.infrastructure.repositories import FileProfileRepository

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: a local-first CLI for career profiles, job search, and tailored documents.",
)
preferences_app = typer.Typer(help="Manage user preferences.")
profile_app = typer.Typer(help="Manage the career profile.")
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


def _build_profile_service() -> ProfileService:
    settings = get_settings()
    return ProfileService(FileProfileRepository(settings.data_dir))


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
        ", ".join(status.missing_required) or "-",
    )
    status_table.add_row(
        "Missing Recommended",
        ", ".join(status.missing_recommended) or "-",
    )
    console.print(status_table)


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


app.add_typer(preferences_app, name="preferences")
app.add_typer(profile_app, name="profile")


def main() -> None:
    app()
