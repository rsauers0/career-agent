from __future__ import annotations

from career_agent.application.ports import ProfileRepository
from career_agent.application.status import ComponentStatus, evaluate_user_preferences_status
from career_agent.domain.models import CareerProfile, UserPreferences


class ProfileService:
    """Application-layer operations for canonical profile data."""

    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    def profile_storage_initialized(self) -> bool:
        """Return whether profile storage scaffolding already exists."""

        return self.repository.profile_storage_initialized()

    def initialize_profile_storage(self) -> None:
        """Create the directory scaffolding used for profile persistence."""

        self.repository.initialize_profile_storage()

    def get_user_preferences(self) -> UserPreferences | None:
        """Return the stored user preferences, if present."""

        return self.repository.load_user_preferences()

    def get_user_preferences_status(self) -> ComponentStatus:
        """Return workflow completeness status for the stored user preferences."""

        return evaluate_user_preferences_status(self.get_user_preferences())

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        """Persist the provided user preferences."""

        self.repository.save_user_preferences(preferences)

    def get_career_profile(self) -> CareerProfile | None:
        """Return the stored career profile, if present."""

        return self.repository.load_career_profile()

    def save_career_profile(self, profile: CareerProfile) -> None:
        """Persist the provided career profile."""

        self.repository.save_career_profile(profile)
