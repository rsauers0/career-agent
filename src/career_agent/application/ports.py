from __future__ import annotations

from typing import Protocol

from career_agent.domain.models import CareerProfile, UserPreferences


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
