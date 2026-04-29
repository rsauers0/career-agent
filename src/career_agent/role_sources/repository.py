from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import TypeAdapter

from career_agent.role_sources.models import RoleSourceEntry
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

ROLE_SOURCES_DIRNAME = "role_sources"
ROLE_SOURCES_FILENAME = "role_sources.json"

_SOURCE_LIST_ADAPTER = TypeAdapter(list[RoleSourceEntry])


class RoleSourceRepository:
    """File-backed storage boundary for role source entries."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def sources_dir(self) -> Path:
        """Return the directory that stores role source data."""

        return self.data_dir / ROLE_SOURCES_DIRNAME

    @property
    def sources_path(self) -> Path:
        """Return the JSON file path for role sources."""

        return self.sources_dir / ROLE_SOURCES_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores role source snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / ROLE_SOURCES_DIRNAME

    def list(self, role_id: str | None = None) -> list[RoleSourceEntry]:
        """Load all sources, optionally filtered by experience role id."""

        sources = self._load_all()
        if role_id is None:
            return sources
        return [source for source in sources if source.role_id == role_id]

    def get(self, source_id: str) -> RoleSourceEntry | None:
        """Load one source entry by identifier if it exists."""

        for source in self._load_all():
            if source.id == source_id:
                return source
        return None

    def save(self, source: RoleSourceEntry) -> None:
        """Create or update one role source entry."""

        sources = [
            existing_source
            for existing_source in self._load_all()
            if existing_source.id != source.id
        ]
        sources.append(source)
        self._save_all(sources)

    def delete(self, source_id: str) -> bool:
        """Delete one role source entry by identifier."""

        sources = self._load_all()
        remaining_sources = [source for source in sources if source.id != source_id]
        if len(remaining_sources) == len(sources):
            return False

        self._save_all(remaining_sources)
        return True

    def _load_all(self) -> list[RoleSourceEntry]:
        """Load all source entries from disk in stored order."""

        if not self.sources_path.exists():
            return []

        return _SOURCE_LIST_ADAPTER.validate_json(self.sources_path.read_text(encoding="utf-8"))

    def _save_all(self, sources: list[RoleSourceEntry]) -> None:
        """Persist the complete source list to disk."""

        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_sources()
        self.sources_path.write_text(
            _SOURCE_LIST_ADAPTER.dump_json(sources, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_sources(self) -> None:
        """Copy the current sources file before overwriting it."""

        if not self.sources_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (f"{timestamp_for_snapshot()}-{ROLE_SOURCES_FILENAME}")
        shutil.copy2(self.sources_path, snapshot_path)
