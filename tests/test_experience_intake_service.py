from __future__ import annotations

import pytest

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.domain.models import ExperienceIntakeSession, ExperienceIntakeStatus


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
