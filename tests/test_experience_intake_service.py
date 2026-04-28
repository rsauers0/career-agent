from __future__ import annotations

import pytest

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import (
    CareerProfile,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    IntakeQuestion,
    YearMonth,
)


class FakeExperienceIntakeRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, ExperienceIntakeSession] = {}

    def load_session(self, session_id: str) -> ExperienceIntakeSession | None:
        return self.sessions.get(session_id)

    def save_session(self, session: ExperienceIntakeSession) -> None:
        self.sessions[session.id] = session

    def delete_session(self, session_id: str) -> bool:
        return self.sessions.pop(session_id, None) is not None

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        return list(self.sessions.values())

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        return [session for session in self.sessions.values() if session.status == status]


class FakeProfileRepository:
    def __init__(self) -> None:
        self.career_profile: CareerProfile | None = None
        self.preferences = None
        self.initialized = False

    def profile_storage_initialized(self) -> bool:
        return self.initialized

    def initialize_profile_storage(self) -> None:
        self.initialized = True

    def load_user_preferences(self):
        return self.preferences

    def save_user_preferences(self, preferences) -> None:
        self.preferences = preferences

    def load_career_profile(self) -> CareerProfile | None:
        return self.career_profile

    def save_career_profile(self, profile: CareerProfile) -> None:
        self.career_profile = profile


class FakeExperienceIntakeAssistant:
    def __init__(self, questions: list[IntakeQuestion] | None = None) -> None:
        if questions is None:
            questions = [
                IntakeQuestion(
                    question="What measurable impact did this work have?",
                    rationale="Impact helps turn duties into accomplishments.",
                )
            ]
        self.questions = questions
        self.received_session: ExperienceIntakeSession | None = None
        self.received_draft_session: ExperienceIntakeSession | None = None

    def generate_follow_up_questions(
        self,
        session: ExperienceIntakeSession,
    ) -> list[IntakeQuestion]:
        self.received_session = session
        return self.questions

    def draft_experience_entry(self, session: ExperienceIntakeSession) -> ExperienceEntry:
        self.received_draft_session = session
        return ExperienceEntry(
            employer_name=session.employer_name or "Wrong Employer",
            job_title=session.job_title or "Wrong Job",
            location="Wrong Location",
            employment_type="Wrong Type",
            start_date="01/2000",
            end_date="01/2001",
            role_summary="Built and improved reporting workflows.",
            accomplishments=["Reduced manual reporting time by 10 hours per week."],
            systems_and_tools=["Python"],
        )


def test_create_session_persists_draft_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)

    session = service.create_session()

    assert session.status == ExperienceIntakeStatus.DRAFT
    assert repository.load_session(session.id) == session


def test_get_session_returns_repository_value() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    assert service.get_session("session-123") == session


def test_list_sessions_returns_repository_values() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    assert service.list_sessions() == [session]


def test_list_sessions_by_status_returns_repository_values() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    draft = ExperienceIntakeSession(id="draft", status=ExperienceIntakeStatus.DRAFT)
    captured = ExperienceIntakeSession(
        id="captured",
        status=ExperienceIntakeStatus.SOURCE_CAPTURED,
    )
    repository.save_session(draft)
    repository.save_session(captured)

    assert service.list_sessions_by_status(ExperienceIntakeStatus.SOURCE_CAPTURED) == [captured]


def test_delete_session_removes_unlocked_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.SOURCE_CAPTURED,
        source_text="- Built reporting pipeline",
    )
    repository.save_session(session)

    service.delete_session("session-123")

    assert repository.load_session("session-123") is None


def test_delete_session_rejects_missing_session() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())

    with pytest.raises(ValueError, match="not found"):
        service.delete_session("missing")


def test_delete_session_rejects_locked_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.LOCKED,
        draft_experience_entry=draft,
        accepted_experience_entry_id="entry-123",
        locked_at="2026-01-01T00:00:00Z",
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="cannot be deleted"):
        service.delete_session("session-123")

    assert repository.load_session("session-123") == session


def test_capture_source_text_updates_existing_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    updated = service.capture_source_text("session-123", "  - Built reporting pipeline  ")

    assert updated.source_text == "- Built reporting pipeline"
    assert updated.status == ExperienceIntakeStatus.SOURCE_CAPTURED
    assert updated.updated_at > session.updated_at
    assert repository.load_session("session-123") == updated


def test_capture_source_text_can_append_to_existing_source_text() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        source_text="- Built reporting pipeline",
    )
    repository.save_session(session)

    updated = service.capture_source_text(
        "session-123",
        "- Added alerting",
        append=True,
    )

    assert updated.source_text == "- Built reporting pipeline\n\n- Added alerting"
    assert updated.status == ExperienceIntakeStatus.SOURCE_CAPTURED


def test_capture_source_text_append_without_existing_source_behaves_like_save() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    updated = service.capture_source_text(
        "session-123",
        "- Added alerting",
        append=True,
    )

    assert updated.source_text == "- Added alerting"


def test_capture_source_text_rejects_missing_session() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.capture_source_text("missing", "source text")


def test_capture_source_text_rejects_blank_source_text() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="source text is required"):
        service.capture_source_text("session-123", "   ")

    assert repository.load_session("session-123") == session


def test_capture_role_details_updates_existing_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    updated = service.capture_role_details(
        "session-123",
        employer_name="  Acme Analytics  ",
        job_title="  Senior Data Engineer  ",
        location="  Chicago, IL  ",
        employment_type="full-time",
        start_date="05/2021",
        end_date="06/2024",
    )

    assert updated.employer_name == "Acme Analytics"
    assert updated.job_title == "Senior Data Engineer"
    assert updated.location == "Chicago, IL"
    assert updated.employment_type == "full-time"
    assert updated.start_date == YearMonth(year=2021, month=5)
    assert updated.end_date == YearMonth(year=2024, month=6)
    assert updated.is_current_role is False
    assert updated.updated_at > session.updated_at
    assert repository.load_session("session-123") == updated


def test_capture_role_details_current_role_clears_end_date() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    updated = service.capture_role_details(
        "session-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        start_date="05/2021",
        end_date="06/2024",
        is_current_role=True,
    )

    assert updated.start_date == YearMonth(year=2021, month=5)
    assert updated.end_date is None
    assert updated.is_current_role is True


def test_capture_role_details_rejects_end_date_before_start_date() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="end_date cannot be earlier"):
        service.capture_role_details(
            "session-123",
            employer_name="Acme Analytics",
            job_title="Senior Data Engineer",
            start_date="06/2024",
            end_date="05/2021",
        )

    assert repository.load_session("session-123") == session


def test_capture_role_details_rejects_missing_session() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.capture_role_details(
            "missing",
            employer_name="Acme Analytics",
            job_title="Senior Data Engineer",
            start_date="05/2021",
        )


def test_capture_role_details_rejects_blank_values() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="employer name is required"):
        service.capture_role_details(
            "session-123",
            employer_name=" ",
            job_title="Senior Data Engineer",
            start_date="05/2021",
        )

    with pytest.raises(ValueError, match="job title is required"):
        service.capture_role_details(
            "session-123",
            employer_name="Acme Analytics",
            job_title=" ",
            start_date="05/2021",
        )

    assert repository.load_session("session-123") == session


def test_generate_follow_up_questions_updates_existing_session() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(repository, assistant)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.SOURCE_CAPTURED,
        source_text="- Built reporting pipeline",
    )
    repository.save_session(session)

    updated = service.generate_follow_up_questions("session-123")

    assert assistant.received_session == session
    assert updated.follow_up_questions == assistant.questions
    assert updated.status == ExperienceIntakeStatus.QUESTIONS_GENERATED
    assert updated.updated_at > session.updated_at
    assert repository.load_session("session-123") == updated


def test_generate_follow_up_questions_rejects_unconfigured_assistant() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)

    with pytest.raises(RuntimeError, match="assistant is not configured"):
        service.generate_follow_up_questions("session-123")


def test_generate_follow_up_questions_rejects_missing_session() -> None:
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(FakeExperienceIntakeRepository(), assistant)

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.generate_follow_up_questions("missing")


def test_generate_follow_up_questions_requires_captured_source_text() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(repository, assistant)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="source text must be captured"):
        service.generate_follow_up_questions("session-123")

    assert repository.load_session("session-123") == session


def test_generate_follow_up_questions_rejects_empty_assistant_response() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant(questions=[])
    service = ExperienceIntakeService(repository, assistant)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.SOURCE_CAPTURED,
        source_text="- Built reporting pipeline",
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="returned no follow-up questions"):
        service.generate_follow_up_questions("session-123")

    assert repository.load_session("session-123") == session


