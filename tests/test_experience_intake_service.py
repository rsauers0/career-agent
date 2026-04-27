from __future__ import annotations

import pytest

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import (
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    IntakeQuestion,
)


class FakeExperienceIntakeRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, ExperienceIntakeSession] = {}

    def load_session(self, session_id: str) -> ExperienceIntakeSession | None:
        return self.sessions.get(session_id)

    def save_session(self, session: ExperienceIntakeSession) -> None:
        self.sessions[session.id] = session

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        return list(self.sessions.values())

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        return [session for session in self.sessions.values() if session.status == status]


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

    def generate_follow_up_questions(
        self,
        session: ExperienceIntakeSession,
    ) -> list[IntakeQuestion]:
        self.received_session = session
        return self.questions


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
