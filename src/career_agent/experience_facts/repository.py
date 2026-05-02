from __future__ import annotations

import shutil
from pathlib import Path
from typing import TypeAlias

from pydantic import TypeAdapter

from career_agent.experience_facts.models import ExperienceFact, FactChangeEvent
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

EXPERIENCE_FACTS_DIRNAME = "experience_facts"
EXPERIENCE_FACTS_FILENAME = "experience_facts.json"
FACT_CHANGE_EVENTS_FILENAME = "fact_change_events.json"

ExperienceFactList: TypeAlias = list[ExperienceFact]
FactChangeEventList: TypeAlias = list[FactChangeEvent]

_FACT_LIST_ADAPTER = TypeAdapter(list[ExperienceFact])
_FACT_CHANGE_EVENT_LIST_ADAPTER = TypeAdapter(list[FactChangeEvent])


class ExperienceFactRepository:
    """File-backed storage boundary for experience facts."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def facts_dir(self) -> Path:
        """Return the directory that stores experience fact data."""

        return self.data_dir / EXPERIENCE_FACTS_DIRNAME

    @property
    def facts_path(self) -> Path:
        """Return the JSON file path for experience facts."""

        return self.facts_dir / EXPERIENCE_FACTS_FILENAME

    @property
    def change_events_path(self) -> Path:
        """Return the JSON file path for fact change events."""

        return self.facts_dir / FACT_CHANGE_EVENTS_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores experience fact snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / EXPERIENCE_FACTS_DIRNAME

    def list(self, role_id: str | None = None) -> ExperienceFactList:
        """Load all facts, optionally filtered by experience role id."""

        facts = self._load_all()
        if role_id is None:
            return facts
        return [fact for fact in facts if fact.role_id == role_id]

    def get(self, fact_id: str) -> ExperienceFact | None:
        """Load one fact by identifier if it exists."""

        for fact in self._load_all():
            if fact.id == fact_id:
                return fact
        return None

    def save(self, fact: ExperienceFact) -> None:
        """Create or update one experience fact."""

        facts = [existing_fact for existing_fact in self._load_all() if existing_fact.id != fact.id]
        facts.append(fact)
        self._save_all(facts)

    def list_change_events(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> FactChangeEventList:
        """Load fact change events, optionally filtered by fact or role."""

        events = self._load_all_change_events()
        if fact_id is not None:
            events = [event for event in events if event.fact_id == fact_id]
        if role_id is not None:
            events = [event for event in events if event.role_id == role_id]
        return events

    def save_change_event(self, event: FactChangeEvent) -> None:
        """Append one fact change event."""

        events = self._load_all_change_events()
        events.append(event)
        self._save_all_change_events(events)

    def delete(self, fact_id: str) -> bool:
        """Delete one experience fact by identifier."""

        facts = self._load_all()
        remaining_facts = [fact for fact in facts if fact.id != fact_id]
        if len(remaining_facts) == len(facts):
            return False

        self._save_all(remaining_facts)
        return True

    def _load_all(self) -> ExperienceFactList:
        """Load all facts from disk in stored order."""

        if not self.facts_path.exists():
            return []

        return _FACT_LIST_ADAPTER.validate_json(self.facts_path.read_text(encoding="utf-8"))

    def _load_all_change_events(self) -> FactChangeEventList:
        """Load all fact change events from disk in stored order."""

        if not self.change_events_path.exists():
            return []

        return _FACT_CHANGE_EVENT_LIST_ADAPTER.validate_json(
            self.change_events_path.read_text(encoding="utf-8")
        )

    def _save_all(self, facts: ExperienceFactList) -> None:
        """Persist the complete fact list to disk."""

        self.facts_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_facts()
        self.facts_path.write_text(
            _FACT_LIST_ADAPTER.dump_json(facts, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _save_all_change_events(self, events: FactChangeEventList) -> None:
        """Persist the complete fact change event list to disk."""

        self.facts_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_change_events()
        self.change_events_path.write_text(
            _FACT_CHANGE_EVENT_LIST_ADAPTER.dump_json(events, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_facts(self) -> None:
        """Copy the current facts file before overwriting it."""

        if not self.facts_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (
            f"{timestamp_for_snapshot()}-{EXPERIENCE_FACTS_FILENAME}"
        )
        shutil.copy2(self.facts_path, snapshot_path)

    def _snapshot_existing_change_events(self) -> None:
        """Copy the current fact change event file before overwriting it."""

        if not self.change_events_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / (
            f"{timestamp_for_snapshot()}-{FACT_CHANGE_EVENTS_FILENAME}"
        )
        shutil.copy2(self.change_events_path, snapshot_path)
