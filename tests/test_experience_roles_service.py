from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_roles.service import ExperienceRoleService


class FakeExperienceRoleRepository:
    def __init__(self) -> None:
        self.roles: dict[str, ExperienceRole] = {}

    def list(self) -> list[ExperienceRole]:
        return list(self.roles.values())

    def get(self, role_id: str) -> ExperienceRole | None:
        return self.roles.get(role_id)

    def save(self, role: ExperienceRole) -> None:
        self.roles[role.id] = role

    def delete(self, role_id: str) -> bool:
        if role_id not in self.roles:
            return False
        del self.roles[role_id]
        return True


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def test_experience_role_service_lists_roles() -> None:
    repository = FakeExperienceRoleRepository()
    service = ExperienceRoleService(repository)
    role = build_role()
    repository.save(role)

    assert service.list_roles() == [role]


def test_experience_role_service_returns_role_by_id() -> None:
    repository = FakeExperienceRoleRepository()
    service = ExperienceRoleService(repository)
    role = build_role()
    repository.save(role)

    assert service.get_role("role-1") == role
    assert service.get_role("missing-role") is None


def test_experience_role_service_saves_role() -> None:
    repository = FakeExperienceRoleRepository()
    service = ExperienceRoleService(repository)
    role = build_role()

    service.save_role(role)

    assert repository.get("role-1") == role


def test_experience_role_service_deletes_role() -> None:
    repository = FakeExperienceRoleRepository()
    service = ExperienceRoleService(repository)
    role = build_role()
    repository.save(role)

    assert service.delete_role("role-1") is True
    assert service.delete_role("missing-role") is False
    assert service.get_role("role-1") is None
