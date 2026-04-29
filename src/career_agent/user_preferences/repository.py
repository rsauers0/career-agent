from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from career_agent.user_preferences.models import UserPreferences

USER_PREFERENCES_DIRNAME = "user_preferences"
USER_PREFERENCES_FILENAME = "user_preferences.json"
SNAPSHOTS_DIRNAME = "snapshots"


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

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores user preference snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / USER_PREFERENCES_DIRNAME

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
        self._snapshot_existing_preferences()
        self.preferences_path.write_text(
            preferences.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _snapshot_existing_preferences(self) -> None:
        """Copy the current preferences file before overwriting it."""

        if not self.preferences_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (
            f"{self._timestamp_for_snapshot()}-{USER_PREFERENCES_FILENAME}"
        )
        shutil.copy2(self.preferences_path, snapshot_path)

    def _timestamp_for_snapshot(self) -> str:
        """Return a UTC timestamp suitable for snapshot filenames."""

        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
