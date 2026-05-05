from __future__ import annotations

import shutil
from pathlib import Path
from typing import TypeAlias

from pydantic import TypeAdapter

from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

SCOPED_CONSTRAINTS_DIRNAME = "scoped_constraints"
SCOPED_CONSTRAINTS_FILENAME = "scoped_constraints.json"

ScopedConstraintList: TypeAlias = list[ScopedConstraint]

_CONSTRAINT_LIST_ADAPTER = TypeAdapter(list[ScopedConstraint])


class ScopedConstraintRepository:
    """File-backed storage boundary for scoped constraints."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def constraints_dir(self) -> Path:
        """Return the directory that stores scoped constraint data."""

        return self.data_dir / SCOPED_CONSTRAINTS_DIRNAME

    @property
    def constraints_path(self) -> Path:
        """Return the JSON file path for scoped constraints."""

        return self.constraints_dir / SCOPED_CONSTRAINTS_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores scoped constraint snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / SCOPED_CONSTRAINTS_DIRNAME

    def list(
        self,
        scope_type: ConstraintScopeType | None = None,
        scope_id: str | None = None,
        status: ScopedConstraintStatus | None = None,
    ) -> ScopedConstraintList:
        """Load constraints, optionally filtered by scope or status."""

        constraints = self._load_all()
        if scope_type is not None:
            constraints = [
                constraint for constraint in constraints if constraint.scope_type == scope_type
            ]
        if scope_id is not None:
            constraints = [
                constraint for constraint in constraints if constraint.scope_id == scope_id
            ]
        if status is not None:
            constraints = [constraint for constraint in constraints if constraint.status == status]
        return constraints

    def get(self, constraint_id: str) -> ScopedConstraint | None:
        """Load one scoped constraint by identifier if it exists."""

        for constraint in self._load_all():
            if constraint.id == constraint_id:
                return constraint
        return None

    def save(self, constraint: ScopedConstraint) -> None:
        """Create or update one scoped constraint."""

        constraints = [
            existing_constraint
            for existing_constraint in self._load_all()
            if existing_constraint.id != constraint.id
        ]
        constraints.append(constraint)
        self._save_all(constraints)

    def _load_all(self) -> ScopedConstraintList:
        """Load all scoped constraints from disk in stored order."""

        if not self.constraints_path.exists():
            return []
        return _CONSTRAINT_LIST_ADAPTER.validate_json(
            self.constraints_path.read_text(encoding="utf-8")
        )

    def _save_all(self, constraints: ScopedConstraintList) -> None:
        """Persist the complete scoped constraint list."""

        self.constraints_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_constraints()
        self.constraints_path.write_text(
            _CONSTRAINT_LIST_ADAPTER.dump_json(constraints, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_constraints(self) -> None:
        """Copy the current constraints file before overwriting it."""

        if not self.constraints_path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = (
            self.snapshots_dir / f"{timestamp_for_snapshot()}-{SCOPED_CONSTRAINTS_FILENAME}"
        )
        shutil.copy2(self.constraints_path, snapshot_path)