def test_capture_answers_updates_existing_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    question = IntakeQuestion(
        id="question-1",
        question="What measurable impact did this work have?",
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
        source_text="- Built reporting pipeline",
        follow_up_questions=[question],
    )
    repository.save_session(session)

    updated = service.capture_answers(
        "session-123",
        {"question-1": "Reduced manual reporting time by 10 hours per week."},
    )

    assert updated.status == ExperienceIntakeStatus.ANSWERS_CAPTURED
    assert updated.updated_at > session.updated_at
    assert len(updated.user_answers) == 1
    assert updated.user_answers[0].question_id == "question-1"
    assert updated.user_answers[0].answer == "Reduced manual reporting time by 10 hours per week."
    assert repository.load_session("session-123") == updated


def test_capture_answers_can_replace_existing_answers() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    question = IntakeQuestion(id="question-1", question="Who benefited?")
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
        follow_up_questions=[question],
    )
    repository.save_session(session)
    service.capture_answers("session-123", {"question-1": "Finance team."})

    updated = service.capture_answers("session-123", {"question-1": "Finance leadership."})

    assert updated.status == ExperienceIntakeStatus.ANSWERS_CAPTURED
    assert len(updated.user_answers) == 1
    assert updated.user_answers[0].answer == "Finance leadership."


def test_capture_answers_rejects_missing_session() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.capture_answers("missing", {"question-1": "Answer"})


def test_capture_answers_requires_generated_questions_status() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="questions must be generated"):
        service.capture_answers("session-123", {"question-1": "Answer"})

    assert repository.load_session("session-123") == session


def test_capture_answers_requires_existing_questions() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="follow-up questions are required"):
        service.capture_answers("session-123", {})

    assert repository.load_session("session-123") == session


def test_capture_answers_rejects_unknown_question_ids() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
        follow_up_questions=[IntakeQuestion(id="question-1", question="Who benefited?")],
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="Unknown follow-up question IDs"):
        service.capture_answers(
            "session-123",
            {
                "question-1": "Finance team.",
                "question-2": "Extra answer.",
            },
        )

    assert repository.load_session("session-123") == session


def test_capture_answers_rejects_missing_answers() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
        follow_up_questions=[
            IntakeQuestion(id="question-1", question="Who benefited?"),
            IntakeQuestion(id="question-2", question="What changed?"),
        ],
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="Missing answers"):
        service.capture_answers("session-123", {"question-1": "Finance team."})

    assert repository.load_session("session-123") == session


def test_capture_answers_rejects_blank_answers() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.QUESTIONS_GENERATED,
        follow_up_questions=[IntakeQuestion(id="question-1", question="Who benefited?")],
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="Answer cannot be blank"):
        service.capture_answers("session-123", {"question-1": "   "})

    assert repository.load_session("session-123") == session


def test_generate_draft_entry_updates_existing_session() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(repository, assistant)
    question = IntakeQuestion(id="question-1", question="What impact did this have?")
    repository.save_session(
        ExperienceIntakeSession(
            id="session-123",
            employer_name="Acme Analytics",
            job_title="Senior Data Engineer",
            start_date="05/2021",
            end_date="06/2024",
            source_text="- Built reporting pipeline",
            follow_up_questions=[question],
            user_answers=[
                {
                    "question_id": "question-1",
                    "answer": "Reduced manual reporting time by 10 hours per week.",
                }
            ],
            status=ExperienceIntakeStatus.ANSWERS_CAPTURED,
        )
    )

    updated = service.generate_draft_entry("session-123")

    assert assistant.received_draft_session is not None
    assert updated.status == ExperienceIntakeStatus.DRAFT_GENERATED
    assert updated.draft_experience_entry is not None
    assert updated.draft_experience_entry.employer_name == "Acme Analytics"
    assert updated.draft_experience_entry.job_title == "Senior Data Engineer"
    assert updated.draft_experience_entry.start_date == YearMonth(year=2021, month=5)
    assert updated.draft_experience_entry.end_date == YearMonth(year=2024, month=6)
    assert updated.draft_experience_entry.accomplishments == [
        "Reduced manual reporting time by 10 hours per week."
    ]
    assert repository.load_session("session-123") == updated


def test_generate_draft_entry_rejects_unconfigured_assistant() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)

    with pytest.raises(RuntimeError, match="assistant is not configured"):
        service.generate_draft_entry("session-123")


def test_generate_draft_entry_rejects_missing_session() -> None:
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(FakeExperienceIntakeRepository(), assistant)

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.generate_draft_entry("missing")


