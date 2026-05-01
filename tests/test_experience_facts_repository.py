from pydantic import TypeAdapter

from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
    FactChangeActor,
    FactChangeEvent,
    FactChangeEventType,
)
from career_agent.experience_facts.repository import (
    EXPERIENCE_FACTS_DIRNAME,
    EXPERIENCE_FACTS_FILENAME,
    FACT_CHANGE_EVENTS_FILENAME,
    ExperienceFactRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

FACT_LIST_ADAPTER = TypeAdapter(list[ExperienceFact])
FACT_CHANGE_EVENT_LIST_ADAPTER = TypeAdapter(list[FactChangeEvent])


def build_fact(
    *,
    fact_id: str,
    role_id: str = "role-1",
    source_ids: list[str] | None = None,
    text: str = "Automated reporting workflows, reducing manual reconciliation time.",
    status: ExperienceFactStatus = ExperienceFactStatus.DRAFT,
) -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        source_ids=source_ids or [],
        text=text,
        status=status,
    )


def test_experience_fact_repository_builds_storage_paths(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)

    assert repository.facts_dir == tmp_path / EXPERIENCE_FACTS_DIRNAME
    assert repository.facts_path == (
        tmp_path / EXPERIENCE_FACTS_DIRNAME / EXPERIENCE_FACTS_FILENAME
    )
    assert repository.change_events_path == (
        tmp_path / EXPERIENCE_FACTS_DIRNAME / FACT_CHANGE_EVENTS_FILENAME
    )
    assert repository.snapshots_dir == (tmp_path / SNAPSHOTS_DIRNAME / EXPERIENCE_FACTS_DIRNAME)


def test_experience_fact_repository_list_returns_empty_when_missing(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)

    assert repository.list() == []
    assert repository.list_change_events() == []


def test_experience_fact_repository_saves_and_loads_facts(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)
    fact = build_fact(fact_id="fact-1")

    repository.save(fact)

    assert repository.facts_path.exists()
    assert repository.list() == [fact]
    assert repository.get("fact-1") == fact


def test_experience_fact_repository_saves_and_loads_change_events(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)
    first_event = FactChangeEvent(
        id="event-1",
        fact_id="fact-1",
        role_id="role-1",
        event_type=FactChangeEventType.CREATED,
        actor=FactChangeActor.USER,
    )
    second_event = FactChangeEvent(
        id="event-2",
        fact_id="fact-2",
        role_id="role-1",
        event_type=FactChangeEventType.REVISED,
        actor=FactChangeActor.LLM,
    )

    repository.save_change_event(first_event)
    repository.save_change_event(second_event)

    assert repository.change_events_path.exists()
    assert repository.list_change_events() == [first_event, second_event]
    assert repository.list_change_events(fact_id="fact-1") == [first_event]
    assert repository.list_change_events(role_id="role-1") == [first_event, second_event]
    assert repository.list_change_events(role_id="missing-role") == []


def test_experience_fact_repository_filters_facts_by_role_id(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)
    first_fact = build_fact(fact_id="fact-1", role_id="role-1")
    second_fact = build_fact(fact_id="fact-2", role_id="role-2")
    repository.save(first_fact)
    repository.save(second_fact)

    assert repository.list(role_id="role-1") == [first_fact]
    assert repository.list(role_id="role-2") == [second_fact]
    assert repository.list(role_id="missing-role") == []


def test_experience_fact_repository_get_returns_none_when_missing(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)

    assert repository.get("missing-fact") is None


def test_experience_fact_repository_updates_existing_fact_by_id(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)
    original_fact = build_fact(fact_id="fact-1")
    updated_fact = build_fact(
        fact_id="fact-1",
        text="Automated reporting workflows, reducing reconciliation time by 40%.",
        status=ExperienceFactStatus.ACTIVE,
    )
    repository.save(original_fact)

    repository.save(updated_fact)

    assert repository.list() == [updated_fact]


def test_experience_fact_repository_deletes_fact_by_id(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)
    fact_to_delete = build_fact(fact_id="fact-1")
    fact_to_keep = build_fact(fact_id="fact-2")
    repository.save(fact_to_delete)
    repository.save(fact_to_keep)

    deleted = repository.delete("fact-1")

    assert deleted is True
    assert repository.get("fact-1") is None
    assert repository.list() == [fact_to_keep]


def test_experience_fact_repository_delete_returns_false_when_missing(tmp_path) -> None:
    repository = ExperienceFactRepository(tmp_path)

    assert repository.delete("missing-fact") is False


def test_experience_fact_repository_snapshots_existing_file_before_overwrite(
    tmp_path,
) -> None:
    repository = ExperienceFactRepository(tmp_path)
    first_fact = build_fact(fact_id="fact-1")
    second_fact = build_fact(
        fact_id="fact-2",
        text="Built a dashboard for service performance trends.",
    )
    repository.save(first_fact)

    repository.save(second_fact)

    snapshots = list(repository.snapshots_dir.glob(f"*-{EXPERIENCE_FACTS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_facts = FACT_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_facts == [first_fact]
    assert repository.list() == [first_fact, second_fact]


def test_experience_fact_repository_snapshots_existing_change_events_before_overwrite(
    tmp_path,
) -> None:
    repository = ExperienceFactRepository(tmp_path)
    first_event = FactChangeEvent(
        id="event-1",
        fact_id="fact-1",
        role_id="role-1",
        event_type=FactChangeEventType.CREATED,
        actor=FactChangeActor.USER,
    )
    second_event = FactChangeEvent(
        id="event-2",
        fact_id="fact-1",
        role_id="role-1",
        event_type=FactChangeEventType.ACTIVATED,
        actor=FactChangeActor.USER,
    )
    repository.save_change_event(first_event)

    repository.save_change_event(second_event)

    snapshots = list(repository.snapshots_dir.glob(f"*-{FACT_CHANGE_EVENTS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_events = FACT_CHANGE_EVENT_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_events == [first_event]
    assert repository.list_change_events() == [first_event, second_event]
