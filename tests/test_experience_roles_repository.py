from pydantic import TypeAdapter

from career_agent.experience_roles.models import (
    EmploymentType,
    ExperienceRole,
    ExperienceRoleStatus,
)
from career_agent.experience_roles.repository import (
    EXPERIENCE_ROLES_DIRNAME,
    EXPERIENCE_ROLES_FILENAME,
    ExperienceRoleRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

ROLE_LIST_ADAPTER = TypeAdapter(list[ExperienceRole])


def build_role(
    *,
    role_id: str,
    employer_name: str = "Acme Analytics",
    job_title: str = "Senior Systems Analyst",
    start_date: str = "05/2021",
    end_date: str | None = "06/2024",
    is_current_role: bool = False,
    status: ExperienceRoleStatus = ExperienceRoleStatus.INPUT_REQUIRED,
) -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name=employer_name,
        job_title=job_title,
        employment_type=EmploymentType.FULL_TIME,
        start_date=start_date,
        end_date=end_date,
        is_current_role=is_current_role,
        status=status,
    )


def test_experience_role_repository_builds_storage_paths(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)

    assert repository.roles_dir == tmp_path / EXPERIENCE_ROLES_DIRNAME
    assert repository.roles_path == (
        tmp_path / EXPERIENCE_ROLES_DIRNAME / EXPERIENCE_ROLES_FILENAME
    )
    assert repository.snapshots_dir == (tmp_path / SNAPSHOTS_DIRNAME / EXPERIENCE_ROLES_DIRNAME)


def test_experience_role_repository_list_returns_empty_when_missing(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)

    assert repository.list() == []


def test_experience_role_repository_saves_and_loads_roles(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)
    role = build_role(role_id="role-1")

    repository.save(role)

    assert repository.roles_path.exists()
    assert repository.list() == [role]
    assert repository.get("role-1") == role


def test_experience_role_repository_get_returns_none_when_missing(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)

    assert repository.get("missing-role") is None


def test_experience_role_repository_updates_existing_role_by_id(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)
    original_role = build_role(role_id="role-1")
    updated_role = build_role(
        role_id="role-1",
        employer_name="Acme Updated",
        job_title="Platform Engineer",
        start_date="05/2021",
        end_date="07/2025",
        status=ExperienceRoleStatus.REVIEW_REQUIRED,
    )
    repository.save(original_role)

    repository.save(updated_role)

    assert repository.list() == [updated_role]


def test_experience_role_repository_deletes_role_by_id(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)
    role_to_delete = build_role(role_id="role-1")
    role_to_keep = build_role(
        role_id="role-2",
        employer_name="Beta Systems",
        start_date="01/2020",
        end_date="02/2022",
    )
    repository.save(role_to_delete)
    repository.save(role_to_keep)

    deleted = repository.delete("role-1")

    assert deleted is True
    assert repository.get("role-1") is None
    assert repository.list() == [role_to_keep]


def test_experience_role_repository_delete_returns_false_when_missing(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)

    assert repository.delete("missing-role") is False


def test_experience_role_repository_lists_current_and_recent_roles_first(tmp_path) -> None:
    repository = ExperienceRoleRepository(tmp_path)
    oldest_role = build_role(
        role_id="oldest",
        employer_name="Old Co",
        start_date="01/2018",
        end_date="01/2020",
    )
    current_role = build_role(
        role_id="current",
        employer_name="Current Co",
        start_date="02/2024",
        end_date=None,
        is_current_role=True,
    )
    recent_role = build_role(
        role_id="recent",
        employer_name="Recent Co",
        start_date="03/2020",
        end_date="12/2023",
    )

    repository.save(oldest_role)
    repository.save(current_role)
    repository.save(recent_role)

    assert [role.id for role in repository.list()] == ["current", "recent", "oldest"]


def test_experience_role_repository_snapshots_existing_file_before_overwrite(
    tmp_path,
) -> None:
    repository = ExperienceRoleRepository(tmp_path)
    first_role = build_role(role_id="role-1")
    second_role = build_role(
        role_id="role-2",
        employer_name="Beta Systems",
        start_date="07/2024",
        end_date="07/2025",
    )
    repository.save(first_role)

    repository.save(second_role)

    snapshots = list(repository.snapshots_dir.glob(f"*-{EXPERIENCE_ROLES_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_roles = ROLE_LIST_ADAPTER.validate_json(snapshots[0].read_text(encoding="utf-8"))
    assert snapshotted_roles == [first_role]
    assert repository.list() == [second_role, first_role]
