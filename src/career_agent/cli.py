from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from career_agent.config import get_settings
from career_agent.user_preferences.models import UserPreferences
from career_agent.user_preferences.repository import UserPreferencesRepository
from career_agent.user_preferences.service import UserPreferencesService

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: local-first career workflow tooling.",
)
preferences_app = typer.Typer(help="Manage user preferences.")
console = Console()


@app.callback()
def cli() -> None:
    """Career Agent command group."""


@preferences_app.callback()
def preferences_cli() -> None:
    """Commands for working with user preferences."""


@app.command()
def doctor() -> None:
    """Confirm the v2 foundation CLI is runnable."""

    settings = get_settings()
    console.print("[bold green]Career Agent v2 foundation is ready.[/bold green]")
    console.print(f"Data directory: {settings.data_dir}")


@preferences_app.command("show")
def show_preferences() -> None:
    """Show saved user preferences."""

    service = build_user_preferences_service()
    preferences = service.get_preferences()
    if preferences is None:
        console.print("[yellow]No user preferences saved yet.[/yellow]")
        return

    render_user_preferences(preferences)


def build_user_preferences_service() -> UserPreferencesService:
    """Build the user preferences service from configured settings."""

    settings = get_settings()
    repository = UserPreferencesRepository(settings.data_dir)
    return UserPreferencesService(repository)


def render_user_preferences(preferences: UserPreferences) -> None:
    """Render user preferences as a CLI table."""

    table = Table(title="User Preferences")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Full Name", preferences.full_name)
    table.add_row("Base Location", preferences.base_location)
    table.add_row("Time Zone", preferences.time_zone or "-")
    table.add_row("Target Job Titles", ", ".join(preferences.target_job_titles) or "-")
    table.add_row("Preferred Locations", ", ".join(preferences.preferred_locations) or "-")
    table.add_row(
        "Work Arrangements",
        ", ".join(value.value for value in preferences.preferred_work_arrangements),
    )
    table.add_row(
        "Minimum Desired Salary",
        str(preferences.desired_salary_min) if preferences.desired_salary_min is not None else "-",
    )
    table.add_row("Salary Currency", preferences.salary_currency)
    table.add_row(
        "Maximum Commute Distance",
        str(preferences.max_commute_distance)
        if preferences.max_commute_distance is not None
        else "-",
    )
    table.add_row("Commute Distance Unit", preferences.commute_distance_unit.value)
    table.add_row(
        "Maximum Commute Time",
        str(preferences.max_commute_time) if preferences.max_commute_time is not None else "-",
    )
    table.add_row("Work Authorization", "Yes" if preferences.work_authorization else "No")
    table.add_row(
        "Requires Work Sponsorship",
        "Yes" if preferences.requires_work_sponsorship else "No",
    )
    console.print(table)


app.add_typer(preferences_app, name="preferences")


def main() -> None:
    """Run the Career Agent CLI."""

    app()


if __name__ == "__main__":
    main()
