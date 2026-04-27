from __future__ import annotations

from typing import Protocol

from career_agent.domain.models import (
    CareerProfile,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    IntakeQuestion,
    UserPreferences,
)


class ProfileRepository(Protocol):
    """Persistence contract for canonical profile data."""

    def profile_storage_initialized(self) -> bool:
        """Return whether profile storage scaffolding already exists."""

    def initialize_profile_storage(self) -> None:
        """Create the directory scaffolding needed for profile persistence."""

    def load_user_preferences(self) -> UserPreferences | None:
        """Load the stored user preferences, or return `None` if not yet present."""

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        """Persist the canonical user preferences."""

    def load_career_profile(self) -> CareerProfile | None:
        """Load the stored career profile, or return `None` if not yet present."""

    def save_career_profile(self, profile: CareerProfile) -> None:
        """Persist the canonical career profile."""


class ExperienceIntakeRepository(Protocol):
    """Persistence contract for recoverable experience intake workflow state."""

    def load_session(self, session_id: str) -> ExperienceIntakeSession | None:
        """Load an intake session, or return `None` if it does not exist."""

    def save_session(self, session: ExperienceIntakeSession) -> None:
        """Persist an intake session."""

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        """Return all intake sessions."""

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        """Return intake sessions matching a workflow status."""


class ExperienceIntakeAssistant(Protocol):
    """Assistant contract for LLM-assisted experience intake workflow steps."""

    def generate_follow_up_questions(
        self,
        session: ExperienceIntakeSession,
    ) -> list[IntakeQuestion]:
        """Generate structured follow-up questions for an intake session."""
