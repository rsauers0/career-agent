import pytest

from career_agent.errors import (
    FactNotFoundError,
    FactRoleMismatchError,
    InvalidScopedConstraintStatusTransitionError,
    RoleNotFoundError,
    ScopedConstraintNotFoundError,
)
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.scoped_constraints.service import ScopedConstraintService


class FakeScopedConstraintRepository:
    def __init__(self) -> None:
        self.constraints: dict[str, ScopedConstraint] = {}

    def list(
        self,
        scope_type: ConstraintScopeType | None = None,
        scope_id: str | None = None,
        status: ScopedConstraintStatus | None = None,
    ) -> list[ScopedConstraint]:
        constraints = list(self.constraints.values())
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
        return self.constraints.get(constraint_id)

    def save(self, constraint: ScopedConstraint) -> None:
        self.constraints[constraint.id] = constraint


class FakeExperienceRoleRepository:
    def __init__(self) -> None:
        self.roles: dict[str, ExperienceRole] = {}

    def get(self, role_id: str) -> ExperienceRole | None:
        return self.roles.get(role_id)

    def save(self, role: ExperienceRole) -> None:
        self.roles[role.id] = role


class FakeExperienceFactRepository:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}

    def get(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_fact(fact_id: str = "fact-1", role_id: str = "role-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        text="Managed reporting workflows.",
    )


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


def build_service() -> tuple[
    ScopedConstraintService,
    FakeScopedConstraintRepository,
    FakeExperienceRoleRepository,
    FakeExperienceFactRepository,
]:
    constraint_repository = FakeScopedConstraintRepository()
    role_repository = FakeExperienceRoleRepository()
    fact_repository = FakeExperienceFactRepository()
    return (
        ScopedConstraintService(
            constraint_repository,
            role_repository,
            fact_repository,
        ),
        constraint_repository,
        role_repository,
        fact_repository,
    )


def test_scoped_constraint_service_adds_global_constraint() -> None:
    service, constraint_repository, _role_repository, _fact_repository = build_service()

    constraint = service.add_constraint(
        scope_type=ConstraintScopeType.GLOBAL,
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not use em dashes.",
        source_message_ids=["message-1"],
    )

    assert constraint.scope_type == ConstraintScopeType.GLOBAL
    assert constraint.scope_id is None
    assert constraint.status == ScopedConstraintStatus.PROPOSED
    assert constraint.source_message_ids == ["message-1"]
    assert constraint_repository.get(constraint.id) == constraint


def test_scoped_constraint_service_adds_role_constraint_for_existing_role() -> None:
    service, _constraint_repository, role_repository, _fact_repository = build_service()
    role_repository.save(build_role())

    constraint = service.add_constraint(
        scope_type=ConstraintScopeType.ROLE,
        scope_id="role-1",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not describe this role as enterprise-level.",
    )

    assert constraint.scope_id == "role-1"


def test_scoped_constraint_service_rejects_role_constraint_for_missing_role() -> None:
    service, _constraint_repository, _role_repository, _fact_repository = build_service()

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.add_constraint(
            scope_type=ConstraintScopeType.ROLE,
            scope_id="role-1",
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not describe this role as enterprise-level.",
        )


def test_scoped_constraint_service_adds_fact_constraint_for_existing_fact() -> None:
    service, _constraint_repository, _role_repository, fact_repository = build_service()
    fact_repository.save(build_fact())

    constraint = service.add_constraint(
        scope_type=ConstraintScopeType.FACT,
        scope_id="fact-1",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not imply organization-wide deployment.",
    )

    assert constraint.scope_id == "fact-1"


def test_scoped_constraint_service_rejects_fact_constraint_for_missing_fact() -> None:
    service, _constraint_repository, _role_repository, _fact_repository = build_service()

    with pytest.raises(FactNotFoundError, match="fact-1"):
        service.add_constraint(
            scope_type=ConstraintScopeType.FACT,
            scope_id="fact-1",
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not imply organization-wide deployment.",
        )


def test_scoped_constraint_service_lists_constraints() -> None:
    service, constraint_repository, _role_repository, _fact_repository = build_service()
    proposed_constraint = build_constraint(constraint_id="constraint-1")
    active_constraint = build_constraint(
        constraint_id="constraint-2",
        status=ScopedConstraintStatus.ACTIVE,
    )
    constraint_repository.save(proposed_constraint)
    constraint_repository.save(active_constraint)

    assert service.list_constraints() == [proposed_constraint, active_constraint]
    assert service.list_constraints(status=ScopedConstraintStatus.ACTIVE) == [active_constraint]


def test_scoped_constraint_service_lists_applicable_constraints_for_fact() -> None:
    service, constraint_repository, role_repository, fact_repository = build_service()
    role_repository.save(build_role())
    fact_repository.save(build_fact())
    global_constraint = build_constraint(
        constraint_id="constraint-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    role_constraint = build_constraint(
        constraint_id="constraint-2",
        scope_type=ConstraintScopeType.ROLE,
        scope_id="role-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    fact_constraint = build_constraint(
        constraint_id="constraint-3",
        scope_type=ConstraintScopeType.FACT,
        scope_id="fact-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    proposed_constraint = build_constraint(
        constraint_id="constraint-4",
        status=ScopedConstraintStatus.PROPOSED,
    )
    constraint_repository.save(global_constraint)
    constraint_repository.save(role_constraint)
    constraint_repository.save(fact_constraint)
    constraint_repository.save(proposed_constraint)

    constraints = service.list_applicable_constraints(fact_id="fact-1")

    assert constraints == [global_constraint, role_constraint, fact_constraint]


def test_scoped_constraint_service_lists_applicable_constraints_for_role() -> None:
    service, constraint_repository, role_repository, _fact_repository = build_service()
    role_repository.save(build_role())
    global_constraint = build_constraint(
        constraint_id="constraint-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    role_constraint = build_constraint(
        constraint_id="constraint-2",
        scope_type=ConstraintScopeType.ROLE,
        scope_id="role-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    fact_constraint = build_constraint(
        constraint_id="constraint-3",
        scope_type=ConstraintScopeType.FACT,
        scope_id="fact-1",
        status=ScopedConstraintStatus.ACTIVE,
    )
    constraint_repository.save(global_constraint)
    constraint_repository.save(role_constraint)
    constraint_repository.save(fact_constraint)

    constraints = service.list_applicable_constraints(role_id="role-1")

    assert constraints == [global_constraint, role_constraint]


def test_scoped_constraint_service_rejects_applicable_constraints_for_missing_fact() -> None:
    service, _constraint_repository, _role_repository, _fact_repository = build_service()

    with pytest.raises(FactNotFoundError, match="fact-1"):
        service.list_applicable_constraints(fact_id="fact-1")


def test_scoped_constraint_service_rejects_applicable_constraints_for_mismatched_role() -> None:
    service, _constraint_repository, role_repository, fact_repository = build_service()
    role_repository.save(build_role(role_id="role-2"))
    fact_repository.save(build_fact(fact_id="fact-1", role_id="role-1"))

    with pytest.raises(FactRoleMismatchError, match="fact-1"):
        service.list_applicable_constraints(role_id="role-2", fact_id="fact-1")


def test_scoped_constraint_service_activates_rejects_and_archives_constraints() -> None:
    service, constraint_repository, _role_repository, _fact_repository = build_service()
    constraint = build_constraint()
    constraint_repository.save(constraint)

    active_constraint = service.activate_constraint("constraint-1")
    archived_constraint = service.archive_constraint("constraint-1")

    assert active_constraint.status == ScopedConstraintStatus.ACTIVE
    assert archived_constraint.status == ScopedConstraintStatus.ARCHIVED

    rejected_constraint = build_constraint(constraint_id="constraint-2")
    constraint_repository.save(rejected_constraint)

    rejected_constraint = service.reject_constraint("constraint-2")

    assert rejected_constraint.status == ScopedConstraintStatus.REJECTED


def test_scoped_constraint_service_rejects_missing_constraint_status_change() -> None:
    service, _constraint_repository, _role_repository, _fact_repository = build_service()

    with pytest.raises(ScopedConstraintNotFoundError, match="constraint-1"):
        service.activate_constraint("constraint-1")


def test_scoped_constraint_service_rejects_invalid_status_transition() -> None:
    service, constraint_repository, _role_repository, _fact_repository = build_service()
    constraint = build_constraint(status=ScopedConstraintStatus.ARCHIVED)
    constraint_repository.save(constraint)

    with pytest.raises(InvalidScopedConstraintStatusTransitionError, match="archived"):
        service.activate_constraint("constraint-1")
