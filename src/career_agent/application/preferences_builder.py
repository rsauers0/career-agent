from __future__ import annotations

from dataclasses import dataclass

from career_agent.domain.models import (
    CommuteDistanceUnit,
    UserPreferences,
    WorkArrangement,
    validate_iana_time_zone,
)


@dataclass
class PreferenceWizardAnswers:
    """Raw string and boolean answers collected by the preferences wizard."""

    full_name: str
    base_location: str
    time_zone: str
    target_job_titles: str
    preferred_locations: str
    preferred_work_arrangements: str
    desired_salary_min: str
    salary_currency: str
    max_commute_distance: str
    commute_distance_unit: str
    max_commute_time: str
    work_authorization: bool
    requires_work_sponsorship: bool


def build_user_preferences_from_answers(answers: PreferenceWizardAnswers) -> UserPreferences:
    """Normalize raw wizard answers into a validated `UserPreferences` model."""

    return UserPreferences(
        full_name=answers.full_name.strip(),
        base_location=answers.base_location.strip(),
        time_zone=parse_time_zone(answers.time_zone),
        target_job_titles=_parse_list(answers.target_job_titles),
        preferred_locations=_parse_list(answers.preferred_locations),
        preferred_work_arrangements=parse_work_arrangements(answers.preferred_work_arrangements),
        desired_salary_min=parse_optional_int(answers.desired_salary_min),
        salary_currency=answers.salary_currency.strip().upper(),
        max_commute_distance=parse_optional_int(answers.max_commute_distance),
        commute_distance_unit=parse_commute_distance_unit(answers.commute_distance_unit),
        max_commute_time=parse_optional_int(answers.max_commute_time),
        work_authorization=answers.work_authorization,
        requires_work_sponsorship=answers.requires_work_sponsorship,
    )


def parse_time_zone(value: str) -> str | None:
    """Normalize and validate a time zone string."""

    return validate_iana_time_zone(_parse_optional_text(value))


def _parse_optional_text(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_optional_int(value: str) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    return int(normalized)


def parse_work_arrangements(value: str) -> list[WorkArrangement]:
    arrangements: list[WorkArrangement] = []
    for item in _parse_list(value):
        try:
            arrangements.append(WorkArrangement(item.lower()))
        except ValueError as exc:
            msg = f"Unsupported work arrangement: {item}."
            raise ValueError(msg) from exc
    return arrangements


def parse_commute_distance_unit(value: str) -> CommuteDistanceUnit:
    normalized = value.strip().lower()
    try:
        return CommuteDistanceUnit(normalized)
    except ValueError as exc:
        msg = f"Unsupported commute distance unit: {value}."
        raise ValueError(msg) from exc
