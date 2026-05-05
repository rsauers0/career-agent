from pydantic import TypeAdapter

from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.scoped_constraints.repository import (
    SCOPED_CONSTRAINTS_DIRNAME,
    SCOPED_CONSTRAINTS_FILENAME,
    ScopedConstraintRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

CONSTRAINT_LIST_ADAPTER = TypeAdapter(list[ScopedConstraint])


def build_constraint(
    *,
    constraint_id: str = "constraint-1",
    scope_type: ConstraintScopeType = ConstraintScopeType.GLOBAL,
    scope_id: str | None = None,
    status: ScopedConstraintStatus = ScopedConstraintStatus.PROPOSED,
) -> ScopedConstraint:
    return ScopedConstraint(
        id=constraint_id,
        scope_type=scope_type,
        scope_id=scope_id,
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not use em dashes.",
        status=status,
    )


def test_scoped_constraint_repository_builds_storage_paths(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)

    assert repository.constraints_dir == tmp_path / SCOPED_CONSTRAINTS_DIRNAME
    assert repository.constraints_path == (
        tmp_path / SCOPED_CONSTRAINTS_DIRNAME / SCOPED_CONSTRAINTS_FILENAME
    )
    assert repository.snapshots_dir == tmp_path / SNAPSHOTS_DIRNAME / SCOPED_CONSTRAINTS_DIRNAME


def test_scoped_constraint_repository_returns_empty_when_file_missing(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)

    assert repository.list() == []


def test_scoped_constraint_repository_saves_and_loads_constraints(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)
    constraint = build_constraint()

    repository.save(constraint)

    assert repository.constraints_path.exists()
    assert repository.list() == [constraint]
    assert repository.get("constraint-1") == constraint
    assert repository.get("missing-constraint") is None


def test_scoped_constraint_repository_filters_constraints(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)
    global_constraint = build_constraint(constraint_id="constraint-1")
    role_constraint = build_constraint(
        constraint_id="constraint-2",
        scope_type=ConstraintScopeType.ROLE,
        scope_id="role-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    repository.save(global_constraint)
    repository.save(role_constraint)

    assert repository.list(scope_type=ConstraintScopeType.GLOBAL) == [global_constraint]
    assert repository.list(scope_id="role-1") == [role_constraint]
    assert repository.list(status=ScopedConstraintStatus.ACTIVE) == [role_constraint]
    assert repository.list(scope_id="missing-scope") == []


def test_scoped_constraint_repository_updates_existing_constraint_by_id(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)
    original_constraint = build_constraint(constraint_id="constraint-1")
    updated_constraint = build_constraint(
        constraint_id="constraint-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    repository.save(original_constraint)

    repository.save(updated_constraint)

    assert repository.list() == [updated_constraint]


def test_scoped_constraint_repository_snapshots_existing_file(tmp_path) -> None:
    repository = ScopedConstraintRepository(tmp_path)
    first_constraint = build_constraint(constraint_id="constraint-1")
    second_constraint = build_constraint(constraint_id="constraint-2")
    repository.save(first_constraint)

    repository.save(second_constraint)

    snapshots = list(repository.snapshots_dir.glob(f"*-{SCOPED_CONSTRAINTS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_constraints = CONSTRAINT_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_constraints == [first_constraint]
