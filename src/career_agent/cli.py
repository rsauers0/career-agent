from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from career_agent.config import get_settings
from career_agent.experience_roles.models import (
    EmploymentType,
    ExperienceRole,
    ExperienceRoleStatus,
)
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.experience_roles.service import ExperienceRoleService
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.role_sources.repository import RoleSourceRepository
from career_agent.role_sources.service import RoleNotFoundError, RoleSourceService
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
roles_app = typer.Typer(help="Manage experience roles.")
sources_app = typer.Typer(help="Manage role source entries.")
console = Console()


@app.callback()
def cli() -> None:
    """Career Agent command group."""


@preferences_app.callback()
def preferences_cli() -> None:
    """Commands for working with user preferences."""


@roles_app.callback()
def roles_cli() -> None:
    """Commands for working with experience roles."""


@sources_app.callback()
def sources_cli() -> None:
    """Commands for working with role source entries."""


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


@roles_app.command("list")
def list_roles() -> None:
    """List saved experience roles."""

    service = build_experience_role_service()
    roles = service.list_roles()
    if not roles:
        console.print("[yellow]No experience roles saved yet.[/yellow]")
        return

    render_experience_role_list(roles)


@roles_app.command("show")
def show_role(role_id: str = typer.Argument(..., help="Experience role identifier.")) -> None:
    """Show one saved experience role."""

    service = build_experience_role_service()
    role = service.get_role(role_id)
    if role is None:
        console.print(f"[yellow]No experience role found for id: {role_id}[/yellow]")
        raise typer.Exit(1)

    render_experience_role(role)


@roles_app.command("save")
def save_role(
    employer_name: str = typer.Option(..., help="Employer, client, or organization name."),
    job_title: str = typer.Option(..., help="Role title held by the user."),
    start_date: str = typer.Option(..., help="Role start month/year, such as 05/2021."),
    role_id: str | None = typer.Option(None, help="Existing role id to update."),
    end_date: str | None = typer.Option(
        None,
        help="Role end month/year, such as 06/2024. Omit for current roles.",
    ),
    current: bool = typer.Option(
        False,
        "--current",
        help="Mark this as a current role. Current roles cannot have an end date.",
    ),
    location: str | None = typer.Option(None, help="Optional role location."),
    employment_type: EmploymentType | None = typer.Option(
        None,
        help="Optional employment type.",
    ),
    status: ExperienceRoleStatus = typer.Option(
        ExperienceRoleStatus.INPUT_REQUIRED,
        help="Role workflow status.",
    ),
) -> None:
    """Save an experience role from explicit CLI options."""

    try:
        role_data = {
            "employer_name": employer_name,
            "job_title": job_title,
            "location": location,
            "employment_type": employment_type,
            "start_date": start_date,
            "end_date": end_date,
            "is_current_role": current,
            "status": status,
        }
        if role_id is not None:
            role_data["id"] = role_id
        role = ExperienceRole(**role_data)
    except ValidationError as exc:
        console.print("[red]Could not save experience role.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    service = build_experience_role_service()
    service.save_role(role)
    console.print("[green]Saved experience role.[/green]")
    console.print(f"Role ID: {role.id}")


@roles_app.command("delete")
def delete_role(role_id: str = typer.Argument(..., help="Experience role identifier.")) -> None:
    """Delete one saved experience role."""

    service = build_experience_role_service()
    if not service.delete_role(role_id):
        console.print(f"[yellow]No experience role found for id: {role_id}[/yellow]")
        raise typer.Exit(1)

    console.print("[green]Deleted experience role.[/green]")


@sources_app.command("list")
def list_sources(
    role_id: str | None = typer.Option(None, help="Optional role id to filter sources."),
) -> None:
    """List saved role source entries."""

    service = build_role_source_service()
    sources = service.list_sources(role_id=role_id)
    if not sources:
        console.print("[yellow]No role sources saved yet.[/yellow]")
        return

    render_role_source_list(sources)


@sources_app.command("show")
def show_source(source_id: str = typer.Argument(..., help="Role source identifier.")) -> None:
    """Show one saved role source entry."""

    service = build_role_source_service()
    source = service.get_source(source_id)
    if source is None:
        console.print(f"[yellow]No role source found for id: {source_id}[/yellow]")
        raise typer.Exit(1)

    render_role_source(source)


@sources_app.command("add")
def add_source(
    role_id: str = typer.Option(..., help="Existing experience role id."),
    source_text: str | None = typer.Option(None, help="Source text to save."),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a UTF-8 text file containing source material.",
    ),
) -> None:
    """Add source material for an existing experience role."""

    if (source_text is None) == (from_file is None):
        console.print("[red]Provide exactly one of --source-text or --from-file.[/red]")
        raise typer.Exit(1)

    if from_file is not None:
        source_text = from_file.read_text(encoding="utf-8")

    service = build_role_source_service()
    try:
        source = service.add_source(role_id=role_id, source_text=source_text or "")
    except RoleNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save role source.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved role source.[/green]")
    console.print(f"Source ID: {source.id}")


