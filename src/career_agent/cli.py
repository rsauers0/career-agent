from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from career_agent.config import get_settings
from career_agent.errors import (
    ActiveAnalysisRunExistsError,
    ActiveFactReviewThreadExistsError,
    AnalysisRunNotFoundError,
    ClarificationQuestionNotFoundError,
    EvidenceReferenceRemovalError,
    FactNotFoundError,
    FactReviewActionNotFoundError,
    FactReviewThreadNotFoundError,
    FactRevisionNotAllowedError,
    FactRoleMismatchError,
    InvalidFactReviewActionStatusTransitionError,
    InvalidFactReviewThreadStatusTransitionError,
    InvalidFactStatusTransitionError,
    InvalidLLMOutputError,
    InvalidScopedConstraintStatusTransitionError,
    InvalidSourceFindingStatusTransitionError,
    LLMClientError,
    LLMConfigurationError,
    NoUnanalyzedSourcesError,
    OpenClarificationQuestionsError,
    RoleNotFoundError,
    ScopedConstraintNotFoundError,
    SourceFindingNotFoundError,
    SourceFindingsAlreadyExistError,
    SourceNotFoundError,
    SourceNotInAnalysisRunError,
    SourceRoleMismatchError,
)
from career_agent.experience_facts.models import (
    ExperienceFact,
    FactChangeActor,
    FactChangeEvent,
)
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_facts.service import ExperienceFactService
from career_agent.experience_roles.models import (
    EmploymentType,
    ExperienceRole,
    ExperienceRoleStatus,
)
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.experience_roles.service import ExperienceRoleService
from career_agent.experience_workflow.factory import (
    build_source_finding_generator,
    build_source_question_generator,
)
from career_agent.experience_workflow.service import (
    AppliedSourceFindingResult,
    ExperienceWorkflowService,
)
from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionType,
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
)
from career_agent.fact_review.repository import FactReviewRepository
from career_agent.fact_review.service import FactReviewService
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.role_sources.repository import RoleSourceRepository
from career_agent.role_sources.service import RoleSourceService
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.scoped_constraints.repository import ScopedConstraintRepository
from career_agent.scoped_constraints.service import ScopedConstraintService
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceFinding,
    SourceFindingType,
)
from career_agent.source_analysis.repository import SourceAnalysisRepository
from career_agent.source_analysis.service import SourceAnalysisService
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
facts_app = typer.Typer(help="Manage canonical experience facts.")
constraints_app = typer.Typer(help="Manage scoped constraints.")
source_analysis_app = typer.Typer(help="Manage source analysis workflow artifacts.")
analysis_runs_app = typer.Typer(help="Manage source analysis runs.")
analysis_questions_app = typer.Typer(help="Manage source clarification questions.")
analysis_messages_app = typer.Typer(help="Manage source clarification messages.")
analysis_findings_app = typer.Typer(help="Manage structured source findings.")
fact_review_app = typer.Typer(help="Manage fact review workflow artifacts.")
fact_review_threads_app = typer.Typer(help="Manage fact review threads.")
fact_review_messages_app = typer.Typer(help="Manage fact review messages.")
fact_review_actions_app = typer.Typer(help="Manage structured fact review actions.")
experience_workflow_app = typer.Typer(help="Run experience workflow harness commands.")
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


@facts_app.callback()
def facts_cli() -> None:
    """Commands for working with canonical experience facts."""


@constraints_app.callback()
def constraints_cli() -> None:
    """Commands for working with scoped constraints."""


@source_analysis_app.callback()
def source_analysis_cli() -> None:
    """Commands for working with source analysis workflow artifacts."""


@fact_review_app.callback()
def fact_review_cli() -> None:
    """Commands for working with fact review workflow artifacts."""


@fact_review_threads_app.callback()
def fact_review_threads_cli() -> None:
    """Commands for working with fact review threads."""


@fact_review_messages_app.callback()
def fact_review_messages_cli() -> None:
    """Commands for working with fact review messages."""


@fact_review_actions_app.callback()
def fact_review_actions_cli() -> None:
    """Commands for working with structured fact review actions."""


@analysis_runs_app.callback()
def analysis_runs_cli() -> None:
    """Commands for working with source analysis runs."""


@analysis_questions_app.callback()
def analysis_questions_cli() -> None:
    """Commands for working with source clarification questions."""


@analysis_messages_app.callback()
def analysis_messages_cli() -> None:
    """Commands for working with source clarification messages."""


@analysis_findings_app.callback()
def analysis_findings_cli() -> None:
    """Commands for working with structured source findings."""


@experience_workflow_app.callback()
def experience_workflow_cli() -> None:
    """Commands for running experience workflow harnesses."""


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
    role_focus: str | None = typer.Option(
        None,
        help="Optional 1-2 sentence user-authored description of the role's primary focus.",
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
            "role_focus": role_focus,
            "start_date": start_date,
            "end_date": end_date,
            "is_current_role": current,
            "status": status,
        }
        if role_id is not None:
            role_data["id"] = role_id
        role = ExperienceRole.model_validate(role_data)
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


@facts_app.command("list")
def list_facts(
    role_id: str | None = typer.Option(None, help="Optional role id to filter facts."),
) -> None:
    """List saved experience facts."""

    service = build_experience_fact_service()
    facts = service.list_facts(role_id=role_id)
    if not facts:
        console.print("[yellow]No experience facts saved yet.[/yellow]")
        return

    render_experience_fact_list(facts)


@facts_app.command("show")
def show_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
) -> None:
    """Show one saved experience fact."""

    service = build_experience_fact_service()
    fact = service.get_fact(fact_id)
    if fact is None:
        console.print(f"[yellow]No experience fact found for id: {fact_id}[/yellow]")
        raise typer.Exit(1)

    render_experience_fact(fact)


@facts_app.command("events")
def list_fact_change_events(
    fact_id: str | None = typer.Option(None, help="Optional fact id to filter events."),
    role_id: str | None = typer.Option(None, help="Optional role id to filter events."),
) -> None:
    """List experience fact change events."""

    service = build_experience_fact_service()
    events = service.list_change_events(fact_id=fact_id, role_id=role_id)
    if not events:
        console.print("[yellow]No fact change events saved yet.[/yellow]")
        return

    render_fact_change_event_list(events)


