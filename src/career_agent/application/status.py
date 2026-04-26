from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from career_agent.domain.models import UserPreferences, WorkArrangement


class ComponentStatusState(StrEnum):
    """High-level workflow completeness states for dashboard-style displays."""

    NOT_STARTED = "not_started"
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    COMPLETE = "complete"


@dataclass(frozen=True)
class ComponentStatus:
    """Reusable status result for CLI, TUI, and future interface adapters."""

    component: str
    state: ComponentStatusState
    missing_required: list[str] = field(default_factory=list)
    missing_recommended: list[str] = field(default_factory=list)


USER_PREFERENCES_REQUIRED_FIELDS = (
    "full_name",
    "base_location",
    "preferred_work_arrangements",
)

USER_PREFERENCES_RECOMMENDED_FIELDS = (
    "target_job_titles",
    "work_authorization",
    "requires_work_sponsorship",
    "time_zone",
    "desired_salary_min",
)

USER_PREFERENCES_COMMUTE_RECOMMENDED_FIELDS = (
    "max_commute_distance",
    "max_commute_time",
)

USER_PREFERENCES_FIELD_LABELS = {
    "full_name": "Full Name",
    "base_location": "Base Location",
    "preferred_work_arrangements": "Preferred Work Arrangements",
    "target_job_titles": "Target Job Titles",
    "work_authorization": "Work Authorization",
    "requires_work_sponsorship": "Requires Work Sponsorship",
    "time_zone": "Time Zone",
    "desired_salary_min": "Minimum Salary Desired",
    "max_commute_distance": "Max Commute Distance",
    "max_commute_time": "Max Commute Time",
}


def evaluate_user_preferences_status(
    preferences: UserPreferences | None,
) -> ComponentStatus:
    """Return product-level completeness status for user preferences."""

    if preferences is None:
        return ComponentStatus(
            component="user_preferences",
            state=ComponentStatusState.NOT_STARTED,
            missing_required=list(USER_PREFERENCES_REQUIRED_FIELDS),
        )

    missing_required = _missing_fields(preferences, USER_PREFERENCES_REQUIRED_FIELDS)
    if missing_required:
        return ComponentStatus(
            component="user_preferences",
            state=ComponentStatusState.INCOMPLETE,
            missing_required=missing_required,
        )

    recommended_fields = list(USER_PREFERENCES_RECOMMENDED_FIELDS)
    if _needs_commute_preferences(preferences):
        recommended_fields.extend(USER_PREFERENCES_COMMUTE_RECOMMENDED_FIELDS)

    missing_recommended = _missing_fields(preferences, recommended_fields)
    if missing_recommended:
        return ComponentStatus(
            component="user_preferences",
            state=ComponentStatusState.PARTIAL,
            missing_recommended=missing_recommended,
        )

    return ComponentStatus(
        component="user_preferences",
        state=ComponentStatusState.COMPLETE,
    )


def _missing_fields(model: UserPreferences, field_names: list[str] | tuple[str, ...]) -> list[str]:
    return [field_name for field_name in field_names if not _has_value(getattr(model, field_name))]


def format_status_field_names(field_names: list[str]) -> list[str]:
    """Return user-facing labels for status field identifiers."""

    return [USER_PREFERENCES_FIELD_LABELS.get(field_name, field_name) for field_name in field_names]


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return True


def _needs_commute_preferences(preferences: UserPreferences) -> bool:
    return any(
        arrangement in preferences.preferred_work_arrangements
        for arrangement in (WorkArrangement.HYBRID, WorkArrangement.ONSITE)
    )
