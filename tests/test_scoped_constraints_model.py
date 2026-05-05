from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)


def test_scoped_constraint_json_round_trip() -> None:
    constraint = ScopedConstraint(
        scope_type=ConstraintScopeType.ROLE,
        scope_id="role-1",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not describe this role as enterprise-level.",
        source_message_ids=["message-1"],
        status=ScopedConstraintStatus.ACTIVE,
    )

    restored = ScopedConstraint.model_validate_json(constraint.model_dump_json())

    assert restored == constraint
    assert restored.id


def test_scoped_constraint_defaults_to_proposed() -> None:
    constraint = ScopedConstraint(
        scope_type=ConstraintScopeType.GLOBAL,
        constraint_type=ConstraintType.PREFERENCE,
        rule_text="Prefer direct wording.",
    )

    assert constraint.status == ScopedConstraintStatus.PROPOSED
    assert constraint.created_at.tzinfo is not None
    assert constraint.updated_at.tzinfo is not None


def test_scoped_constraint_normalizes_text_fields() -> None:
    constraint = ScopedConstraint(
        scope_type=ConstraintScopeType.FACT,
        scope_id="  fact-1  ",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="  Do not imply organization-wide deployment.  ",
        source_message_ids=["  message-1  ", ""],
    )

    assert constraint.scope_id == "fact-1"
    assert constraint.rule_text == "Do not imply organization-wide deployment."
    assert constraint.source_message_ids == ["message-1"]


def test_scoped_constraint_rejects_global_scope_id() -> None:
    with pytest.raises(ValidationError, match="global constraints cannot have scope_id"):
        ScopedConstraint(
            scope_type=ConstraintScopeType.GLOBAL,
            scope_id="role-1",
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not use em dashes.",
        )


def test_scoped_constraint_requires_scope_id_for_non_global_scope() -> None:
    with pytest.raises(ValidationError, match="role constraints require scope_id"):
        ScopedConstraint(
            scope_type=ConstraintScopeType.ROLE,
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not describe this role as enterprise-level.",
        )


def test_scoped_constraint_rejects_blank_rule_text() -> None:
    with pytest.raises(ValidationError):
        ScopedConstraint(
            scope_type=ConstraintScopeType.GLOBAL,
            constraint_type=ConstraintType.PREFERENCE,
            rule_text="  ",
        )


def test_scoped_constraint_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timestamp values must be timezone-aware"):
        ScopedConstraint(
            scope_type=ConstraintScopeType.GLOBAL,
            constraint_type=ConstraintType.PREFERENCE,
            rule_text="Prefer direct wording.",
            created_at=datetime(2026, 1, 1),
        )


def test_scoped_constraint_accepts_timezone_aware_timestamps() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    constraint = ScopedConstraint(
        scope_type=ConstraintScopeType.GLOBAL,
        constraint_type=ConstraintType.PREFERENCE,
        rule_text="Prefer direct wording.",
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert constraint.created_at == timestamp
    assert constraint.updated_at == timestamp
