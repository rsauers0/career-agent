from __future__ import annotations

from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState

DASHBOARD_PLACEHOLDER_COMPONENTS = (
    "career_profile",
    "experience",
    "jobs",
    "documents",
)


def build_dashboard_statuses(profile_service: ProfileService) -> list[ComponentStatus]:
    """Return component statuses for the application landing dashboard."""

    return [
        profile_service.get_user_preferences_status(),
        *[
            ComponentStatus(component=component, state=ComponentStatusState.NOT_STARTED)
            for component in DASHBOARD_PLACEHOLDER_COMPONENTS
        ],
    ]
