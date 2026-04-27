from __future__ import annotations

from career_agent.application.ports import (
    ExperienceIntakeAssistant,
    ExperienceIntakeRepository,
)
from career_agent.domain.models import (
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    utc_now,
)


class ExperienceIntakeService:
    """Application service for recoverable experience intake workflows."""

    def __init__(
        self,
        repository: ExperienceIntakeRepository,
        assistant: ExperienceIntakeAssistant | None = None,
    ) -> None:
        self.repository = repository
        self.assistant = assistant

    def create_session(self) -> ExperienceIntakeSession:
        """Create and persist a new draft intake session."""

        session = ExperienceIntakeSession()
        self.repository.save_session(session)
        return session

    def get_session(self, session_id: str) -> ExperienceIntakeSession | None:
        """Return a stored intake session if it exists."""

        return self.repository.load_session(session_id)

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        """Return all stored intake sessions."""

        return self.repository.list_sessions()

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        """Return stored intake sessions matching a status."""

        return self.repository.list_sessions_by_status(status)

    def capture_source_text(
        self,
        session_id: str,
        source_text: str,
    ) -> ExperienceIntakeSession:
        """Store role-specific source text for an existing intake session."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        normalized_source_text = source_text.strip()
        if not normalized_source_text:
            msg = "Experience intake source text is required."
            raise ValueError(msg)

        updated = session.model_copy(
            update={
                "source_text": normalized_source_text,
                "status": ExperienceIntakeStatus.SOURCE_CAPTURED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def generate_follow_up_questions(self, session_id: str) -> ExperienceIntakeSession:
        """Generate and store follow-up questions for captured source text."""

        if self.assistant is None:
            msg = "Experience intake assistant is not configured."
            raise RuntimeError(msg)

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status is not ExperienceIntakeStatus.SOURCE_CAPTURED:
            msg = "Experience intake source text must be captured before generating questions."
            raise ValueError(msg)

        if not session.source_text:
            msg = "Experience intake source text is required before generating questions."
            raise ValueError(msg)

        questions = self.assistant.generate_follow_up_questions(session)
        if not questions:
            msg = "Experience intake assistant returned no follow-up questions."
            raise ValueError(msg)

        updated = session.model_copy(
            update={
                "follow_up_questions": questions,
                "status": ExperienceIntakeStatus.QUESTIONS_GENERATED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated
