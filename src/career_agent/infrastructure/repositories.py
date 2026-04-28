from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from typing import TypeVar

from pydantic import BaseModel

from career_agent.domain.models import (
    CareerProfile,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    UserPreferences,
)

T = TypeVar("T", bound=BaseModel)


class FileProfileRepository:
    """File-backed repository for canonical profile data."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "profile"
        self.profile_snapshot_dir = self.data_dir / "snapshots" / "profile"
        self.user_preferences_path = self.profile_dir / "user_preferences.json"
        self.career_profile_path = self.profile_dir / "career_profile.json"

    def profile_storage_initialized(self) -> bool:
        """Return whether the profile storage directories already exist."""

        return self.profile_dir.exists() or self.profile_snapshot_dir.exists()

    def initialize_profile_storage(self) -> None:
        """Create the directory scaffolding used for profile storage."""

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_snapshot_dir.mkdir(parents=True, exist_ok=True)

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
        self.initialize_profile_storage()

        if path.exists():
            self._create_snapshot(path)

        path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def _create_snapshot(self, source_path: Path) -> None:
        self.profile_snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        snapshot_name = f"{source_path.stem}-{timestamp}{source_path.suffix}"
        copy2(source_path, self.profile_snapshot_dir / snapshot_name)


class FileExperienceIntakeRepository:
    """File-backed repository for recoverable experience intake sessions."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.session_dir = self.data_dir / "intake" / "experience"
        self.snapshot_dir = self.data_dir / "snapshots" / "intake" / "experience"

    def load_session(self, session_id: str) -> ExperienceIntakeSession | None:
        """Load an intake session from disk."""

        return self._load_model(ExperienceIntakeSession, self._session_path(session_id))

    def save_session(self, session: ExperienceIntakeSession) -> None:
        """Persist an intake session to disk."""

        self._save_model(session, self._session_path(session.id))

    def delete_session(self, session_id: str) -> bool:
        """Delete an intake session from disk, snapshotting it first if present."""

        path = self._session_path(session_id)
        if not path.exists():
            return False

        self._create_snapshot(path)
        path.unlink()
        return True

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        """Return all persisted intake sessions sorted by update time."""

        if not self.session_dir.exists():
            return []

        sessions = [
            ExperienceIntakeSession.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.session_dir.glob("*.json")
        ]
        return sorted(sessions, key=lambda session: session.updated_at, reverse=True)

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        """Return persisted intake sessions matching a workflow status."""

        return [session for session in self.list_sessions() if session.status == status]

    def _session_path(self, session_id: str) -> Path:
        if not session_id or "/" in session_id or "\\" in session_id:
            msg = "Experience intake session ID must be a file-safe identifier."
            raise ValueError(msg)

        return self.session_dir / f"{session_id}.json"

    def _load_model(self, model_type: type[T], path: Path) -> T | None:
        if not path.exists():
            return None

        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def _save_model(self, model: BaseModel, path: Path) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if path.exists():
            self._create_snapshot(path)

        path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def _create_snapshot(self, source_path: Path) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        snapshot_name = f"{source_path.stem}-{timestamp}{source_path.suffix}"
        copy2(source_path, self.snapshot_dir / snapshot_name)
