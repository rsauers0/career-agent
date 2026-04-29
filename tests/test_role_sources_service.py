import pytest

from career_agent.errors import RoleNotFoundError
from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.role_sources.service import RoleSourceService


class FakeExperienceRoleRepository:
    def __init__(self) -> None:
        self.roles: dict[str, ExperienceRole] = {}

    def get(self, role_id: str) -> ExperienceRole | None:
        return self.roles.get(role_id)

    def save(self, role: ExperienceRole) -> None:
        self.roles[role.id] = role


class FakeRoleSourceRepository:
    def __init__(self) -> None:
        self.sources: dict[str, RoleSourceEntry] = {}

    def list(self, role_id: str | None = None) -> list[RoleSourceEntry]:
        sources = list(self.sources.values())
        if role_id is None:
            return sources
        return [source for source in sources if source.role_id == role_id]

    def get(self, source_id: str) -> RoleSourceEntry | None:
        return self.sources.get(source_id)

    def save(self, source: RoleSourceEntry) -> None:
        self.sources[source.id] = source

    def delete(self, source_id: str) -> bool:
        if source_id not in self.sources:
            return False
        del self.sources[source_id]
        return True


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_service() -> tuple[
    RoleSourceService,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
]:
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    return RoleSourceService(source_repository, role_repository), role_repository, source_repository


def test_role_source_service_lists_sources() -> None:
    service, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    first_source = service.add_source(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )
    second_source = service.add_source(
        role_id="role-1",
        source_text="- Built a service trend dashboard.",
    )

    assert service.list_sources() == [first_source, second_source]
    assert service.list_sources(role_id="role-1") == [first_source, second_source]


def test_role_source_service_returns_source_by_id() -> None:
    service, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    source = service.add_source(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )

    assert service.get_source(source.id) == source
    assert service.get_source("missing-source") is None


def test_role_source_service_adds_source_for_existing_role() -> None:
    service, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    source = service.add_source(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )

    assert source.role_id == "role-1"
    assert source.source_text == "- Led a reporting automation project."


def test_role_source_service_rejects_source_for_missing_role() -> None:
    service, _role_repository, _source_repository = build_service()

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.add_source(
            role_id="role-1",
            source_text="- Led a reporting automation project.",
        )


def test_role_source_service_deletes_source() -> None:
    service, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    source = service.add_source(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )

    assert service.delete_source(source.id) is True
    assert service.delete_source("missing-source") is False
    assert service.get_source(source.id) is None
