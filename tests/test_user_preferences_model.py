import pytest
from pydantic import ValidationError

from career_agent.user_preferences.models import (
    CommuteDistanceUnit,
    UserPreferences,
    WorkArrangement,
)


def build_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        time_zone="America/Chicago",
        target_job_titles=["Senior Systems Analyst", "Platform Engineer"],
        preferred_locations=["Chicago, IL"],
        preferred_work_arrangements=[WorkArrangement.REMOTE, WorkArrangement.HYBRID],
        desired_salary_min=150000,
        salary_currency="USD",
        max_commute_distance=35,
        commute_distance_unit=CommuteDistanceUnit.MILES,
        max_commute_time=45,
        work_authorization=True,
        requires_work_sponsorship=False,
    )


def test_user_preferences_json_round_trip() -> None:
    preferences = build_preferences()

    restored = UserPreferences.model_validate_json(preferences.model_dump_json())

    assert restored == preferences


def test_user_preferences_normalizes_text_fields() -> None:
    preferences = UserPreferences(
        full_name="  Randy Example  ",
        base_location="  Aurora, IL 60504  ",
        time_zone="   ",
        target_job_titles=["  Senior Systems Analyst  ", "  "],
        preferred_locations=["  Chicago, IL  ", ""],
        preferred_work_arrangements=["remote"],
        salary_currency=" usd ",
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    assert preferences.full_name == "Randy Example"
    assert preferences.base_location == "Aurora, IL 60504"
    assert preferences.time_zone is None
    assert preferences.target_job_titles == ["Senior Systems Analyst"]
    assert preferences.preferred_locations == ["Chicago, IL"]
    assert preferences.preferred_work_arrangements == [WorkArrangement.REMOTE]
    assert preferences.salary_currency == "USD"


def test_user_preferences_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            work_authorization=True,
            requires_work_sponsorship=False,
        )

    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            work_authorization=True,
            requires_work_sponsorship=False,
        )


def test_user_preferences_requires_work_arrangement() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[],
            work_authorization=True,
            requires_work_sponsorship=False,
        )


def test_user_preferences_rejects_invalid_time_zone() -> None:
    with pytest.raises(ValidationError, match="valid IANA"):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            time_zone="Not/A_Zone",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            work_authorization=True,
            requires_work_sponsorship=False,
        )


def test_user_preferences_rejects_negative_numbers() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            desired_salary_min=-1,
            work_authorization=True,
            requires_work_sponsorship=False,
        )

    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            max_commute_distance=-1,
            work_authorization=True,
            requires_work_sponsorship=False,
        )

    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            max_commute_time=-1,
            work_authorization=True,
            requires_work_sponsorship=False,
        )


def test_user_preferences_rejects_invalid_salary_currency() -> None:
    with pytest.raises(ValidationError, match="salary_currency"):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            preferred_work_arrangements=[WorkArrangement.REMOTE],
            salary_currency="US1",
            work_authorization=True,
            requires_work_sponsorship=False,
        )
