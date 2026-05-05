from __future__ import annotations

from datetime import UTC, datetime

from career_agent.errors import (
    FactNotFoundError,
    FactRoleMismatchError,
    InvalidScopedConstraintStatusTransitionError,
    RoleNotFoundError,
    ScopedConstraintNotFoundError,
)
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.scoped_constraints.repository import ScopedConstraintRepository

ALLOWED_SCOPED_CONSTRAINT_STATUS_TRANSITIONS: dict[
    ScopedConstraintStatus,
    set[ScopedConstraintStatus],
] = {
    ScopedConstraintStatus.PROPOSED: {
        ScopedConstraintStatus.ACTIVE,
        ScopedConstraintStatus.REJECTED,
        ScopedConstraintStatus.ARCHIVED,
    },
    ScopedConstraintStatus.ACTIVE: {ScopedConstraintStatus.ARCHIVED},
    ScopedConstraintStatus.REJECTED: {ScopedConstraintStatus.ARCHIVED},
    ScopedConstraintStatus.ARCHIVED: set(),
}


class ScopedConstraintService:
    """Application behavior for durable scoped constraints."""

    def __init__(
        self,
        constraint_repository: ScopedConstraintRepository,
        role_repository: ExperienceRoleRepository,
        fact_repository: ExperienceFactRepository,
    ) -> None:
        self.constraint_repository = constraint_repository
        self.role_repository = role_repository
        self.fact_repository = fact_repository

    def list_constraints(
        self,
        scope_type: ConstraintScopeType | None = None,
        scope_id: str | None = None,
        status: ScopedConstraintStatus | None = None,
    ) -> list[ScopedConstraint]:
        """Return scoped constraints, optionally filtered by scope or status."""

        return self.constraint_repository.list(
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
        )

    def list_applicable_constraints(
        self,
        role_id: str | None = None,
        fact_id: str | None = None,
    ) -> list[ScopedConstraint]:
        """Return active global, role, and fact constraints for a workflow context."""

        resolved_role_id = role_id
        if fact_id is not None:
            fact = self.fact_repository.get(fact_id)
            if fact is None:
                msg = f"Experience fact does not exist: {fact_id}"
                raise FactNotFoundError(msg)
            if resolved_role_id is not None and fact.role_id != resolved_role_id:
                msg = f"Experience fact {fact_id} does not belong to role: {resolved_role_id}"
                raise FactRoleMismatchError(msg)
            resolved_role_id = fact.role_id

        if resolved_role_id is not None and self.role_repository.get(resolved_role_id) is None:
            msg = f"Experience role does not exist: {resolved_role_id}"
            raise RoleNotFoundError(msg)

        constraints = self.constraint_repository.list(status=ScopedConstraintStatus.ACTIVE)
        applicable_constraints: list[ScopedConstraint] = []
        for constraint in constraints:
            if constraint.scope_type == ConstraintScopeType.GLOBAL:
                applicable_constraints.append(constraint)
            elif (
                constraint.scope_type == ConstraintScopeType.ROLE
                and constraint.scope_id == resolved_role_id
            ):
                applicable_constraints.append(constraint)
            elif (
                constraint.scope_type == ConstraintScopeType.FACT and constraint.scope_id == fact_id
            ):
                applicable_constraints.append(constraint)
        return applicable_constraints

    def add_constraint(
        self,
        scope_type: ConstraintScopeType,
        constraint_type: ConstraintType,
        rule_text: str,
        scope_id: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ScopedConstraint:
        """Add a proposed scoped constraint after validating its target scope."""

        constraint = ScopedConstraint(
            scope_type=scope_type,
            scope_id=scope_id,
            constraint_type=constraint_type,
            rule_text=rule_text,
            source_message_ids=source_message_ids or [],
        )
        self._validate_scope(scope_type=constraint.scope_type, scope_id=constraint.scope_id)
        self.constraint_repository.save(constraint)
        return constraint

    def activate_constraint(self, constraint_id: str) -> ScopedConstraint:
        """Activate a proposed scoped constraint."""

        return self._set_constraint_status(
            constraint_id=constraint_id,
            status=ScopedConstraintStatus.ACTIVE,
        )

    def reject_constraint(self, constraint_id: str) -> ScopedConstraint:
        """Reject a proposed scoped constraint."""

        return self._set_constraint_status(
            constraint_id=constraint_id,
            status=ScopedConstraintStatus.REJECTED,
        )

    def archive_constraint(self, constraint_id: str) -> ScopedConstraint:
        """Archive a scoped constraint."""

        return self._set_constraint_status(
            constraint_id=constraint_id,
            status=ScopedConstraintStatus.ARCHIVED,
        )

    def _get_required_constraint(self, constraint_id: str) -> ScopedConstraint:
        """Return one scoped constraint or raise a domain error."""

        constraint = self.constraint_repository.get(constraint_id)
        if constraint is None:
            msg = f"Scoped constraint does not exist: {constraint_id}"
            raise ScopedConstraintNotFoundError(msg)
        return constraint

    def _set_constraint_status(
        self,
        constraint_id: str,
        status: ScopedConstraintStatus,
    ) -> ScopedConstraint:
        """Persist an explicit scoped constraint status transition."""

        constraint = self._get_required_constraint(constraint_id)
        allowed_statuses = ALLOWED_SCOPED_CONSTRAINT_STATUS_TRANSITIONS[constraint.status]
        if status not in allowed_statuses:
            msg = (
                f"Cannot transition scoped constraint {constraint.id} "
                f"from {constraint.status.value} to {status.value}."
            )
            raise InvalidScopedConstraintStatusTransitionError(msg)

        updated_constraint = constraint.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.constraint_repository.save(updated_constraint)
        return updated_constraint

    def _validate_scope(
        self,
        scope_type: ConstraintScopeType,
        scope_id: str | None,
    ) -> None:
        """Validate that a scoped constraint target exists when applicable."""

        if scope_type == ConstraintScopeType.GLOBAL:
            return

        if scope_type == ConstraintScopeType.ROLE:
            if self.role_repository.get(scope_id or "") is None:
                msg = f"Experience role does not exist: {scope_id}"
                raise RoleNotFoundError(msg)
            return

        if self.fact_repository.get(scope_id or "") is None:
            msg = f"Experience fact does not exist: {scope_id}"
            raise FactNotFoundError(msg)
