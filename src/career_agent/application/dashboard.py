from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState


class JobWorkflowState(StrEnum):
    """Runtime-oriented status states for job processing workflows."""

    IDLE = "idle"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class JobWorkflowStatus:
    """Current runtime state for the job workflow."""

    component: str
    state: JobWorkflowState


DashboardStatus = ComponentStatus | JobWorkflowStatus


@dataclass(frozen=True)
class DashboardCard:
    """Display metadata for one dashboard card."""

    title: str
    status: DashboardStatus
    detail: str
    shortcut: str | None = None


@dataclass(frozen=True)
class DashboardSection:
    """A named dashboard section containing related workflow statuses."""

    title: str
    cards: list[DashboardCard] = field(default_factory=list)


def build_dashboard_sections(profile_service: ProfileService) -> list[DashboardSection]:
    """Return grouped statuses for the application landing dashboard."""

    user_preferences_status = profile_service.get_user_preferences_status()

    return [
        DashboardSection(
            title="Profile Readiness",
            cards=[
                DashboardCard(
                    title="User Preferences",
                    status=user_preferences_status,
                    detail=_user_preferences_detail(user_preferences_status),
                    shortcut="p",
                ),
                DashboardCard(
                    title="Career Profile",
                    status=ComponentStatus(
                        component="career_profile",
                        state=ComponentStatusState.NOT_STARTED,
                    ),
                    detail="Career profile setup is not available yet.",
                ),
            ],
        ),
        DashboardSection(
            title="Job Workflow",
            cards=[
                DashboardCard(
                    title="Jobs",
                    status=JobWorkflowStatus(
                        component="jobs",
                        state=JobWorkflowState.IDLE,
                    ),
                    detail="No job URLs queued for analysis.",
                ),
            ],
        ),
    ]


def _user_preferences_detail(status: ComponentStatus) -> str:
    if status.state in (
        ComponentStatusState.NOT_STARTED,
        ComponentStatusState.INCOMPLETE,
        ComponentStatusState.PARTIAL,
    ):
        return "Press p to complete preferences setup."

    return "Press p to review or update preferences."
