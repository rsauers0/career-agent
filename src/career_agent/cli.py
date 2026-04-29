from __future__ import annotations

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from career_agent.config import get_settings
from career_agent.user_preferences.models import (
    CommuteDistanceUnit,
    UserPreferences,
    WorkArrangement,
)
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


@preferences_app.command("save")
def save_preferences(
    full_name: str = typer.Option(..., help="User's preferred display name."),
    base_location: str = typer.Option(..., help="User's home/base location."),
    work_arrangements: list[WorkArrangement] = typer.Option(
        ...,
        "--work-arrangement",
        help="Preferred work arrangement. Can be provided more than once.",
    ),
    work_authorization: bool = typer.Option(
        ...,
        "--work-authorization/--no-work-authorization",
        help="Whether the user is legally authorized to work.",
    ),
    requires_work_sponsorship: bool = typer.Option(
        ...,
        "--requires-work-sponsorship/--no-requires-work-sponsorship",
        help="Whether the user requires employer sponsorship.",
    ),
    time_zone: str | None = typer.Option(None, help="Optional IANA time zone."),
    target_job_titles: list[str] = typer.Option(
        [],
        "--target-job-title",
        help="Target job title. Can be provided more than once.",
    ),
    preferred_locations: list[str] = typer.Option(
        [],
        "--preferred-location",
        help="Preferred location. Can be provided more than once.",
    ),
    desired_salary_min: int | None = typer.Option(None, help="Minimum desired salary."),
    salary_currency: str = typer.Option("USD", help="Three-letter salary currency code."),
    max_commute_distance: int | None = typer.Option(None, help="Maximum commute distance."),
    commute_distance_unit: CommuteDistanceUnit = typer.Option(
        CommuteDistanceUnit.MILES,
        help="Commute distance unit.",
    ),
    max_commute_time: int | None = typer.Option(None, help="Maximum commute time in minutes."),
) -> None:
    """Save user preferences from explicit CLI options."""

    try:
        preferences = UserPreferences(
            full_name=full_name,
            base_location=base_location,
            time_zone=time_zone,
            target_job_titles=target_job_titles,
            preferred_locations=preferred_locations,
            preferred_work_arrangements=work_arrangements,
            desired_salary_min=desired_salary_min,
            salary_currency=salary_currency,
            max_commute_distance=max_commute_distance,
            commute_distance_unit=commute_distance_unit,
            max_commute_time=max_commute_time,
            work_authorization=work_authorization,
            requires_work_sponsorship=requires_work_sponsorship,
        )
    except ValidationError as exc:
        console.print("[red]Could not save user preferences.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    service = build_user_preferences_service()
    service.save_preferences(preferences)
    console.print("[green]Saved user preferences.[/green]")


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
