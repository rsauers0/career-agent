import pytest
from pydantic import ValidationError

from career_agent.domain.models import (
    CareerProfile,
    CommuteDistanceUnit,
    ExperienceEntry,
    UserPreferences,
    WorkArrangement,
    YearMonth,
)


def test_user_preferences_json_round_trip() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer", "Machine Learning Engineer"],
        preferred_locations=["Remote", "Chicago, IL"],
        time_zone="America/Chicago",
        preferred_work_arrangements=[WorkArrangement.REMOTE, WorkArrangement.HYBRID],
        desired_salary_min=150000,
        salary_currency="USD",
        max_commute_distance=35,
        commute_distance_unit=CommuteDistanceUnit.MILES,
        max_commute_time=50,
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    payload = preferences.model_dump_json()
    restored = UserPreferences.model_validate_json(payload)

    assert restored == preferences


def test_user_preferences_reject_invalid_time_zone() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(
            full_name="Randy Example",
            base_location="Aurora, IL 60504",
            time_zone="Not/A_Real_Zone",
            work_authorization=True,
            requires_work_sponsorship=False,
        )


def test_experience_entry_json_round_trip() -> None:
    experience = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        location="Chicago, IL",
        employment_type="full-time",
        start_date="05/2021",
        role_summary="Led data platform development for analytics and reporting workloads.",
        responsibilities=[
            "Owned orchestration and reliability for core ETL pipelines.",
            "Partnered with analysts and business stakeholders on reporting requirements.",
        ],
        accomplishments=[
            "Reduced pipeline failures by redesigning retry and alerting patterns.",
        ],
        metrics=["Supported 40+ recurring reporting workflows."],
        systems_and_tools=["Python", "Airflow", "Snowflake", "dbt"],
        skills_demonstrated=["data engineering", "stakeholder communication"],
        domains=["retail analytics"],
        team_context="Worked on a 4-person data platform team.",
        scope_notes="Primary owner of the ingestion framework.",
        keywords=["etl", "analytics engineering"],
    )

    payload = experience.model_dump_json()
    restored = ExperienceEntry.model_validate_json(payload)

    assert restored == experience
    assert experience.start_date == YearMonth(year=2021, month=5)


def test_experience_entry_rejects_end_date_before_start_date() -> None:
    with pytest.raises(ValidationError):
        ExperienceEntry(
            employer_name="Acme Analytics",
            job_title="Senior Data Engineer",
            start_date="January 2022",
            end_date="12/2021",
        )


def test_experience_entry_current_role_rejects_end_date() -> None:
    with pytest.raises(ValidationError):
        ExperienceEntry(
            employer_name="Acme Analytics",
            job_title="Senior Data Engineer",
            start_date="2022-01",
            end_date="January 2024",
            is_current_role=True,
        )


def test_career_profile_json_round_trip() -> None:
    experience = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        start_date="05/2021",
        responsibilities=["Owned orchestration and reliability for core ETL pipelines."],
    )
    profile = CareerProfile(
        core_narrative_notes=[
            "Prefer to be positioned as a data platform and analytics engineering leader.",
            "Strengths include modernization, reliability, and stakeholder alignment.",
        ],
        experience_entries=[experience],
        education_entries=["B.S. in Computer Science, Example University"],
        certification_entries=["AWS Certified Data Analytics - Specialty"],
        skills=["data engineering", "analytics engineering", "technical leadership"],
        tools_and_technologies=["Python", "Snowflake", "dbt", "Airflow"],
        domains=["retail analytics", "data platforms"],
        notable_achievements=["Led modernization of reporting pipelines used across finance."],
        additional_notes=(
            "Open to emphasizing architecture or delivery leadership depending on target role."
        ),
    )

    payload = profile.model_dump_json()
    restored = CareerProfile.model_validate_json(payload)

    assert restored == profile


def test_career_profile_rejects_duplicate_experience_ids() -> None:
    experience = ExperienceEntry(
        experience_id="exp-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )

    with pytest.raises(ValidationError):
        CareerProfile(
            experience_entries=[
                experience,
                ExperienceEntry(
                    experience_id="exp-123",
                    employer_name="Beta Insights",
                    job_title="Lead Data Engineer",
                ),
            ]
        )
