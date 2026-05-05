from pydantic import TypeAdapter

from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionStatus,
    FactReviewActionType,
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewThread,
    FactReviewThreadStatus,
)
from career_agent.fact_review.repository import (
    FACT_REVIEW_ACTIONS_FILENAME,
    FACT_REVIEW_DIRNAME,
    FACT_REVIEW_MESSAGES_FILENAME,
    FACT_REVIEW_THREADS_FILENAME,
    FactReviewRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

THREAD_LIST_ADAPTER = TypeAdapter(list[FactReviewThread])
MESSAGE_LIST_ADAPTER = TypeAdapter(list[FactReviewMessage])
ACTION_LIST_ADAPTER = TypeAdapter(list[FactReviewAction])


def build_thread(
    *,
    thread_id: str = "thread-1",
    fact_id: str = "fact-1",
    role_id: str = "role-1",
    status: FactReviewThreadStatus = FactReviewThreadStatus.OPEN,
) -> FactReviewThread:
    return FactReviewThread(
        id=thread_id,
        fact_id=fact_id,
        role_id=role_id,
        status=status,
    )


def build_message(
    *,
    message_id: str = "message-1",
    thread_id: str = "thread-1",
) -> FactReviewMessage:
    return FactReviewMessage(
        id=message_id,
        thread_id=thread_id,
        author=FactReviewMessageAuthor.USER,
        message_text="Looks good.",
    )


def build_action(
    *,
    action_id: str = "action-1",
    thread_id: str = "thread-1",
    fact_id: str = "fact-1",
    role_id: str = "role-1",
    status: FactReviewActionStatus = FactReviewActionStatus.PROPOSED,
) -> FactReviewAction:
    return FactReviewAction(
        id=action_id,
        thread_id=thread_id,
        fact_id=fact_id,
        role_id=role_id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
        status=status,
        applied_fact_id="fact-1" if status == FactReviewActionStatus.APPLIED else None,
    )


def test_fact_review_repository_builds_storage_paths(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)

    assert repository.review_dir == tmp_path / FACT_REVIEW_DIRNAME
    assert repository.threads_path == (
        tmp_path / FACT_REVIEW_DIRNAME / FACT_REVIEW_THREADS_FILENAME
    )
    assert repository.messages_path == (
        tmp_path / FACT_REVIEW_DIRNAME / FACT_REVIEW_MESSAGES_FILENAME
    )
    assert repository.actions_path == (
        tmp_path / FACT_REVIEW_DIRNAME / FACT_REVIEW_ACTIONS_FILENAME
    )
    assert repository.snapshots_dir == tmp_path / SNAPSHOTS_DIRNAME / FACT_REVIEW_DIRNAME


def test_fact_review_repository_returns_empty_when_files_missing(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)

    assert repository.list_threads() == []
    assert repository.list_messages("thread-1") == []
    assert repository.list_actions() == []


def test_fact_review_repository_saves_and_loads_threads(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    thread = build_thread()

    repository.save_thread(thread)

    assert repository.threads_path.exists()
    assert repository.list_threads() == [thread]
    assert repository.get_thread("thread-1") == thread


def test_fact_review_repository_filters_threads(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_thread = build_thread(thread_id="thread-1", fact_id="fact-1", role_id="role-1")
    second_thread = build_thread(thread_id="thread-2", fact_id="fact-2", role_id="role-2")
    repository.save_thread(first_thread)
    repository.save_thread(second_thread)

    assert repository.list_threads(fact_id="fact-1") == [first_thread]
    assert repository.list_threads(role_id="role-2") == [second_thread]
    assert repository.list_threads(fact_id="missing-fact") == []


def test_fact_review_repository_updates_existing_thread_by_id(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    original_thread = build_thread(thread_id="thread-1")
    updated_thread = build_thread(
        thread_id="thread-1",
        status=FactReviewThreadStatus.RESOLVED,
    )
    repository.save_thread(original_thread)

    repository.save_thread(updated_thread)

    assert repository.list_threads() == [updated_thread]


def test_fact_review_repository_saves_and_loads_messages(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_message = build_message(message_id="message-1", thread_id="thread-1")
    second_message = build_message(message_id="message-2", thread_id="thread-2")
    repository.save_message(first_message)
    repository.save_message(second_message)

    assert repository.messages_path.exists()
    assert repository.list_messages("thread-1") == [first_message]
    assert repository.get_message("message-2") == second_message
    assert repository.get_message("missing-message") is None


def test_fact_review_repository_updates_existing_message_by_id(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    original_message = build_message(message_id="message-1")
    updated_message = original_message.model_copy(update={"message_text": "Updated text."})
    repository.save_message(original_message)

    repository.save_message(updated_message)

    assert repository.list_messages("thread-1") == [updated_message]


def test_fact_review_repository_saves_and_loads_actions(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_action = build_action(action_id="action-1", thread_id="thread-1")
    second_action = build_action(action_id="action-2", thread_id="thread-2", fact_id="fact-2")
    repository.save_action(first_action)
    repository.save_action(second_action)

    assert repository.actions_path.exists()
    assert repository.list_actions(thread_id="thread-1") == [first_action]
    assert repository.get_action("action-2") == second_action
    assert repository.get_action("missing-action") is None


def test_fact_review_repository_filters_actions(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_action = build_action(action_id="action-1", fact_id="fact-1", role_id="role-1")
    second_action = build_action(action_id="action-2", fact_id="fact-2", role_id="role-2")
    repository.save_action(first_action)
    repository.save_action(second_action)

    assert repository.list_actions(fact_id="fact-1") == [first_action]
    assert repository.list_actions(role_id="role-2") == [second_action]
    assert repository.list_actions(thread_id="missing-thread") == []


def test_fact_review_repository_updates_existing_action_by_id(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    original_action = build_action(action_id="action-1")
    updated_action = build_action(
        action_id="action-1",
        status=FactReviewActionStatus.APPLIED,
    )
    repository.save_action(original_action)

    repository.save_action(updated_action)

    assert repository.list_actions() == [updated_action]


def test_fact_review_repository_snapshots_existing_thread_file(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_thread = build_thread(thread_id="thread-1")
    second_thread = build_thread(thread_id="thread-2")
    repository.save_thread(first_thread)

    repository.save_thread(second_thread)

    snapshots = list(repository.snapshots_dir.glob(f"*-{FACT_REVIEW_THREADS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_threads = THREAD_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_threads == [first_thread]


def test_fact_review_repository_snapshots_existing_message_file(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_message = build_message(message_id="message-1")
    second_message = build_message(message_id="message-2")
    repository.save_message(first_message)

    repository.save_message(second_message)

    snapshots = list(repository.snapshots_dir.glob(f"*-{FACT_REVIEW_MESSAGES_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_messages = MESSAGE_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_messages == [first_message]


def test_fact_review_repository_snapshots_existing_action_file(tmp_path) -> None:
    repository = FactReviewRepository(tmp_path)
    first_action = build_action(action_id="action-1")
    second_action = build_action(action_id="action-2")
    repository.save_action(first_action)

    repository.save_action(second_action)

    snapshots = list(repository.snapshots_dir.glob(f"*-{FACT_REVIEW_ACTIONS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_actions = ACTION_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_actions == [first_action]