@facts_app.command("add")
def add_fact(
    role_id: str = typer.Option(..., help="Existing experience role id."),
    text: str = typer.Option(..., help="Experience fact text."),
    source_ids: list[str] = typer.Option(
        [],
        "--source-id",
        help="Source id supporting this fact. Can be provided more than once.",
    ),
    question_ids: list[str] = typer.Option(
        [],
        "--question-id",
        help="Clarification question id supporting this fact. Can be provided more than once.",
    ),
    message_ids: list[str] = typer.Option(
        [],
        "--message-id",
        help="Clarification message id supporting this fact. Can be provided more than once.",
    ),
    details: list[str] = typer.Option(
        [],
        "--detail",
        help="Second-level detail clarifying this fact. Can be provided more than once.",
    ),
    systems: list[str] = typer.Option(
        [],
        "--system",
        help=(
            "Referenced system, platform, application, or environment. "
            "Can be provided more than once."
        ),
    ),
    skills: list[str] = typer.Option(
        [],
        "--skill",
        help="Referenced skill, tool, technology, or method. Can be provided more than once.",
    ),
    functions: list[str] = typer.Option(
        [],
        "--function",
        help="Referenced duty, function, or work category. Can be provided more than once.",
    ),
    supersedes_fact_id: str | None = typer.Option(
        None,
        help="Existing fact id this fact replaces or revises.",
    ),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    summary: str | None = typer.Option(
        None,
        help="Optional summary for the change event.",
    ),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Add a canonical experience fact for an existing role."""

    service = build_experience_fact_service()
    try:
        fact = service.add_fact(
            role_id=role_id,
            text=text,
            source_ids=source_ids,
            question_ids=question_ids,
            message_ids=message_ids,
            details=details,
            systems=systems,
            skills=skills,
            functions=functions,
            supersedes_fact_id=supersedes_fact_id,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids,
        )
    except (
        FactNotFoundError,
        FactRoleMismatchError,
        RoleNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save experience fact.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved experience fact.[/green]")
    console.print(f"Fact ID: {fact.id}")


@facts_app.command("activate")
def activate_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason this fact was activated."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Activate a draft experience fact."""

    service = build_experience_fact_service()
    try:
        fact = service.activate_fact(
            fact_id,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (FactNotFoundError, InvalidFactStatusTransitionError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Activated experience fact.[/green]")
    console.print(f"Fact ID: {fact.id}")


@facts_app.command("needs-clarification")
def mark_fact_needs_clarification(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason clarification is needed."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Mark a draft experience fact as needing clarification."""

    service = build_experience_fact_service()
    try:
        fact = service.mark_needs_clarification(
            fact_id,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (FactNotFoundError, InvalidFactStatusTransitionError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Marked experience fact as needing clarification.[/green]")
    console.print(f"Fact ID: {fact.id}")
    if reason:
        console.print(f"Reason: {reason}")


@facts_app.command("draft")
def return_fact_to_draft(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason this fact returned to draft."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Return a needs-clarification experience fact to draft."""

    service = build_experience_fact_service()
    try:
        fact = service.return_to_draft(
            fact_id,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (FactNotFoundError, InvalidFactStatusTransitionError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Returned experience fact to draft.[/green]")
    console.print(f"Fact ID: {fact.id}")


@facts_app.command("reject")
def reject_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason this fact was rejected."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Reject a draft or needs-clarification experience fact."""

    service = build_experience_fact_service()
    try:
        fact = service.reject_fact(
            fact_id,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (FactNotFoundError, InvalidFactStatusTransitionError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Rejected experience fact.[/green]")
    console.print(f"Fact ID: {fact.id}")
    if reason:
        console.print(f"Reason: {reason}")


@facts_app.command("archive")
def archive_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason this fact was archived."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Archive an experience fact."""

    service = build_experience_fact_service()
    try:
        fact = service.archive_fact(
            fact_id,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (FactNotFoundError, InvalidFactStatusTransitionError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Archived experience fact.[/green]")
    console.print(f"Fact ID: {fact.id}")


@facts_app.command("revise")
def revise_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
    text: str = typer.Option(..., help="Revised experience fact text."),
    source_ids: list[str] = typer.Option(
        [],
        "--source-id",
        help="Additional source id supporting this revision. Can be provided more than once.",
    ),
    question_ids: list[str] = typer.Option(
        [],
        "--question-id",
        help="Additional clarification question id. Can be provided more than once.",
    ),
    message_ids: list[str] = typer.Option(
        [],
        "--message-id",
        help="Additional clarification message id. Can be provided more than once.",
    ),
    details: list[str] = typer.Option(
        [],
        "--detail",
        help="Replacement second-level detail. Can be provided more than once.",
    ),
    systems: list[str] = typer.Option(
        [],
        "--system",
        help="Replacement referenced system list item. Can be provided more than once.",
    ),
    skills: list[str] = typer.Option(
        [],
        "--skill",
        help="Replacement referenced skill list item. Can be provided more than once.",
    ),
    functions: list[str] = typer.Option(
        [],
        "--function",
        help="Replacement referenced function list item. Can be provided more than once.",
    ),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.USER,
        help="Workflow actor recorded for the change event.",
    ),
    reason: str | None = typer.Option(None, help="Reason this fact was revised."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Clarification message id that caused this change. Can be provided more than once.",
    ),
) -> None:
    """Revise an experience fact according to lifecycle rules."""

    service = build_experience_fact_service()
    try:
        fact = service.revise_fact(
            fact_id=fact_id,
            text=text,
            source_ids=source_ids,
            question_ids=question_ids,
            message_ids=message_ids,
            details=details,
            systems=systems,
            skills=skills,
            functions=functions,
            actor=actor,
            summary=reason,
            source_message_ids=source_message_ids,
        )
    except (
        EvidenceReferenceRemovalError,
        FactNotFoundError,
        FactRevisionNotAllowedError,
        RoleNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
        ValidationError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Revised experience fact.[/green]")
    console.print(f"Fact ID: {fact.id}")


@facts_app.command("delete")
def delete_fact(
    fact_id: str = typer.Argument(..., help="Experience fact identifier."),
) -> None:
    """Delete one saved experience fact."""

    service = build_experience_fact_service()
    if not service.delete_fact(fact_id):
        console.print(f"[yellow]No experience fact found for id: {fact_id}[/yellow]")
        raise typer.Exit(1)

    console.print("[green]Deleted experience fact.[/green]")


@constraints_app.command("list")
def list_constraints(
    scope_type: ConstraintScopeType | None = typer.Option(None, help="Optional scope type."),
    scope_id: str | None = typer.Option(None, help="Optional scope id."),
    status: ScopedConstraintStatus | None = typer.Option(None, help="Optional constraint status."),
) -> None:
    """List scoped constraints."""

    service = build_scoped_constraint_service()
    constraints = service.list_constraints(
        scope_type=scope_type,
        scope_id=scope_id,
        status=status,
    )
    if not constraints:
        console.print("[yellow]No scoped constraints saved yet.[/yellow]")
        return

    render_scoped_constraint_list(constraints)


@constraints_app.command("applicable")
def list_applicable_constraints(
    role_id: str | None = typer.Option(None, help="Optional role id."),
    fact_id: str | None = typer.Option(None, help="Optional fact id."),
) -> None:
    """List active constraints that apply to a workflow context."""

    service = build_scoped_constraint_service()
    try:
        constraints = service.list_applicable_constraints(role_id=role_id, fact_id=fact_id)
    except (
        FactNotFoundError,
        FactRoleMismatchError,
        RoleNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if not constraints:
        console.print("[yellow]No applicable scoped constraints saved yet.[/yellow]")
        return

    render_scoped_constraint_list(constraints)


@constraints_app.command("add")
def add_constraint(
    scope_type: ConstraintScopeType = typer.Option(
        ...,
        help="Scope type: global, role, or fact.",
    ),
    constraint_type: ConstraintType = typer.Option(
        ...,
        help="Constraint type: hard_rule or preference.",
    ),
    rule_text: str = typer.Option(..., help="Rule or preference text."),
    scope_id: str | None = typer.Option(
        None,
        help="Required for role and fact scopes. Must be omitted for global scope.",
    ),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Workflow message id that caused this constraint. Can be provided more than once.",
    ),
) -> None:
    """Add a proposed scoped constraint."""

    service = build_scoped_constraint_service()
    try:
        constraint = service.add_constraint(
            scope_type=scope_type,
            constraint_type=constraint_type,
            rule_text=rule_text,
            scope_id=scope_id,
            source_message_ids=source_message_ids,
        )
    except (
        FactNotFoundError,
        RoleNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save scoped constraint.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved scoped constraint.[/green]")
    console.print(f"Constraint ID: {constraint.id}")


@constraints_app.command("activate")
def activate_constraint(
    constraint_id: str = typer.Argument(..., help="Scoped constraint identifier."),
) -> None:
    """Activate a proposed scoped constraint."""

    service = build_scoped_constraint_service()
    try:
        constraint = service.activate_constraint(constraint_id)
    except (
        InvalidScopedConstraintStatusTransitionError,
        ScopedConstraintNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Activated scoped constraint.[/green]")
    console.print(f"Constraint ID: {constraint.id}")


@constraints_app.command("reject")
def reject_constraint(
    constraint_id: str = typer.Argument(..., help="Scoped constraint identifier."),
) -> None:
    """Reject a proposed scoped constraint."""

    service = build_scoped_constraint_service()
    try:
        constraint = service.reject_constraint(constraint_id)
    except (
        InvalidScopedConstraintStatusTransitionError,
        ScopedConstraintNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Rejected scoped constraint.[/green]")
    console.print(f"Constraint ID: {constraint.id}")


@constraints_app.command("archive")
def archive_constraint(
    constraint_id: str = typer.Argument(..., help="Scoped constraint identifier."),
) -> None:
    """Archive a scoped constraint."""

    service = build_scoped_constraint_service()
    try:
        constraint = service.archive_constraint(constraint_id)
    except (
        InvalidScopedConstraintStatusTransitionError,
        ScopedConstraintNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Archived scoped constraint.[/green]")
    console.print(f"Constraint ID: {constraint.id}")


@analysis_runs_app.command("list")
def list_source_analysis_runs(
    role_id: str | None = typer.Option(None, help="Optional role id to filter runs."),
) -> None:
    """List saved source analysis runs."""

    service = build_source_analysis_service()
    runs = service.list_runs(role_id=role_id)
    if not runs:
        console.print("[yellow]No source analysis runs saved yet.[/yellow]")
        return

    render_source_analysis_run_list(runs)


@analysis_runs_app.command("start")
def start_source_analysis_run(
    role_id: str = typer.Option(..., help="Existing experience role id."),
    source_ids: list[str] = typer.Option(
        ...,
        "--source-id",
        help="Source id included in this run. Can be provided more than once.",
    ),
) -> None:
    """Start a source analysis run for an experience role."""

    service = build_source_analysis_service()
    try:
        run = service.start_run(role_id=role_id, source_ids=source_ids)
    except (
        ActiveAnalysisRunExistsError,
        RoleNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not start source analysis run.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Started source analysis run.[/green]")
    console.print(f"Run ID: {run.id}")


@analysis_questions_app.command("list")
def list_source_analysis_questions(
    run_id: str = typer.Option(..., help="Source analysis run id."),
) -> None:
    """List clarification questions for a source analysis run."""

    service = build_source_analysis_service()
    questions = service.list_questions(run_id)
    if not questions:
        console.print("[yellow]No clarification questions saved yet.[/yellow]")
        return

    render_source_clarification_question_list(questions)


@analysis_questions_app.command("add")
def add_source_analysis_question(
    run_id: str = typer.Option(..., help="Existing source analysis run id."),
    text: str | None = typer.Option(None, help="Clarification question text."),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a UTF-8 text file containing clarification question text.",
    ),
    relevant_source_ids: list[str] = typer.Option(
        [],
        "--relevant-source-id",
        help="Source id relevant to this question. Can be provided more than once.",
    ),
) -> None:
    """Add a clarification question to an existing source analysis run."""

    if (text is None) == (from_file is None):
        console.print("[red]Provide exactly one of --text or --from-file.[/red]")
        raise typer.Exit(1)

    if from_file is not None:
        text = from_file.read_text(encoding="utf-8")

    service = build_source_analysis_service()
    try:
        question = service.add_question(
            analysis_run_id=run_id,
            question_text=text or "",
            relevant_source_ids=relevant_source_ids,
        )
    except (AnalysisRunNotFoundError, SourceNotInAnalysisRunError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save clarification question.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved clarification question.[/green]")
    console.print(f"Question ID: {question.id}")


@analysis_questions_app.command("resolve")
def resolve_source_analysis_question(
    question_id: str = typer.Argument(..., help="Clarification question identifier."),
) -> None:
    """Mark a clarification question as resolved."""

    service = build_source_analysis_service()
    try:
        question = service.resolve_question(question_id)
    except ClarificationQuestionNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Resolved clarification question.[/green]")
    console.print(f"Question ID: {question.id}")


@analysis_questions_app.command("skip")
def skip_source_analysis_question(
    question_id: str = typer.Argument(..., help="Clarification question identifier."),
) -> None:
    """Mark a clarification question as skipped."""

    service = build_source_analysis_service()
    try:
        question = service.skip_question(question_id)
    except ClarificationQuestionNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Skipped clarification question.[/green]")
    console.print(f"Question ID: {question.id}")


@analysis_messages_app.command("list")
def list_source_analysis_messages(
    question_id: str = typer.Option(..., help="Clarification question id."),
) -> None:
    """List messages for a source clarification question."""

    service = build_source_analysis_service()
    messages = service.list_messages(question_id)
    if not messages:
        console.print("[yellow]No clarification messages saved yet.[/yellow]")
        return

    render_source_clarification_message_list(messages)


@analysis_messages_app.command("add")
def add_source_analysis_message(
    question_id: str = typer.Option(..., help="Existing clarification question id."),
    author: ClarificationMessageAuthor = typer.Option(
        ...,
        help="Message author: assistant, user, or system.",
    ),
    text: str | None = typer.Option(None, help="Clarification message text."),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a UTF-8 text file containing clarification message text.",
    ),
) -> None:
    """Append one message to a clarification question thread."""

    if (text is None) == (from_file is None):
        console.print("[red]Provide exactly one of --text or --from-file.[/red]")
        raise typer.Exit(1)

    if from_file is not None:
        text = from_file.read_text(encoding="utf-8")

    service = build_source_analysis_service()
    try:
        message = service.add_message(
            question_id=question_id,
            author=author,
            message_text=text or "",
        )
    except ClarificationQuestionNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save clarification message.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved clarification message.[/green]")
    console.print(f"Message ID: {message.id}")


@analysis_findings_app.command("list")
def list_source_analysis_findings(
    run_id: str | None = typer.Option(None, help="Optional source analysis run id."),
    role_id: str | None = typer.Option(None, help="Optional role id."),
    source_id: str | None = typer.Option(None, help="Optional source id."),
    fact_id: str | None = typer.Option(None, help="Optional fact id."),
) -> None:
    """List structured source findings."""

    service = build_source_analysis_service()
    findings = service.list_findings(
        analysis_run_id=run_id,
        role_id=role_id,
        source_id=source_id,
        fact_id=fact_id,
    )
    if not findings:
        console.print("[yellow]No source findings saved yet.[/yellow]")
        return

    render_source_finding_list(findings)


@analysis_findings_app.command("add")
def add_source_analysis_finding(
    run_id: str = typer.Option(..., help="Existing source analysis run id."),
    source_id: str = typer.Option(..., help="Source id evaluated by this finding."),
    finding_type: SourceFindingType = typer.Option(
        ...,
        help="Finding type.",
    ),
    fact_id: str | None = typer.Option(
        None,
        help="Existing fact id being compared, when applicable.",
    ),
    proposed_fact_text: str | None = typer.Option(
        None,
        help="Candidate normalized fact text for new_fact findings.",
    ),
    rationale: str | None = typer.Option(None, help="Optional rationale for the finding."),
) -> None:
    """Add a structured source finding to an existing source analysis run."""

    service = build_source_analysis_service()
    try:
        finding = service.add_finding(
            analysis_run_id=run_id,
            source_id=source_id,
            finding_type=finding_type,
            fact_id=fact_id,
            proposed_fact_text=proposed_fact_text,
            rationale=rationale,
        )
    except (
        AnalysisRunNotFoundError,
        FactNotFoundError,
        FactRoleMismatchError,
        SourceNotFoundError,
        SourceNotInAnalysisRunError,
        SourceRoleMismatchError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save source finding.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved source finding.[/green]")
    console.print(f"Finding ID: {finding.id}")


@analysis_findings_app.command("accept")
def accept_source_analysis_finding(
    finding_id: str = typer.Argument(..., help="Source finding identifier."),
) -> None:
    """Accept a source finding without mutating canonical facts."""

    service = build_source_analysis_service()
    try:
        finding = service.accept_finding(finding_id)
    except (
        InvalidSourceFindingStatusTransitionError,
        SourceFindingNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Accepted source finding.[/green]")
    console.print(f"Finding ID: {finding.id}")


@analysis_findings_app.command("reject")
def reject_source_analysis_finding(
    finding_id: str = typer.Argument(..., help="Source finding identifier."),
) -> None:
    """Reject a source finding without mutating canonical facts."""

    service = build_source_analysis_service()
    try:
        finding = service.reject_finding(finding_id)
    except (
        InvalidSourceFindingStatusTransitionError,
        SourceFindingNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Rejected source finding.[/green]")
    console.print(f"Finding ID: {finding.id}")


@analysis_findings_app.command("archive")
def archive_source_analysis_finding(
    finding_id: str = typer.Argument(..., help="Source finding identifier."),
) -> None:
    """Archive a source finding."""

    service = build_source_analysis_service()
    try:
        finding = service.archive_finding(finding_id)
    except (
        InvalidSourceFindingStatusTransitionError,
        SourceFindingNotFoundError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Archived source finding.[/green]")
    console.print(f"Finding ID: {finding.id}")


@fact_review_threads_app.command("start")
def start_fact_review_thread(
    fact_id: str = typer.Option(..., help="Existing experience fact id."),
) -> None:
    """Start a review thread for an experience fact."""

    service = build_fact_review_service()
    try:
        thread = service.start_thread(fact_id)
    except (ActiveFactReviewThreadExistsError, FactNotFoundError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not start fact review thread.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Started fact review thread.[/green]")
    console.print(f"Thread ID: {thread.id}")


@fact_review_threads_app.command("list")
def list_fact_review_threads(
    fact_id: str | None = typer.Option(None, help="Optional fact id."),
    role_id: str | None = typer.Option(None, help="Optional role id."),
) -> None:
    """List fact review threads."""

    service = build_fact_review_service()
    threads = service.list_threads(fact_id=fact_id, role_id=role_id)
    if not threads:
        console.print("[yellow]No fact review threads saved yet.[/yellow]")
        return

    render_fact_review_thread_list(threads)


@fact_review_threads_app.command("resolve")
def resolve_fact_review_thread(
    thread_id: str = typer.Argument(..., help="Fact review thread identifier."),
) -> None:
    """Mark a fact review thread as resolved."""

    service = build_fact_review_service()
    try:
        thread = service.resolve_thread(thread_id)
    except (
        FactReviewThreadNotFoundError,
        InvalidFactReviewThreadStatusTransitionError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Resolved fact review thread.[/green]")
    console.print(f"Thread ID: {thread.id}")


@fact_review_threads_app.command("archive")
def archive_fact_review_thread(
    thread_id: str = typer.Argument(..., help="Fact review thread identifier."),
) -> None:
    """Archive a fact review thread."""

    service = build_fact_review_service()
    try:
        thread = service.archive_thread(thread_id)
    except (
        FactReviewThreadNotFoundError,
        InvalidFactReviewThreadStatusTransitionError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Archived fact review thread.[/green]")
    console.print(f"Thread ID: {thread.id}")


@fact_review_messages_app.command("list")
def list_fact_review_messages(
    thread_id: str = typer.Option(..., help="Fact review thread id."),
) -> None:
    """List messages for a fact review thread."""

    service = build_fact_review_service()
    messages = service.list_messages(thread_id)
    if not messages:
        console.print("[yellow]No fact review messages saved yet.[/yellow]")
        return

    render_fact_review_message_list(messages)


@fact_review_messages_app.command("add")
def add_fact_review_message(
    thread_id: str = typer.Option(..., help="Existing fact review thread id."),
    author: FactReviewMessageAuthor = typer.Option(
        ...,
        help="Message author: assistant, user, or system.",
    ),
    text: str | None = typer.Option(None, help="Fact review message text."),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a UTF-8 text file containing fact review message text.",
    ),
    recommended_action: FactReviewRecommendedAction = typer.Option(
        FactReviewRecommendedAction.NONE,
        help="Optional recommended action metadata.",
    ),
) -> None:
    """Append one message to a fact review thread."""

    if (text is None) == (from_file is None):
        console.print("[red]Provide exactly one of --text or --from-file.[/red]")
        raise typer.Exit(1)

    if from_file is not None:
        text = from_file.read_text(encoding="utf-8")

    service = build_fact_review_service()
    try:
        message = service.add_message(
            thread_id=thread_id,
            author=author,
            message_text=text or "",
            recommended_action=recommended_action,
        )
    except FactReviewThreadNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save fact review message.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved fact review message.[/green]")
    console.print(f"Message ID: {message.id}")


@fact_review_actions_app.command("list")
def list_fact_review_actions(
    thread_id: str | None = typer.Option(None, help="Optional fact review thread id."),
    fact_id: str | None = typer.Option(None, help="Optional fact id."),
    role_id: str | None = typer.Option(None, help="Optional role id."),
) -> None:
    """List structured fact review actions."""

    service = build_fact_review_service()
    actions = service.list_actions(thread_id=thread_id, fact_id=fact_id, role_id=role_id)
    if not actions:
        console.print("[yellow]No fact review actions saved yet.[/yellow]")
        return

    render_fact_review_action_list(actions)


@fact_review_actions_app.command("add")
def add_fact_review_action(
    thread_id: str = typer.Option(..., help="Existing fact review thread id."),
    action_type: FactReviewActionType = typer.Option(
        ...,
        help=(
            "Action type: activate_fact, reject_fact, revise_fact, "
            "add_evidence, or propose_constraint."
        ),
    ),
    rationale: str | None = typer.Option(None, help="Rationale for the proposed action."),
    source_message_ids: list[str] = typer.Option(
        [],
        "--source-message-id",
        help="Fact review message id that caused this action. Can be provided more than once.",
    ),
    revised_text: str | None = typer.Option(
        None,
        help="Required replacement fact text for revise_fact actions.",
    ),
    source_ids: list[str] = typer.Option(
        [],
        "--source-id",
        help="Role source id to add or preserve. Can be provided more than once.",
    ),
    question_ids: list[str] = typer.Option(
        [],
        "--question-id",
        help="Clarification question id to add as evidence. Can be provided more than once.",
    ),
    message_ids: list[str] = typer.Option(
        [],
        "--message-id",
        help="Clarification message id to add as evidence. Can be provided more than once.",
    ),
    constraint_scope_type: ConstraintScopeType | None = typer.Option(
        None,
        help="Required scope type for propose_constraint actions.",
    ),
    constraint_scope_id: str | None = typer.Option(
        None,
        help="Scope id for role and fact propose_constraint actions.",
    ),
    constraint_type: ConstraintType | None = typer.Option(
        None,
        help="Required constraint type for propose_constraint actions.",
    ),
    rule_text: str | None = typer.Option(
        None,
        help="Required rule or preference text for propose_constraint actions.",
    ),
) -> None:
    """Add a structured action proposal to a fact review thread."""

    service = build_fact_review_service()
    try:
        action = service.add_action(
            thread_id=thread_id,
            action_type=action_type,
            rationale=rationale,
            source_message_ids=source_message_ids,
            revised_text=revised_text,
            source_ids=source_ids,
            question_ids=question_ids,
            message_ids=message_ids,
            constraint_scope_type=constraint_scope_type,
            constraint_scope_id=constraint_scope_id,
            constraint_type=constraint_type,
            rule_text=rule_text,
        )
    except FactReviewThreadNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not save fact review action.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Saved fact review action.[/green]")
    console.print(f"Action ID: {action.id}")


@fact_review_actions_app.command("apply")
def apply_fact_review_action(
    action_id: str = typer.Argument(..., help="Fact review action identifier."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.SYSTEM,
        help="Workflow actor recorded for the change event.",
    ),
) -> None:
    """Apply one proposed fact review action through deterministic services."""

    service = build_fact_review_service()
    try:
        action = service.apply_action(action_id, actor=actor)
    except (
        EvidenceReferenceRemovalError,
        FactReviewActionNotFoundError,
        FactNotFoundError,
        FactRevisionNotAllowedError,
        InvalidFactReviewActionStatusTransitionError,
        InvalidFactStatusTransitionError,
        RoleNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
        ValidationError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Applied fact review action.[/green]")
    console.print(f"Action ID: {action.id}")
    if action.applied_fact_id is not None:
        console.print(f"Applied Fact ID: {action.applied_fact_id}")
    if action.applied_constraint_id is not None:
        console.print(f"Applied Constraint ID: {action.applied_constraint_id}")


@fact_review_actions_app.command("reject")
def reject_fact_review_action(
    action_id: str = typer.Argument(..., help="Fact review action identifier."),
) -> None:
    """Reject one proposed fact review action."""

    service = build_fact_review_service()
    try:
        action = service.reject_action(action_id)
    except (
        FactReviewActionNotFoundError,
        InvalidFactReviewActionStatusTransitionError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Rejected fact review action.[/green]")
    console.print(f"Action ID: {action.id}")


@fact_review_actions_app.command("archive")
def archive_fact_review_action(
    action_id: str = typer.Argument(..., help="Fact review action identifier."),
) -> None:
    """Archive one fact review action."""

    service = build_fact_review_service()
    try:
        action = service.archive_action(action_id)
    except (
        FactReviewActionNotFoundError,
        InvalidFactReviewActionStatusTransitionError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Archived fact review action.[/green]")
    console.print(f"Action ID: {action.id}")


@experience_workflow_app.command("analyze-sources")
def analyze_experience_sources(
    role_id: str = typer.Option(..., help="Existing experience role id."),
) -> None:
    """Start source analysis for unanalyzed role sources."""

    try:
        service = build_experience_workflow_service()
        console.print(f"Question Generator: {service.question_generator_name}")
        run = service.analyze_sources(role_id)
    except (
        ActiveAnalysisRunExistsError,
        NoUnanalyzedSourcesError,
        RoleNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
        InvalidLLMOutputError,
        LLMClientError,
        LLMConfigurationError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not analyze role sources.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    questions = build_source_analysis_service().list_questions(run.id)
    console.print("[green]Started experience source analysis.[/green]")
    console.print(f"Run ID: {run.id}")
    console.print(f"Question IDs: {', '.join(question.id for question in questions)}")


@experience_workflow_app.command("generate-findings")
def generate_experience_findings(
    run_id: str = typer.Option(..., help="Existing source analysis run id."),
) -> None:
    """Generate source findings for a closed source analysis run."""

    try:
        service = build_experience_workflow_service()
        console.print(f"Finding Generator: {service.finding_generator_name}")
        findings = service.generate_findings(run_id)
    except (
        AnalysisRunNotFoundError,
        FactNotFoundError,
        FactRoleMismatchError,
        OpenClarificationQuestionsError,
        RoleNotFoundError,
        SourceFindingsAlreadyExistError,
        SourceNotFoundError,
        SourceNotInAnalysisRunError,
        SourceRoleMismatchError,
        InvalidLLMOutputError,
        LLMClientError,
        LLMConfigurationError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not generate source findings.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]Generated source findings.[/green]")
    console.print(f"Finding IDs: {', '.join(finding.id for finding in findings)}")


@experience_workflow_app.command("apply-findings")
def apply_experience_findings(
    run_id: str = typer.Option(..., help="Existing source analysis run id."),
    actor: FactChangeActor = typer.Option(
        FactChangeActor.SYSTEM,
        help="Workflow actor recorded for fact change events.",
    ),
) -> None:
    """Apply accepted source findings through deterministic fact workflows."""

    try:
        service = build_experience_workflow_service()
        results = service.apply_findings(run_id, actor=actor)
    except (
        AnalysisRunNotFoundError,
        EvidenceReferenceRemovalError,
        FactNotFoundError,
        FactRevisionNotAllowedError,
        FactRoleMismatchError,
        InvalidFactStatusTransitionError,
        InvalidSourceFindingStatusTransitionError,
        RoleNotFoundError,
        SourceFindingNotFoundError,
        SourceNotFoundError,
        SourceRoleMismatchError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except ValidationError as exc:
        console.print("[red]Could not apply source findings.[/red]")
        for error in exc.errors():
            console.print(f"[red]- {error['msg']}[/red]")
        raise typer.Exit(1) from exc

    if not results:
        console.print("[yellow]No accepted source findings to apply.[/yellow]")
        return

    console.print("[green]Applied source findings.[/green]")
    render_applied_source_finding_results(results)


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


def build_experience_fact_service() -> ExperienceFactService:
    """Build the experience fact service from configured settings."""

    settings = get_settings()
    fact_repository = ExperienceFactRepository(settings.data_dir)
    role_repository = ExperienceRoleRepository(settings.data_dir)
    source_repository = RoleSourceRepository(settings.data_dir)
    return ExperienceFactService(fact_repository, role_repository, source_repository)


def build_scoped_constraint_service() -> ScopedConstraintService:
    """Build the scoped constraint service from configured settings."""

    settings = get_settings()
    constraint_repository = ScopedConstraintRepository(settings.data_dir)
    role_repository = ExperienceRoleRepository(settings.data_dir)
    fact_repository = ExperienceFactRepository(settings.data_dir)
    return ScopedConstraintService(
        constraint_repository,
        role_repository,
        fact_repository,
    )


def build_source_analysis_service() -> SourceAnalysisService:
    """Build the source analysis service from configured settings."""

    settings = get_settings()
    analysis_repository = SourceAnalysisRepository(settings.data_dir)
    role_repository = ExperienceRoleRepository(settings.data_dir)
    source_repository = RoleSourceRepository(settings.data_dir)
    fact_repository = ExperienceFactRepository(settings.data_dir)
    return SourceAnalysisService(
        analysis_repository,
        role_repository,
        source_repository,
        fact_repository,
    )


def build_fact_review_service() -> FactReviewService:
    """Build the fact review service from configured settings."""

    settings = get_settings()
    review_repository = FactReviewRepository(settings.data_dir)
    fact_service = build_experience_fact_service()
    constraint_service = build_scoped_constraint_service()
    return FactReviewService(review_repository, fact_service, constraint_service)


def build_experience_workflow_service() -> ExperienceWorkflowService:
    """Build the experience workflow service from configured settings."""

    settings = get_settings()
    role_service = build_experience_role_service()
    source_service = build_role_source_service()
    analysis_service = build_source_analysis_service()
    fact_service = build_experience_fact_service()
    question_generator = build_source_question_generator(settings)
    finding_generator = build_source_finding_generator(settings)
    return ExperienceWorkflowService(
        role_service,
        source_service,
        analysis_service,
        fact_service,
        question_generator=question_generator,
        finding_generator=finding_generator,
    )


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
    table.add_row("Role Focus", role.role_focus or "-")
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


def render_experience_fact_list(facts: list[ExperienceFact]) -> None:
    """Render experience facts as a compact CLI table."""

    table = Table(title="Experience Facts")
    table.add_column("ID", no_wrap=True)
    table.add_column("Role ID", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Preview")
    for fact in facts:
        table.add_row(
            fact.id,
            fact.role_id,
            fact.status.value,
            preview_source_text(fact.text),
        )
    console.print(table)


def render_experience_fact(fact: ExperienceFact) -> None:
    """Render one experience fact as a CLI table."""

    table = Table(title="Experience Fact")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", fact.id)
    table.add_row("Role ID", fact.role_id)
    table.add_row("Source IDs", ", ".join(fact.source_ids) or "-")
    table.add_row("Question IDs", ", ".join(fact.question_ids) or "-")
    table.add_row("Message IDs", ", ".join(fact.message_ids) or "-")
    table.add_row("Systems", ", ".join(fact.systems) or "-")
    table.add_row("Skills", ", ".join(fact.skills) or "-")
    table.add_row("Functions", ", ".join(fact.functions) or "-")
    table.add_row("Supersedes Fact ID", fact.supersedes_fact_id or "-")
    table.add_row("Superseded By Fact ID", fact.superseded_by_fact_id or "-")
    table.add_row("Status", fact.status.value)
    table.add_row("Created At", fact.created_at.isoformat())
    table.add_row("Updated At", fact.updated_at.isoformat())
    table.add_row("Text", fact.text)
    table.add_row("Details", "\n".join(fact.details) or "-")
    console.print(table)


def render_fact_change_event_list(events: list[FactChangeEvent]) -> None:
    """Render fact change events as a compact CLI table."""

    table = Table(title="Fact Change Events")
    table.add_column("ID", no_wrap=True)
    table.add_column("Fact ID", no_wrap=True)
    table.add_column("Role ID", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Actor", no_wrap=True)
    table.add_column("Status")
    table.add_column("Summary")
    for event in events:
        status_change = "-"
        if event.from_status is not None or event.to_status is not None:
            from_status = event.from_status.value if event.from_status is not None else "-"
            to_status = event.to_status.value if event.to_status is not None else "-"
            status_change = f"{from_status} -> {to_status}"
        table.add_row(
            event.id,
            event.fact_id,
            event.role_id,
            event.event_type.value,
            event.actor.value,
            status_change,
            event.summary or "-",
        )
    console.print(table)


def render_scoped_constraint_list(constraints: list[ScopedConstraint]) -> None:
    """Render scoped constraints as separated readable CLI blocks."""

    console.print("[bold]Scoped Constraints[/bold]")
    for index, constraint in enumerate(constraints, start=1):
        constraint_details = Table.grid(expand=True, padding=(0, 2))
        constraint_details.add_column(no_wrap=True, style="bold")
        constraint_details.add_column(ratio=1)
        constraint_details.add_row("Rule", constraint.rule_text)
        constraint_details.add_row("ID", constraint.id)
        constraint_details.add_row("Scope", constraint.scope_type.value)
        constraint_details.add_row("Scope ID", constraint.scope_id or "-")
        constraint_details.add_row("Type", constraint.constraint_type.value)
        constraint_details.add_row("Status", constraint.status.value)
        constraint_details.add_row(
            "Source Message IDs",
            ", ".join(constraint.source_message_ids) or "-",
        )
        console.print(
            Panel(
                constraint_details,
                title=f"Constraint {index}",
                expand=True,
            )
        )


def render_source_analysis_run_list(runs: list[SourceAnalysisRun]) -> None:
    """Render source analysis runs as a compact CLI table."""

    table = Table(title="Source Analysis Runs")
    table.add_column("ID", no_wrap=True)
    table.add_column("Role ID", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Source IDs")
    for run in runs:
        table.add_row(
            run.id,
            run.role_id,
            run.status.value,
            ", ".join(run.source_ids),
        )
    console.print(table)


def render_source_clarification_question_list(
    questions: list[SourceClarificationQuestion],
) -> None:
    """Render clarification questions as separated readable CLI blocks."""

    console.print("[bold]Source Clarification Questions[/bold]")
    for index, question in enumerate(questions, start=1):
        question_details = Table.grid(expand=True, padding=(0, 2))
        question_details.add_column(no_wrap=True, style="bold")
        question_details.add_column(ratio=1)
        relevant_source_ids = "\n".join(question.relevant_source_ids) or "-"
        question_details.add_row("Question", question.question_text)
        question_details.add_row("ID", question.id)
        question_details.add_row("Run ID", question.analysis_run_id)
        question_details.add_row("Status", question.status.value)
        question_details.add_row(
            "Relevant Source IDs",
            Text(relevant_source_ids, no_wrap=True, overflow="crop"),
        )
        console.print(Panel(question_details, title=f"Question {index}", expand=True))


def render_source_clarification_message_list(
    messages: list[SourceClarificationMessage],
) -> None:
    """Render clarification messages as separated readable CLI blocks."""

    console.print("[bold]Source Clarification Messages[/bold]")
    for index, message in enumerate(messages, start=1):
        message_details = Table.grid(expand=True, padding=(0, 2))
        message_details.add_column(no_wrap=True, style="bold")
        message_details.add_column(ratio=1)
        message_details.add_row("Message", message.message_text)
        message_details.add_row("ID", message.id)
        message_details.add_row("Question ID", message.question_id)
        message_details.add_row("Author", message.author.value)
        console.print(
            Panel(
                message_details,
                title=f"Message {index}",
                expand=True,
            )
        )


def render_source_finding_list(findings: list[SourceFinding]) -> None:
    """Render source findings as separated readable CLI blocks."""

    console.print("[bold]Source Findings[/bold]")
    for index, finding in enumerate(findings, start=1):
        finding_details = Table.grid(expand=True, padding=(0, 2))
        finding_details.add_column(no_wrap=True, style="bold")
        finding_details.add_column(ratio=1)
        finding_details.add_row("Type", finding.finding_type.value)
        finding_details.add_row("Status", finding.status.value)
        finding_details.add_row("ID", finding.id)
        finding_details.add_row("Run ID", finding.analysis_run_id)
        finding_details.add_row("Role ID", finding.role_id)
        finding_details.add_row("Source ID", finding.source_id)
        finding_details.add_row("Fact ID", finding.fact_id or "-")
        finding_details.add_row("Applied Fact ID", finding.applied_fact_id or "-")
        finding_details.add_row("Proposed Fact", finding.proposed_fact_text or "-")
        finding_details.add_row("Rationale", finding.rationale or "-")
        console.print(
            Panel(
                finding_details,
                title=f"Finding {index}",
                expand=True,
            )
        )


def render_fact_review_thread_list(threads: list[FactReviewThread]) -> None:
    """Render fact review threads as a CLI table."""

    table = Table(title="Fact Review Threads")
    table.add_column("ID")
    table.add_column("Fact ID")
    table.add_column("Role ID")
    table.add_column("Status")
    table.add_column("Updated")
    for thread in threads:
        table.add_row(
            thread.id,
            thread.fact_id,
            thread.role_id,
            thread.status.value,
            thread.updated_at.isoformat(),
        )
    console.print(table)


def render_fact_review_message_list(messages: list[FactReviewMessage]) -> None:
    """Render fact review messages as separated readable CLI blocks."""

    console.print("[bold]Fact Review Messages[/bold]")
    for index, message in enumerate(messages, start=1):
        message_details = Table.grid(expand=True, padding=(0, 2))
        message_details.add_column(no_wrap=True, style="bold")
        message_details.add_column(ratio=1)
        message_details.add_row("Message", message.message_text)
        message_details.add_row("ID", message.id)
        message_details.add_row("Thread ID", message.thread_id)
        message_details.add_row("Author", message.author.value)
        message_details.add_row("Recommended Action", message.recommended_action.value)
        console.print(
            Panel(
                message_details,
                title=f"Message {index}",
                expand=True,
            )
        )


def render_fact_review_action_list(actions: list[FactReviewAction]) -> None:
    """Render fact review actions as separated readable CLI blocks."""

    console.print("[bold]Fact Review Actions[/bold]")
    for index, action in enumerate(actions, start=1):
        action_details = Table.grid(expand=True, padding=(0, 2))
        action_details.add_column(no_wrap=True, style="bold")
        action_details.add_column(ratio=1)
        action_details.add_row("Type", action.action_type.value)
        action_details.add_row("Status", action.status.value)
        action_details.add_row("ID", action.id)
        action_details.add_row("Thread ID", action.thread_id)
        action_details.add_row("Fact ID", action.fact_id)
        action_details.add_row("Role ID", action.role_id)
        action_details.add_row("Applied Fact ID", action.applied_fact_id or "-")
        action_details.add_row("Applied Constraint ID", action.applied_constraint_id or "-")
        action_details.add_row("Rationale", action.rationale or "-")
        action_details.add_row("Review Message IDs", ", ".join(action.source_message_ids) or "-")
        action_details.add_row("Source IDs", ", ".join(action.source_ids) or "-")
        action_details.add_row("Question IDs", ", ".join(action.question_ids) or "-")
        action_details.add_row("Message IDs", ", ".join(action.message_ids) or "-")
        action_details.add_row("Revised Text", action.revised_text or "-")
        action_details.add_row(
            "Constraint Scope",
            action.constraint_scope_type.value if action.constraint_scope_type else "-",
        )
        action_details.add_row("Constraint Scope ID", action.constraint_scope_id or "-")
        action_details.add_row(
            "Constraint Type",
            action.constraint_type.value if action.constraint_type else "-",
        )
        action_details.add_row("Rule Text", action.rule_text or "-")
        console.print(
            Panel(
                action_details,
                title=f"Action {index}",
                expand=True,
            )
        )


def render_applied_source_finding_results(results: list[AppliedSourceFindingResult]) -> None:
    """Render source finding application results."""

    table = Table(title="Applied Source Findings")
    table.add_column("Finding ID")
    table.add_column("Type")
    table.add_column("Action")
    table.add_column("Fact ID")
    table.add_column("Message")
    for result in results:
        table.add_row(
            result.finding_id,
            result.finding_type.value,
            result.action.value,
            result.fact_id or "-",
            result.message or "-",
        )
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
app.add_typer(facts_app, name="facts")
app.add_typer(constraints_app, name="constraints")
app.add_typer(fact_review_app, name="fact-review")
app.add_typer(experience_workflow_app, name="experience-workflow")
source_analysis_app.add_typer(analysis_runs_app, name="runs")
source_analysis_app.add_typer(analysis_questions_app, name="questions")
source_analysis_app.add_typer(analysis_messages_app, name="messages")
source_analysis_app.add_typer(analysis_findings_app, name="findings")
app.add_typer(source_analysis_app, name="source-analysis")
fact_review_app.add_typer(fact_review_threads_app, name="threads")
fact_review_app.add_typer(fact_review_messages_app, name="messages")
fact_review_app.add_typer(fact_review_actions_app, name="actions")


def main() -> None:
    """Run the Career Agent CLI."""

    app()


if __name__ == "__main__":
    main()
