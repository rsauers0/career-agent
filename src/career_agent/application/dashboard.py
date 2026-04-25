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
    detail: str


@dataclass(frozen=True)
class DashboardSection:
    """A named dashboard section containing related workflow statuses."""

    title: str
    items: list[ComponentStatus | JobWorkflowStatus] = field(default_factory=list)


def build_dashboard_sections(profile_service: ProfileService) -> list[DashboardSection]:
    """Return grouped statuses for the application landing dashboard."""

    return [
        DashboardSection(
            title="Profile Readiness",
            items=[
                profile_service.get_user_preferences_status(),
                ComponentStatus(
                    component="career_profile",
                    state=ComponentStatusState.NOT_STARTED,
                ),
            ],
        ),
        DashboardSection(
            title="Job Workflow",
            items=[
                JobWorkflowStatus(
                    component="jobs",
                    state=JobWorkflowState.IDLE,
                    detail="No job URLs queued for analysis.",
                ),
            ],
        ),
    ]
