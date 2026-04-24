from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from career_agent.application.profile_service import ProfileService
from career_agent.config import get_settings
from career_agent.infrastructure.repositories import FileProfileRepository

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: a local-first CLI for career profiles, job search, and tailored documents.",
)
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


@profile_app.callback()
def profile_cli() -> None:
    """Commands for working with the career profile."""


@profile_app.command("show")
def profile_show() -> None:
    """Display the stored user preferences and career profile summary."""

    settings = get_settings()
    service = ProfileService(FileProfileRepository(settings.data_dir))
    preferences = service.get_user_preferences()
    profile = service.get_career_profile()

    if preferences is None and profile is None:
        console.print(
            f"No profile data found. Expected files under [bold]{settings.data_dir}[/bold]."
        )
        return

    if preferences is not None:
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
    service = ProfileService(FileProfileRepository(settings.data_dir))

    if service.profile_storage_initialized():
        console.print("Profile storage is already initialized.")
        return

    service.initialize_profile_storage()

    console.print(f"Initialized profile storage under [bold]{settings.data_dir}[/bold].")


app.add_typer(profile_app, name="profile")


def main() -> None:
    app()