def test_generate_draft_entry_requires_answers_captured_status() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(repository, assistant)
    session = ExperienceIntakeSession(id="session-123")
    repository.save_session(session)

    with pytest.raises(ValueError, match="answers must be captured"):
        service.generate_draft_entry("session-123")

    assert repository.load_session("session-123") == session


def test_generate_draft_entry_requires_role_metadata() -> None:
    repository = FakeExperienceIntakeRepository()
    assistant = FakeExperienceIntakeAssistant()
    service = ExperienceIntakeService(repository, assistant)
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.ANSWERS_CAPTURED,
        source_text="- Built reporting pipeline",
        follow_up_questions=[IntakeQuestion(id="question-1", question="What changed?")],
        user_answers=[
            {
                "question_id": "question-1",
                "answer": "Reduced manual reporting time.",
            }
        ],
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="employer name is required"):
        service.generate_draft_entry("session-123")

    repository.save_session(session.model_copy(update={"employer_name": "Acme Analytics"}))
    with pytest.raises(ValueError, match="job title is required"):
        service.generate_draft_entry("session-123")

    repository.save_session(
        session.model_copy(
            update={
                "employer_name": "Acme Analytics",
                "job_title": "Senior Data Engineer",
            }
        )
    )
    with pytest.raises(ValueError, match="start date is required"):
        service.generate_draft_entry("session-123")

    repository.save_session(
        session.model_copy(
            update={
                "employer_name": "Acme Analytics",
                "job_title": "Senior Data Engineer",
                "start_date": YearMonth(year=2021, month=5),
            }
        )
    )
    with pytest.raises(ValueError, match="end date is required"):
        service.generate_draft_entry("session-123")


def test_update_draft_entry_updates_generated_draft() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    original_draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["Old accomplishment."],
    )
    edited_draft = ExperienceEntry(
        id="entry-999",
        employer_name="Wrong Employer",
        job_title="Wrong Job",
        role_summary="Built reporting automation for finance operations.",
        accomplishments=["Reduced manual reporting time by 10 hours per week."],
    )
    session = ExperienceIntakeSession(
        id="session-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        location="Chicago, IL",
        employment_type="full-time",
        start_date="05/2021",
        end_date="06/2024",
        status=ExperienceIntakeStatus.DRAFT_GENERATED,
        draft_experience_entry=original_draft,
    )
    repository.save_session(session)

    updated = service.update_draft_entry("session-123", edited_draft)

    assert updated.status == ExperienceIntakeStatus.DRAFT_GENERATED
    assert updated.updated_at > session.updated_at
    assert updated.draft_experience_entry is not None
    assert updated.draft_experience_entry.id == "entry-123"
    assert updated.draft_experience_entry.employer_name == "Acme Analytics"
    assert updated.draft_experience_entry.job_title == "Senior Data Engineer"
    assert updated.draft_experience_entry.location == "Chicago, IL"
    assert updated.draft_experience_entry.employment_type == "full-time"
    assert updated.draft_experience_entry.start_date == YearMonth(year=2021, month=5)
    assert updated.draft_experience_entry.end_date == YearMonth(year=2024, month=6)
    assert updated.draft_experience_entry.role_summary == (
        "Built reporting automation for finance operations."
    )
    assert updated.draft_experience_entry.accomplishments == [
        "Reduced manual reporting time by 10 hours per week."
    ]
    assert repository.load_session("session-123") == updated


def test_update_draft_entry_rejects_missing_session() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())
    draft = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.update_draft_entry("missing", draft)


def test_update_draft_entry_requires_draft_generated_status() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    draft = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.ANSWERS_CAPTURED,
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="draft must be generated"):
        service.update_draft_entry("session-123", draft)

    assert repository.load_session("session-123") == session


def test_update_draft_entry_rejects_locked_session() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.LOCKED,
        draft_experience_entry=draft,
        accepted_experience_entry_id="entry-123",
        locked_at="2026-01-01T00:00:00+00:00",
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="cannot be edited"):
        service.update_draft_entry("session-123", draft)

    assert repository.load_session("session-123") == session


def test_update_draft_entry_requires_existing_draft_entry() -> None:
    repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(repository)
    draft = ExperienceEntry(
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.DRAFT_GENERATED,
    )
    repository.save_session(session)

    with pytest.raises(ValueError, match="draft entry is required"):
        service.update_draft_entry("session-123", draft)

    assert repository.load_session("session-123") == session


