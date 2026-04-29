from pydantic import TypeAdapter

from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus
from career_agent.role_sources.repository import (
    ROLE_SOURCES_DIRNAME,
    ROLE_SOURCES_FILENAME,
    RoleSourceRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

SOURCE_LIST_ADAPTER = TypeAdapter(list[RoleSourceEntry])


def build_source(
    *,
    source_id: str,
    role_id: str = "role-1",
    source_text: str = "- Led a reporting automation project.",
    status: RoleSourceStatus = RoleSourceStatus.NOT_ANALYZED,
) -> RoleSourceEntry:
    return RoleSourceEntry(
        id=source_id,
        role_id=role_id,
        source_text=source_text,
        status=status,
    )


def test_role_source_repository_builds_storage_paths(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)

    assert repository.sources_dir == tmp_path / ROLE_SOURCES_DIRNAME
    assert repository.sources_path == tmp_path / ROLE_SOURCES_DIRNAME / ROLE_SOURCES_FILENAME
    assert repository.snapshots_dir == tmp_path / SNAPSHOTS_DIRNAME / ROLE_SOURCES_DIRNAME


def test_role_source_repository_list_returns_empty_when_missing(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)

    assert repository.list() == []


def test_role_source_repository_saves_and_loads_sources(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)
    source = build_source(source_id="source-1")

    repository.save(source)

    assert repository.sources_path.exists()
    assert repository.list() == [source]
    assert repository.get("source-1") == source


def test_role_source_repository_filters_sources_by_role_id(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)
    first_source = build_source(source_id="source-1", role_id="role-1")
    second_source = build_source(source_id="source-2", role_id="role-2")
    repository.save(first_source)
    repository.save(second_source)

    assert repository.list(role_id="role-1") == [first_source]
    assert repository.list(role_id="role-2") == [second_source]
    assert repository.list(role_id="missing-role") == []


def test_role_source_repository_get_returns_none_when_missing(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)

    assert repository.get("missing-source") is None


def test_role_source_repository_updates_existing_source_by_id(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)
    original_source = build_source(source_id="source-1")
    updated_source = build_source(
        source_id="source-1",
        source_text="- Led a reporting automation project with executive visibility.",
        status=RoleSourceStatus.ANALYZED,
    )
    repository.save(original_source)

    repository.save(updated_source)

    assert repository.list() == [updated_source]


def test_role_source_repository_deletes_source_by_id(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)
    source_to_delete = build_source(source_id="source-1")
    source_to_keep = build_source(source_id="source-2")
    repository.save(source_to_delete)
    repository.save(source_to_keep)

    deleted = repository.delete("source-1")

    assert deleted is True
    assert repository.get("source-1") is None
    assert repository.list() == [source_to_keep]


def test_role_source_repository_delete_returns_false_when_missing(tmp_path) -> None:
    repository = RoleSourceRepository(tmp_path)

    assert repository.delete("missing-source") is False


def test_role_source_repository_snapshots_existing_file_before_overwrite(
    tmp_path,
) -> None:
    repository = RoleSourceRepository(tmp_path)
    first_source = build_source(source_id="source-1")
    second_source = build_source(
        source_id="source-2",
        source_text="- Built a dashboard for service performance trends.",
    )
    repository.save(first_source)

    repository.save(second_source)

    snapshots = list(repository.snapshots_dir.glob(f"*-{ROLE_SOURCES_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_sources = SOURCE_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_sources == [first_source]
    assert repository.list() == [first_source, second_source]
