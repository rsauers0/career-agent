from __future__ import annotations

from career_agent.user_preferences.models import UserPreferences
from career_agent.user_preferences.repository import UserPreferencesRepository


class UserPreferencesService:
    """Application behavior for user preferences."""

    def __init__(self, repository: UserPreferencesRepository) -> None:
        self.repository = repository

    def get_preferences(self) -> UserPreferences | None:
        """Return saved user preferences if they exist."""

        return self.repository.load()

    def save_preferences(self, preferences: UserPreferences) -> None:
        """Validate and persist user preferences."""

        self.repository.save(preferences)
