import pytest

from career_agent.errors import (
    ActiveFactReviewThreadExistsError,
    FactNotFoundError,
    FactReviewThreadNotFoundError,
    InvalidFactReviewThreadStatusTransitionError,
)
from career_agent.experience_facts.models import ExperienceFact
from career_agent.fact_review.models import (
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
    FactReviewThreadStatus,
)
from career_agent.fact_review.service import FactReviewService


class FakeFactReviewRepository:
    def __init__(self) -> None:
        self.threads: dict[str, FactReviewThread] = {}
        self.messages: dict[str, FactReviewMessage] = {}

    def list_threads(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewThread]:
        threads = list(self.threads.values())
        if fact_id is not None:
            threads = [thread for thread in threads if thread.fact_id == fact_id]
        if role_id is not None:
            threads = [thread for thread in threads if thread.role_id == role_id]
        return threads

    def get_thread(self, thread_id: str) -> FactReviewThread | None:
        return self.threads.get(thread_id)

    def save_thread(self, thread: FactReviewThread) -> None:
        self.threads[thread.id] = thread

    def list_messages(self, thread_id: str) -> list[FactReviewMessage]:
        return [message for message in self.messages.values() if message.thread_id == thread_id]

    def save_message(self, message: FactReviewMessage) -> None:
        self.messages[message.id] = message


class FakeExperienceFactRepository:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}

    def get(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact


def build_fact(fact_id: str = "fact-1", role_id: str = "role-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        text="Automated reporting workflows.",
    )


def build_service() -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceFactRepository,
]:
    review_repository = FakeFactReviewRepository()
    fact_repository = FakeExperienceFactRepository()
    return FactReviewService(review_repository, fact_repository), review_repository, fact_repository


def test_fact_review_service_starts_thread_for_existing_fact() -> None:
    service, review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())

    thread = service.start_thread("fact-1")

    assert thread.fact_id == "fact-1"
    assert thread.role_id == "role-1"
    assert thread.status == FactReviewThreadStatus.OPEN
    assert review_repository.get_thread(thread.id) == thread


def test_fact_review_service_rejects_missing_fact() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactNotFoundError, match="fact-1"):
        service.start_thread("fact-1")


def test_fact_review_service_rejects_second_open_thread_for_fact() -> None:
    service, _review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())
    first_thread = service.start_thread("fact-1")

    with pytest.raises(ActiveFactReviewThreadExistsError, match=first_thread.id):
        service.start_thread("fact-1")


def test_fact_review_service_allows_new_thread_after_resolve() -> None:
    service, _review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())
    first_thread = service.start_thread("fact-1")
    service.resolve_thread(first_thread.id)

    second_thread = service.start_thread("fact-1")

    assert second_thread.id != first_thread.id
    assert second_thread.status == FactReviewThreadStatus.OPEN


def test_fact_review_service_lists_threads() -> None:
    service, _review_repository, fact_repository = build_service()
    fact_repository.save(build_fact(fact_id="fact-1", role_id="role-1"))
    fact_repository.save(build_fact(fact_id="fact-2", role_id="role-2"))
    first_thread = service.start_thread("fact-1")
    second_thread = service.start_thread("fact-2")

    assert service.list_threads() == [first_thread, second_thread]
    assert service.list_threads(fact_id="fact-1") == [first_thread]
    assert service.list_threads(role_id="role-2") == [second_thread]


def test_fact_review_service_adds_message_to_thread() -> None:
    service, _review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())
    thread = service.start_thread("fact-1")

    message = service.add_message(
        thread_id=thread.id,
        author=FactReviewMessageAuthor.USER,
        message_text="Please split this into two facts.",
        recommended_action=FactReviewRecommendedAction.SPLIT_FACT,
    )

    assert message.thread_id == thread.id
    assert message.author == FactReviewMessageAuthor.USER
    assert message.message_text == "Please split this into two facts."
    assert message.recommended_action == FactReviewRecommendedAction.SPLIT_FACT
    assert service.list_messages(thread.id) == [message]


def test_fact_review_service_rejects_message_for_missing_thread() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.add_message(
            thread_id="thread-1",
            author=FactReviewMessageAuthor.USER,
            message_text="Looks good.",
        )


def test_fact_review_service_resolves_and_archives_thread() -> None:
    service, review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())
    thread = service.start_thread("fact-1")

    resolved_thread = service.resolve_thread(thread.id)
    archived_thread = service.archive_thread(resolved_thread.id)

    assert resolved_thread.status == FactReviewThreadStatus.RESOLVED
    assert archived_thread.status == FactReviewThreadStatus.ARCHIVED
    assert review_repository.get_thread(thread.id) == archived_thread


def test_fact_review_service_rejects_invalid_status_transition() -> None:
    service, _review_repository, fact_repository = build_service()
    fact_repository.save(build_fact())
    thread = service.start_thread("fact-1")
    archived_thread = service.archive_thread(thread.id)

    with pytest.raises(InvalidFactReviewThreadStatusTransitionError, match="archived"):
        service.resolve_thread(archived_thread.id)


def test_fact_review_service_rejects_status_change_for_missing_thread() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.resolve_thread("thread-1")
