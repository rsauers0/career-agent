from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from career_agent.experience_roles.models import ExperienceRole
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

EXPERIENCE_ROLES_DIRNAME = "experience_roles"
EXPERIENCE_ROLES_FILENAME = "experience_roles.json"

_ROLE_LIST_ADAPTER = TypeAdapter(list[ExperienceRole])


class ExperienceRoleRepository:
    """File-backed storage boundary for experience roles."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def roles_dir(self) -> Path:
        """Return the directory that stores experience role data."""

        return self.data_dir / EXPERIENCE_ROLES_DIRNAME

    @property
    def roles_path(self) -> Path:
        """Return the JSON file path for experience roles."""

        return self.roles_dir / EXPERIENCE_ROLES_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores experience role snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / EXPERIENCE_ROLES_DIRNAME

    def list(self) -> list[ExperienceRole]:
        """Load all roles from disk in default display order."""

        return sorted(self._load_all(), key=self._role_sort_key, reverse=True)

    def get(self, role_id: str) -> ExperienceRole | None:
        """Load one role by identifier if it exists."""

        for role in self._load_all():
            if role.id == role_id:
                return role
        return None

    def save(self, role: ExperienceRole) -> None:
        """Create or update one experience role."""

        roles = [existing_role for existing_role in self._load_all() if existing_role.id != role.id]
        roles.append(role)
        self._save_all(roles)

    def delete(self, role_id: str) -> bool:
        """Delete one experience role by identifier."""

        roles = self._load_all()
        remaining_roles = [role for role in roles if role.id != role_id]
        if len(remaining_roles) == len(roles):
            return False

        self._save_all(remaining_roles)
        return True

    def _load_all(self) -> list[ExperienceRole]:
        """Load all roles from disk in stored order."""

        if not self.roles_path.exists():
            return []

        return _ROLE_LIST_ADAPTER.validate_json(self.roles_path.read_text(encoding="utf-8"))

    def _save_all(self, roles: list[ExperienceRole]) -> None:
        """Persist the complete role list to disk."""

        self.roles_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_roles()
        self.roles_path.write_text(
            _ROLE_LIST_ADAPTER.dump_json(roles, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_roles(self) -> None:
        """Copy the current roles file before overwriting it."""

        if not self.roles_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (
            f"{timestamp_for_snapshot()}-{EXPERIENCE_ROLES_FILENAME}"
        )
        shutil.copy2(self.roles_path, snapshot_path)

    def _role_sort_key(self, role: ExperienceRole) -> tuple[int, int, int, datetime]:
        """Return a key that puts current and most recent roles first."""

        current_rank = 1 if role.is_current_role else 0
        effective_end_date = role.end_date or role.start_date
        return (
            current_rank,
            effective_end_date.year,
            effective_end_date.month,
            role.updated_at,
        )
