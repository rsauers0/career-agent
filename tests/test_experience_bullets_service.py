import pytest

from career_agent.experience_bullets.models import ExperienceBullet, ExperienceBulletStatus
from career_agent.experience_bullets.service import (
    ExperienceBulletService,
    RoleNotFoundError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry


class FakeExperienceBulletRepository:
    def __init__(self) -> None:
        self.bullets: dict[str, ExperienceBullet] = {}

    def list(self, role_id: str | None = None) -> list[ExperienceBullet]:
        bullets = list(self.bullets.values())
        if role_id is None:
            return bullets
        return [bullet for bullet in bullets if bullet.role_id == role_id]

    def get(self, bullet_id: str) -> ExperienceBullet | None:
        return self.bullets.get(bullet_id)

    def save(self, bullet: ExperienceBullet) -> None:
        self.bullets[bullet.id] = bullet

    def delete(self, bullet_id: str) -> bool:
        if bullet_id not in self.bullets:
            return False
        del self.bullets[bullet_id]
        return True


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

    def get(self, source_id: str) -> RoleSourceEntry | None:
        return self.sources.get(source_id)

    def save(self, source: RoleSourceEntry) -> None:
        self.sources[source.id] = source


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_source(source_id: str = "source-1", role_id: str = "role-1") -> RoleSourceEntry:
    return RoleSourceEntry(
        id=source_id,
        role_id=role_id,
        source_text="- Led a reporting automation project.",
    )


def build_service() -> tuple[
    ExperienceBulletService,
    FakeExperienceBulletRepository,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
]:
    bullet_repository = FakeExperienceBulletRepository()
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    return (
        ExperienceBulletService(
            bullet_repository,
            role_repository,
            source_repository,
        ),
        bullet_repository,
        role_repository,
        source_repository,
    )


def test_experience_bullet_service_lists_bullets() -> None:
    service, _bullet_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    first_bullet = service.add_bullet(
        role_id="role-1",
        text="Automated reporting workflows.",
        source_ids=["source-1"],
    )
    second_bullet = service.add_bullet(
        role_id="role-1",
        text="Built a dashboard for service performance trends.",
    )

    assert service.list_bullets() == [first_bullet, second_bullet]
    assert service.list_bullets(role_id="role-1") == [first_bullet, second_bullet]


def test_experience_bullet_service_returns_bullet_by_id() -> None:
    service, _bullet_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    bullet = service.add_bullet(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    assert service.get_bullet(bullet.id) == bullet
    assert service.get_bullet("missing-bullet") is None


def test_experience_bullet_service_adds_bullet_for_existing_role() -> None:
    service, _bullet_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())

    bullet = service.add_bullet(
        role_id="role-1",
        text="Automated reporting workflows.",
        source_ids=["source-1"],
    )

    assert bullet.role_id == "role-1"
    assert bullet.source_ids == ["source-1"]
    assert bullet.text == "Automated reporting workflows."
    assert bullet.status == ExperienceBulletStatus.DRAFT


def test_experience_bullet_service_rejects_bullet_for_missing_role() -> None:
    service, _bullet_repository, _role_repository, _source_repository = build_service()

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.add_bullet(
            role_id="role-1",
            text="Automated reporting workflows.",
        )


def test_experience_bullet_service_rejects_missing_source_id() -> None:
    service, _bullet_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    with pytest.raises(SourceNotFoundError, match="source-1"):
        service.add_bullet(
            role_id="role-1",
            text="Automated reporting workflows.",
            source_ids=["source-1"],
        )


def test_experience_bullet_service_rejects_source_for_different_role() -> None:
    service, _bullet_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source(source_id="source-1", role_id="role-2"))

    with pytest.raises(SourceRoleMismatchError, match="source-1"):
        service.add_bullet(
            role_id="role-1",
            text="Automated reporting workflows.",
            source_ids=["source-1"],
        )


def test_experience_bullet_service_saves_existing_bullet_with_validation() -> None:
    service, _bullet_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    bullet = ExperienceBullet(
        id="bullet-1",
        role_id="role-1",
        source_ids=["source-1"],
        text="Automated reporting workflows.",
        status=ExperienceBulletStatus.ACTIVE,
    )

    service.save_bullet(bullet)

    assert service.get_bullet("bullet-1") == bullet


def test_experience_bullet_service_deletes_bullet() -> None:
    service, _bullet_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    bullet = service.add_bullet(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    assert service.delete_bullet(bullet.id) is True
    assert service.delete_bullet("missing-bullet") is False
    assert service.get_bullet(bullet.id) is None
