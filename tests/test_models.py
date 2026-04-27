import pytest
from pydantic import ValidationError

from career_agent.domain.models import (
    CareerProfile,
    CommuteDistanceUnit,
    EmploymentType,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    IntakeAnswer,
    IntakeMessage,
    IntakeMessageRole,
    IntakeQuestion,
    UserPreferences,
    WorkArrangement,
    YearMonth,
)


def test_user_preferences_json_round_trip() -> None:
    preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer", "Machine Learning Engineer"],
        preferred_locations=["Chicago, IL"],
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
    assert experience.id
    assert experience.start_date == YearMonth(year=2021, month=5)


def test_employment_type_values_are_stable() -> None:
    assert [value.value for value in EmploymentType] == [
        "full-time",
        "part-time",
        "contract",
        "consulting",
        "internship",
        "other",
    ]


def test_experience_entry_accepts_legacy_experience_id_input() -> None:
    experience = ExperienceEntry(
        experience_id="exp-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )

    assert experience.id == "exp-123"


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


def test_career_profile_rejects_duplicate_experience_entry_ids() -> None:
    experience = ExperienceEntry(
        id="exp-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )

    with pytest.raises(ValidationError):
        CareerProfile(
            experience_entries=[
                experience,
                ExperienceEntry(
                    id="exp-123",
                    employer_name="Beta Insights",
                    job_title="Lead Data Engineer",
                ),
            ]
        )


def test_experience_intake_session_json_round_trip() -> None:
    question = IntakeQuestion(
        id="question-1",
        question="What business outcome did this work support?",
        rationale="Business impact helps convert duties into accomplishments.",
    )
    answer = IntakeAnswer(
        question_id=question.id,
        answer="It reduced repeated manual reporting work for finance analysts.",
    )
    draft_entry = ExperienceEntry(
        id="exp-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["Reduced manual reporting effort for finance analysts."],
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.ACCEPTED,
        source_text="- Built reporting pipeline",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        location="Chicago, IL",
        employment_type="full-time",
        start_date="05/2021",
        is_current_role=True,
        transcript=[
            IntakeMessage(
                role=IntakeMessageRole.USER,
                content="I built a reporting pipeline.",
            ),
            IntakeMessage(
                role=IntakeMessageRole.ASSISTANT,
                content="What outcome did that create?",
            ),
        ],
        follow_up_questions=[question],
        user_answers=[answer],
        draft_experience_entry=draft_entry,
        accepted_experience_entry_id=draft_entry.id,
    )

    payload = session.model_dump_json()
    restored = ExperienceIntakeSession.model_validate_json(payload)

    assert restored == session
    assert restored.status == ExperienceIntakeStatus.ACCEPTED
    assert restored.draft_experience_entry is not None
    assert restored.accepted_experience_entry_id == restored.draft_experience_entry.id
    assert restored.start_date == YearMonth(year=2021, month=5)
    assert restored.end_date is None
    assert restored.is_current_role is True


def test_experience_intake_session_defaults_to_draft_with_timestamps() -> None:
    session = ExperienceIntakeSession()

    assert session.status == ExperienceIntakeStatus.DRAFT
    assert session.created_at.tzinfo is not None
    assert session.updated_at.tzinfo is not None


def test_experience_intake_session_requires_acceptance_id_when_accepted() -> None:
    with pytest.raises(ValidationError):
        ExperienceIntakeSession(status=ExperienceIntakeStatus.ACCEPTED)


def test_experience_intake_session_rejects_mismatched_acceptance_id() -> None:
    with pytest.raises(ValidationError):
        ExperienceIntakeSession(
            status=ExperienceIntakeStatus.ACCEPTED,
            draft_experience_entry=ExperienceEntry(
                id="exp-123",
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
            ),
            accepted_experience_entry_id="different-id",
        )


def test_experience_intake_session_rejects_invalid_role_dates() -> None:
    with pytest.raises(ValidationError):
        ExperienceIntakeSession(start_date="06/2024", end_date="05/2021")

    with pytest.raises(ValidationError):
        ExperienceIntakeSession(
            start_date="05/2021",
            end_date="06/2024",
            is_current_role=True,
        )


def test_experience_intake_session_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        ExperienceIntakeSession(created_at="2026-01-01T00:00:00")