@sources_app.command("delete")
def delete_source(source_id: str = typer.Argument(..., help="Role source identifier.")) -> None:
    """Delete one saved role source entry."""

    service = build_role_source_service()
    if not service.delete_source(source_id):
        console.print(f"[yellow]No role source found for id: {source_id}[/yellow]")
        raise typer.Exit(1)

    console.print("[green]Deleted role source.[/green]")


def build_user_preferences_service() -> UserPreferencesService:
    """Build the user preferences service from configured settings."""

    settings = get_settings()
    repository = UserPreferencesRepository(settings.data_dir)
    return UserPreferencesService(repository)


def build_experience_role_service() -> ExperienceRoleService:
    """Build the experience role service from configured settings."""

    settings = get_settings()
    repository = ExperienceRoleRepository(settings.data_dir)
    return ExperienceRoleService(repository)


def build_role_source_service() -> RoleSourceService:
    """Build the role source service from configured settings."""

    settings = get_settings()
    source_repository = RoleSourceRepository(settings.data_dir)
    role_repository = ExperienceRoleRepository(settings.data_dir)
    return RoleSourceService(source_repository, role_repository)


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


def render_experience_role_list(roles: list[ExperienceRole]) -> None:
    """Render experience roles as a compact CLI table."""

    table = Table(title="Experience Roles")
    table.add_column("ID", no_wrap=True)
    table.add_column("Employer", no_wrap=True)
    table.add_column("Job Title", no_wrap=True)
    table.add_column("Dates", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    for role in roles:
        table.add_row(
            role.id,
            role.employer_name,
            role.job_title,
            format_role_dates(role),
            role.status.value,
        )
    console.print(table)


def render_experience_role(role: ExperienceRole) -> None:
    """Render one experience role as a CLI table."""

    table = Table(title="Experience Role")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", role.id)
    table.add_row("Employer", role.employer_name)
    table.add_row("Job Title", role.job_title)
    table.add_row("Location", role.location or "-")
    table.add_row("Employment Type", role.employment_type.value if role.employment_type else "-")
    table.add_row("Dates", format_role_dates(role))
    table.add_row("Current Role", "Yes" if role.is_current_role else "No")
    table.add_row("Status", role.status.value)
    table.add_row("Created At", role.created_at.isoformat())
    table.add_row("Updated At", role.updated_at.isoformat())
    console.print(table)


def format_role_dates(role: ExperienceRole) -> str:
    """Format role dates for display."""

    start_date = f"{role.start_date.month:02d}/{role.start_date.year}"
    if role.is_current_role:
        return f"{start_date} - Present"
    if role.end_date is None:
        return start_date
    end_date = f"{role.end_date.month:02d}/{role.end_date.year}"
    return f"{start_date} - {end_date}"


def render_role_source_list(sources: list[RoleSourceEntry]) -> None:
    """Render role source entries as a compact CLI table."""

    table = Table(title="Role Sources")
    table.add_column("ID", no_wrap=True)
    table.add_column("Role ID", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Preview")
    for source in sources:
        table.add_row(
            source.id,
            source.role_id,
            source.status.value,
            preview_source_text(source.source_text),
        )
    console.print(table)


def render_role_source(source: RoleSourceEntry) -> None:
    """Render one role source entry as a CLI table."""

    table = Table(title="Role Source")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", source.id)
    table.add_row("Role ID", source.role_id)
    table.add_row("Status", source.status.value)
    table.add_row("Created At", source.created_at.isoformat())
    table.add_row("Source Text", source.source_text)
    console.print(table)


def preview_source_text(source_text: str, max_length: int = 80) -> str:
    """Return a one-line preview of submitted source text."""

    preview = " ".join(source_text.split())
    if len(preview) <= max_length:
        return preview
    return f"{preview[: max_length - 3]}..."


app.add_typer(preferences_app, name="preferences")
app.add_typer(roles_app, name="roles")
app.add_typer(sources_app, name="sources")


def main() -> None:
    """Run the Career Agent CLI."""

    app()


if __name__ == "__main__":
    main()
