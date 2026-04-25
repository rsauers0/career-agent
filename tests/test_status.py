from __future__ import annotations

from career_agent.application.status import (
    ComponentStatusState,
    evaluate_user_preferences_status,
)
from career_agent.domain.models import CommuteDistanceUnit, UserPreferences, WorkArrangement


def build_complete_user_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Chicago, IL"],
        time_zone="America/Chicago",
        preferred_work_arrangements=[WorkArrangement.HYBRID],
        desired_salary_min=150000,
        max_commute_distance=35,
        commute_distance_unit=CommuteDistanceUnit.MILES,
        max_commute_time=50,
        work_authorization=True,
        requires_work_sponsorship=False,
    )


def test_user_preferences_status_not_started_when_missing() -> None:
    status = evaluate_user_preferences_status(None)

    assert status.state == ComponentStatusState.NOT_STARTED
    assert status.missing_required == [
        "full_name",
        "base_location",
        "preferred_work_arrangements",
    ]
    assert status.missing_recommended == []


def test_user_preferences_status_incomplete_when_required_fields_missing() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[],
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    status = evaluate_user_preferences_status(preferences)

    assert status.state == ComponentStatusState.INCOMPLETE
    assert status.missing_required == ["preferred_work_arrangements"]
    assert status.missing_recommended == []


def test_user_preferences_status_partial_when_recommended_fields_missing() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    status = evaluate_user_preferences_status(preferences)

    assert status.state == ComponentStatusState.PARTIAL
    assert status.missing_required == []
    assert status.missing_recommended == [
        "target_job_titles",
        "preferred_locations",
        "time_zone",
        "desired_salary_min",
    ]


def test_user_preferences_status_recommends_commute_fields_for_hybrid_or_onsite() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Chicago, IL"],
        time_zone="America/Chicago",
        preferred_work_arrangements=[WorkArrangement.HYBRID],
        desired_salary_min=150000,
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    status = evaluate_user_preferences_status(preferences)

    assert status.state == ComponentStatusState.PARTIAL
    assert status.missing_required == []
    assert status.missing_recommended == [
        "max_commute_distance",
        "max_commute_time",
    ]


def test_user_preferences_status_complete_when_required_and_recommended_fields_exist() -> None:
    status = evaluate_user_preferences_status(build_complete_user_preferences())

    assert status.state == ComponentStatusState.COMPLETE
    assert status.missing_required == []
    assert status.missing_recommended == []