def test_lock_draft_entry_saves_entry_to_new_career_profile() -> None:
    intake_repository = FakeExperienceIntakeRepository()
    profile_repository = FakeProfileRepository()
    service = ExperienceIntakeService(
        intake_repository,
        profile_repository=profile_repository,
    )
    draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["Reduced manual reporting time by 10 hours per week."],
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.DRAFT_GENERATED,
        draft_experience_entry=draft,
    )
    intake_repository.save_session(session)

    updated = service.lock_draft_entry("session-123")

    assert updated.status == ExperienceIntakeStatus.LOCKED
    assert updated.accepted_experience_entry_id == "entry-123"
    assert updated.locked_at is not None
    assert updated.updated_at > session.updated_at
    assert intake_repository.load_session("session-123") == updated
    assert profile_repository.career_profile is not None
    assert profile_repository.career_profile.experience_entries == [draft]


def test_lock_draft_entry_replaces_existing_profile_entry_with_same_id() -> None:
    intake_repository = FakeExperienceIntakeRepository()
    profile_repository = FakeProfileRepository()
    service = ExperienceIntakeService(
        intake_repository,
        profile_repository=profile_repository,
    )
    old_entry = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["Old accomplishment."],
    )
    other_entry = ExperienceEntry(
        id="entry-456",
        employer_name="Beta Insights",
        job_title="Data Engineer",
    )
    new_entry = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
        accomplishments=["New accomplishment."],
    )
    profile_repository.save_career_profile(
        CareerProfile(experience_entries=[old_entry, other_entry])
    )
    intake_repository.save_session(
        ExperienceIntakeSession(
            id="session-123",
            status=ExperienceIntakeStatus.DRAFT_GENERATED,
            draft_experience_entry=new_entry,
        )
    )

    service.lock_draft_entry("session-123")

    assert profile_repository.career_profile is not None
    assert profile_repository.career_profile.experience_entries == [other_entry, new_entry]


def test_lock_draft_entry_rejects_unconfigured_profile_repository() -> None:
    service = ExperienceIntakeService(FakeExperienceIntakeRepository())

    with pytest.raises(RuntimeError, match="Profile repository is not configured"):
        service.lock_draft_entry("session-123")


def test_lock_draft_entry_rejects_missing_session() -> None:
    service = ExperienceIntakeService(
        FakeExperienceIntakeRepository(),
        profile_repository=FakeProfileRepository(),
    )

    with pytest.raises(ValueError, match="Experience intake session not found"):
        service.lock_draft_entry("missing")


def test_lock_draft_entry_requires_draft_generated_status() -> None:
    intake_repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(
        intake_repository,
        profile_repository=FakeProfileRepository(),
    )
    session = ExperienceIntakeSession(id="session-123")
    intake_repository.save_session(session)

    with pytest.raises(ValueError, match="draft must be generated"):
        service.lock_draft_entry("session-123")

    assert intake_repository.load_session("session-123") == session


def test_lock_draft_entry_requires_draft_entry() -> None:
    intake_repository = FakeExperienceIntakeRepository()
    service = ExperienceIntakeService(
        intake_repository,
        profile_repository=FakeProfileRepository(),
    )
    session = ExperienceIntakeSession(
        id="session-123",
        status=ExperienceIntakeStatus.DRAFT_GENERATED,
    )
    intake_repository.save_session(session)

    with pytest.raises(ValueError, match="draft entry is required"):
        service.lock_draft_entry("session-123")

    assert intake_repository.load_session("session-123") == session


def test_accept_draft_entry_wraps_lock_draft_entry_for_compatibility() -> None:
    intake_repository = FakeExperienceIntakeRepository()
    profile_repository = FakeProfileRepository()
    service = ExperienceIntakeService(
        intake_repository,
        profile_repository=profile_repository,
    )
    draft = ExperienceEntry(
        id="entry-123",
        employer_name="Acme Analytics",
        job_title="Senior Data Engineer",
    )
    intake_repository.save_session(
        ExperienceIntakeSession(
            id="session-123",
            status=ExperienceIntakeStatus.DRAFT_GENERATED,
            draft_experience_entry=draft,
        )
    )

    updated = service.accept_draft_entry("session-123")

    assert updated.status == ExperienceIntakeStatus.LOCKED
    assert updated.locked_at is not None
