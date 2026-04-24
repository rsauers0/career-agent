from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from typing import TypeVar

from pydantic import BaseModel

from career_agent.domain.models import CareerProfile, UserPreferences

T = TypeVar("T", bound=BaseModel)


class FileProfileRepository:
    """File-backed repository for canonical profile data."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "profile"
        self.profile_snapshot_dir = self.data_dir / "snapshots" / "profile"
        self.user_preferences_path = self.profile_dir / "user_preferences.json"
        self.career_profile_path = self.profile_dir / "career_profile.json"

    def load_user_preferences(self) -> UserPreferences | None:
        """Load canonical user preferences from disk."""

        return self._load_model(UserPreferences, self.user_preferences_path)

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        """Persist canonical user preferences to disk."""

        self._save_model(preferences, self.user_preferences_path)

    def load_career_profile(self) -> CareerProfile | None:
        """Load the canonical career profile from disk."""

        return self._load_model(CareerProfile, self.career_profile_path)

    def save_career_profile(self, profile: CareerProfile) -> None:
        """Persist the canonical career profile to disk."""

        self._save_model(profile, self.career_profile_path)

    def _load_model(self, model_type: type[T], path: Path) -> T | None:
        if not path.exists():
            return None

        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def _save_model(self, model: BaseModel, path: Path) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        if path.exists():
            self._create_snapshot(path)

        path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def _create_snapshot(self, source_path: Path) -> None:
        self.profile_snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        snapshot_name = f"{source_path.stem}-{timestamp}{source_path.suffix}"
        copy2(source_path, self.profile_snapshot_dir / snapshot_name)
