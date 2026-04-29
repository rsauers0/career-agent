from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from career_agent.experience_bullets.models import ExperienceBullet

EXPERIENCE_BULLETS_DIRNAME = "experience_bullets"
EXPERIENCE_BULLETS_FILENAME = "experience_bullets.json"
SNAPSHOTS_DIRNAME = "snapshots"

_BULLET_LIST_ADAPTER = TypeAdapter(list[ExperienceBullet])


class ExperienceBulletRepository:
    """File-backed storage boundary for experience bullets."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def bullets_dir(self) -> Path:
        """Return the directory that stores experience bullet data."""

        return self.data_dir / EXPERIENCE_BULLETS_DIRNAME

    @property
    def bullets_path(self) -> Path:
        """Return the JSON file path for experience bullets."""

        return self.bullets_dir / EXPERIENCE_BULLETS_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores experience bullet snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / EXPERIENCE_BULLETS_DIRNAME

    def list(self, role_id: str | None = None) -> list[ExperienceBullet]:
        """Load all bullets, optionally filtered by experience role id."""

        bullets = self._load_all()
        if role_id is None:
            return bullets
        return [bullet for bullet in bullets if bullet.role_id == role_id]

    def get(self, bullet_id: str) -> ExperienceBullet | None:
        """Load one bullet by identifier if it exists."""

        for bullet in self._load_all():
            if bullet.id == bullet_id:
                return bullet
        return None

    def save(self, bullet: ExperienceBullet) -> None:
        """Create or update one experience bullet."""

        bullets = [
            existing_bullet
            for existing_bullet in self._load_all()
            if existing_bullet.id != bullet.id
        ]
        bullets.append(bullet)
        self._save_all(bullets)

    def delete(self, bullet_id: str) -> bool:
        """Delete one experience bullet by identifier."""

        bullets = self._load_all()
        remaining_bullets = [bullet for bullet in bullets if bullet.id != bullet_id]
        if len(remaining_bullets) == len(bullets):
            return False

        self._save_all(remaining_bullets)
        return True

    def _load_all(self) -> list[ExperienceBullet]:
        """Load all bullets from disk in stored order."""

        if not self.bullets_path.exists():
            return []

        return _BULLET_LIST_ADAPTER.validate_json(self.bullets_path.read_text(encoding="utf-8"))

    def _save_all(self, bullets: list[ExperienceBullet]) -> None:
        """Persist the complete bullet list to disk."""

        self.bullets_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_bullets()
        self.bullets_path.write_text(
            _BULLET_LIST_ADAPTER.dump_json(bullets, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_bullets(self) -> None:
        """Copy the current bullets file before overwriting it."""

        if not self.bullets_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (
            f"{self._timestamp_for_snapshot()}-{EXPERIENCE_BULLETS_FILENAME}"
        )
        shutil.copy2(self.bullets_path, snapshot_path)

    def _timestamp_for_snapshot(self) -> str:
        """Return a UTC timestamp suitable for snapshot filenames."""

        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
