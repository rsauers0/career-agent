from __future__ import annotations

from pathlib import Path

from career_agent.user_preferences.models import UserPreferences

USER_PREFERENCES_DIRNAME = "user_preferences"
USER_PREFERENCES_FILENAME = "user_preferences.json"


class UserPreferencesRepository:
    """File-backed storage boundary for user preferences."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def preferences_dir(self) -> Path:
        """Return the directory that stores user preference data."""

        return self.data_dir / USER_PREFERENCES_DIRNAME

    @property
    def preferences_path(self) -> Path:
        """Return the JSON file path for user preferences."""

        return self.preferences_dir / USER_PREFERENCES_FILENAME

    def load(self) -> UserPreferences | None:
        """Load user preferences from disk if they exist."""

        if not self.preferences_path.exists():
            return None

        return UserPreferences.model_validate_json(
            self.preferences_path.read_text(encoding="utf-8")
        )

    def save(self, preferences: UserPreferences) -> None:
        """Persist user preferences to disk."""

        self.preferences_dir.mkdir(parents=True, exist_ok=True)
        self.preferences_path.write_text(
            preferences.model_dump_json(indent=2),
            encoding="utf-8",
        )
