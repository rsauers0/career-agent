from pydantic import TypeAdapter

from career_agent.experience_bullets.models import (
    ExperienceBullet,
    ExperienceBulletStatus,
)
from career_agent.experience_bullets.repository import (
    EXPERIENCE_BULLETS_DIRNAME,
    EXPERIENCE_BULLETS_FILENAME,
    ExperienceBulletRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

BULLET_LIST_ADAPTER = TypeAdapter(list[ExperienceBullet])


def build_bullet(
    *,
    bullet_id: str,
    role_id: str = "role-1",
    source_ids: list[str] | None = None,
    text: str = "Automated reporting workflows, reducing manual reconciliation time.",
    status: ExperienceBulletStatus = ExperienceBulletStatus.DRAFT,
) -> ExperienceBullet:
    return ExperienceBullet(
        id=bullet_id,
        role_id=role_id,
        source_ids=source_ids or [],
        text=text,
        status=status,
    )


def test_experience_bullet_repository_builds_storage_paths(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)

    assert repository.bullets_dir == tmp_path / EXPERIENCE_BULLETS_DIRNAME
    assert repository.bullets_path == (
        tmp_path / EXPERIENCE_BULLETS_DIRNAME / EXPERIENCE_BULLETS_FILENAME
    )
    assert repository.snapshots_dir == (tmp_path / SNAPSHOTS_DIRNAME / EXPERIENCE_BULLETS_DIRNAME)


def test_experience_bullet_repository_list_returns_empty_when_missing(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)

    assert repository.list() == []


def test_experience_bullet_repository_saves_and_loads_bullets(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)
    bullet = build_bullet(bullet_id="bullet-1")

    repository.save(bullet)

    assert repository.bullets_path.exists()
    assert repository.list() == [bullet]
    assert repository.get("bullet-1") == bullet


def test_experience_bullet_repository_filters_bullets_by_role_id(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)
    first_bullet = build_bullet(bullet_id="bullet-1", role_id="role-1")
    second_bullet = build_bullet(bullet_id="bullet-2", role_id="role-2")
    repository.save(first_bullet)
    repository.save(second_bullet)

    assert repository.list(role_id="role-1") == [first_bullet]
    assert repository.list(role_id="role-2") == [second_bullet]
    assert repository.list(role_id="missing-role") == []


def test_experience_bullet_repository_get_returns_none_when_missing(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)

    assert repository.get("missing-bullet") is None


def test_experience_bullet_repository_updates_existing_bullet_by_id(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)
    original_bullet = build_bullet(bullet_id="bullet-1")
    updated_bullet = build_bullet(
        bullet_id="bullet-1",
        text="Automated reporting workflows, reducing reconciliation time by 40%.",
        status=ExperienceBulletStatus.ACTIVE,
    )
    repository.save(original_bullet)

    repository.save(updated_bullet)

    assert repository.list() == [updated_bullet]


def test_experience_bullet_repository_deletes_bullet_by_id(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)
    bullet_to_delete = build_bullet(bullet_id="bullet-1")
    bullet_to_keep = build_bullet(bullet_id="bullet-2")
    repository.save(bullet_to_delete)
    repository.save(bullet_to_keep)

    deleted = repository.delete("bullet-1")

    assert deleted is True
    assert repository.get("bullet-1") is None
    assert repository.list() == [bullet_to_keep]


def test_experience_bullet_repository_delete_returns_false_when_missing(tmp_path) -> None:
    repository = ExperienceBulletRepository(tmp_path)

    assert repository.delete("missing-bullet") is False


def test_experience_bullet_repository_snapshots_existing_file_before_overwrite(
    tmp_path,
) -> None:
    repository = ExperienceBulletRepository(tmp_path)
    first_bullet = build_bullet(bullet_id="bullet-1")
    second_bullet = build_bullet(
        bullet_id="bullet-2",
        text="Built a dashboard for service performance trends.",
    )
    repository.save(first_bullet)

    repository.save(second_bullet)

    snapshots = list(repository.snapshots_dir.glob(f"*-{EXPERIENCE_BULLETS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_bullets = BULLET_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_bullets == [first_bullet]
    assert repository.list() == [first_bullet, second_bullet]
