import pytest
from pydantic import ValidationError

from career_agent.experience_roles.models import (
    EmploymentType,
    ExperienceRole,
    ExperienceRoleStatus,
    YearMonth,
)


def test_year_month_accepts_common_string_formats() -> None:
    assert YearMonth.model_validate("05/2021") == YearMonth(year=2021, month=5)
    assert YearMonth.model_validate("May 2021") == YearMonth(year=2021, month=5)
    assert YearMonth.model_validate("May 2021").sort_key() == (2021, 5)


def test_year_month_rejects_invalid_string_format() -> None:
    with pytest.raises(ValidationError, match="YearMonth"):
        YearMonth.model_validate("2021")


def test_experience_role_json_round_trip() -> None:
    role = ExperienceRole(
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        location="Chicago, IL",
        employment_type=EmploymentType.FULL_TIME,
        role_focus="Led internal reporting and automation improvements.",
        start_date="05/2021",
        end_date="06/2024",
        status=ExperienceRoleStatus.REVIEW_REQUIRED,
    )

    restored = ExperienceRole.model_validate_json(role.model_dump_json())

    assert restored == role
    assert restored.id
    assert restored.role_focus == "Led internal reporting and automation improvements."
    assert restored.start_date == YearMonth(year=2021, month=5)
    assert restored.end_date == YearMonth(year=2024, month=6)


def test_experience_role_normalizes_text_fields() -> None:
    role = ExperienceRole(
        employer_name="  Acme Analytics  ",
        job_title="  Senior Systems Analyst  ",
        location="   ",
        role_focus="  Led internal reporting and automation improvements.  ",
        start_date="05/2021",
        is_current_role=True,
    )

    assert role.employer_name == "Acme Analytics"
    assert role.job_title == "Senior Systems Analyst"
    assert role.location is None
    assert role.role_focus == "Led internal reporting and automation improvements."


def test_experience_role_treats_blank_role_focus_as_unset() -> None:
    role = ExperienceRole(
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        role_focus="   ",
        start_date="05/2021",
        is_current_role=True,
    )

    assert role.role_focus is None


def test_experience_role_defaults_to_input_required() -> None:
    role = ExperienceRole(
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        is_current_role=True,
    )

    assert role.status == ExperienceRoleStatus.INPUT_REQUIRED
    assert role.created_at.tzinfo is not None
    assert role.updated_at.tzinfo is not None


def test_experience_role_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        ExperienceRole(
            employer_name="",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            is_current_role=True,
        )

    with pytest.raises(ValidationError):
        ExperienceRole(
            employer_name="Acme Analytics",
            job_title="",
            start_date="05/2021",
            is_current_role=True,
        )


def test_experience_role_requires_end_date_for_past_role() -> None:
    with pytest.raises(ValidationError, match="end_date is required"):
        ExperienceRole(
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
        )


def test_experience_role_current_role_rejects_end_date() -> None:
    with pytest.raises(ValidationError, match="end_date must be empty"):
        ExperienceRole(
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            end_date="06/2024",
            is_current_role=True,
        )


def test_experience_role_rejects_end_date_before_start_date() -> None:
    with pytest.raises(ValidationError, match="end_date cannot be earlier"):
        ExperienceRole(
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="06/2024",
            end_date="05/2021",
        )


def test_experience_role_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ExperienceRole(
            employer_name="Acme Analytics",
            job_title="Senior Systems Analyst",
            start_date="05/2021",
            is_current_role=True,
            created_at="2026-01-01T00:00:00",
        )
