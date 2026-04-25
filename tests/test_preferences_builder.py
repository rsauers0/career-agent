from __future__ import annotations

import pytest

from career_agent.application.preferences_builder import (
    PreferenceWizardAnswers,
    build_user_preferences_from_answers,
)
from career_agent.domain.models import CommuteDistanceUnit, WorkArrangement


def test_build_user_preferences_from_answers_normalizes_lists_and_enums() -> None:
    answers = PreferenceWizardAnswers(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        time_zone="America/Chicago",
        target_job_titles="Senior Data Engineer, Analytics Engineer",
        preferred_locations="Chicago, IL",
        preferred_work_arrangements="remote, hybrid",
        desired_salary_min="150000",
        salary_currency="usd",
        max_commute_distance="35",
        commute_distance_unit="miles",
        max_commute_time="50",
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    preferences = build_user_preferences_from_answers(answers)

    assert preferences.target_job_titles == [
        "Senior Data Engineer",
        "Analytics Engineer",
    ]
    assert preferences.preferred_work_arrangements == [
        WorkArrangement.REMOTE,
        WorkArrangement.HYBRID,
    ]
    assert preferences.salary_currency == "USD"
    assert preferences.max_commute_distance == 35
    assert preferences.commute_distance_unit == CommuteDistanceUnit.MILES


def test_build_user_preferences_from_answers_supports_blank_optional_values() -> None:
    answers = PreferenceWizardAnswers(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        time_zone="",
        target_job_titles="",
        preferred_locations="",
        preferred_work_arrangements="",
        desired_salary_min="",
        salary_currency="USD",
        max_commute_distance="",
        commute_distance_unit="kilometers",
        max_commute_time="",
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    preferences = build_user_preferences_from_answers(answers)

    assert preferences.time_zone is None
    assert preferences.target_job_titles == []
    assert preferences.preferred_locations == []
    assert preferences.preferred_work_arrangements == []
    assert preferences.desired_salary_min is None
    assert preferences.max_commute_distance is None
    assert preferences.max_commute_time is None


def test_build_user_preferences_from_answers_rejects_invalid_work_arrangement() -> None:
    answers = PreferenceWizardAnswers(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        time_zone="America/Chicago",
        target_job_titles="Senior Data Engineer",
        preferred_locations="Chicago, IL",
        preferred_work_arrangements="remote, spaceship",
        desired_salary_min="",
        salary_currency="USD",
        max_commute_distance="",
        commute_distance_unit="miles",
        max_commute_time="",
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    with pytest.raises(ValueError):
        build_user_preferences_from_answers(answers)


def test_parse_time_zone_rejects_invalid_value() -> None:
    answers = PreferenceWizardAnswers(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        time_zone="Not/A_Real_Zone",
        target_job_titles="Senior Data Engineer",
        preferred_locations="Chicago, IL",
        preferred_work_arrangements="remote",
        desired_salary_min="",
        salary_currency="USD",
        max_commute_distance="",
        commute_distance_unit="miles",
        max_commute_time="",
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    with pytest.raises(ValueError):
        build_user_preferences_from_answers(answers)
