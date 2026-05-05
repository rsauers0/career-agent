import pytest

from career_agent.errors import (
    ActiveFactReviewThreadExistsError,
    FactNotFoundError,
    FactReviewActionNotFoundError,
    FactReviewThreadNotFoundError,
    InvalidFactReviewActionStatusTransitionError,
    InvalidFactReviewThreadStatusTransitionError,
)
from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
    FactChangeActor,
)
from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionStatus,
    FactReviewActionType,
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
        self.actions: dict[str, FactReviewAction] = {}

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

    def list_actions(
        self,
        thread_id: str | None = None,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewAction]:
        actions = list(self.actions.values())
        if thread_id is not None:
            actions = [action for action in actions if action.thread_id == thread_id]
        if fact_id is not None:
            actions = [action for action in actions if action.fact_id == fact_id]
        if role_id is not None:
            actions = [action for action in actions if action.role_id == role_id]
        return actions

    def get_action(self, action_id: str) -> FactReviewAction | None:
        return self.actions.get(action_id)

    def save_action(self, action: FactReviewAction) -> None:
        self.actions[action.id] = action


class FakeExperienceFactService:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}
        self.calls: list[tuple[str, FactChangeActor, str | None, list[str]]] = []

    def get_fact(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact

    def activate_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(update={"status": ExperienceFactStatus.ACTIVE})
        self.save(updated_fact)
        self.calls.append(("activate_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def reject_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(update={"status": ExperienceFactStatus.REJECTED})
        self.save(updated_fact)
        self.calls.append(("reject_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def revise_fact(
        self,
        fact_id: str,
        text: str,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        details: list[str] | None = None,
        systems: list[str] | None = None,
        skills: list[str] | None = None,
        functions: list[str] | None = None,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(
            update={
                "text": text,
                "source_ids": [*fact.source_ids, *(source_ids or [])],
                "question_ids": [*fact.question_ids, *(question_ids or [])],
                "message_ids": [*fact.message_ids, *(message_ids or [])],
            }
        )
        self.save(updated_fact)
        self.calls.append(("revise_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def add_evidence(
        self,
        fact_id: str,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(
            update={
                "source_ids": [*fact.source_ids, *(source_ids or [])],
                "question_ids": [*fact.question_ids, *(question_ids or [])],
                "message_ids": [*fact.message_ids, *(message_ids or [])],
            }
        )
        self.save(updated_fact)
        self.calls.append(("add_evidence", actor, summary, source_message_ids or []))
        return updated_fact

    def _get_required_fact(self, fact_id: str) -> ExperienceFact:
        fact = self.get_fact(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)
        return fact


def build_fact(fact_id: str = "fact-1", role_id: str = "role-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        text="Automated reporting workflows.",
    )


def build_service() -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceFactService,
]:
    review_repository = FakeFactReviewRepository()
    fact_service = FakeExperienceFactService()
    return FactReviewService(review_repository, fact_service), review_repository, fact_service


def test_fact_review_service_starts_thread_for_existing_fact() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())

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
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    first_thread = service.start_thread("fact-1")

    with pytest.raises(ActiveFactReviewThreadExistsError, match=first_thread.id):
        service.start_thread("fact-1")


def test_fact_review_service_allows_new_thread_after_resolve() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    first_thread = service.start_thread("fact-1")
    service.resolve_thread(first_thread.id)

    second_thread = service.start_thread("fact-1")

    assert second_thread.id != first_thread.id
    assert second_thread.status == FactReviewThreadStatus.OPEN


def test_fact_review_service_lists_threads() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact(fact_id="fact-1", role_id="role-1"))
    fact_service.save(build_fact(fact_id="fact-2", role_id="role-2"))
    first_thread = service.start_thread("fact-1")
    second_thread = service.start_thread("fact-2")

    assert service.list_threads() == [first_thread, second_thread]
    assert service.list_threads(fact_id="fact-1") == [first_thread]
    assert service.list_threads(role_id="role-2") == [second_thread]


def test_fact_review_service_adds_message_to_thread() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
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
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    resolved_thread = service.resolve_thread(thread.id)
    archived_thread = service.archive_thread(resolved_thread.id)

    assert resolved_thread.status == FactReviewThreadStatus.RESOLVED
    assert archived_thread.status == FactReviewThreadStatus.ARCHIVED
    assert review_repository.get_thread(thread.id) == archived_thread


def test_fact_review_service_rejects_invalid_status_transition() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    archived_thread = service.archive_thread(thread.id)

    with pytest.raises(InvalidFactReviewThreadStatusTransitionError, match="archived"):
        service.resolve_thread(archived_thread.id)


def test_fact_review_service_rejects_status_change_for_missing_thread() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.resolve_thread("thread-1")


def test_fact_review_service_adds_action_from_thread_context() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REVISE_FACT,
        rationale="User clarified the wording.",
        source_message_ids=["message-1"],
        revised_text="Managed reporting workflows.",
    )

    assert action.thread_id == thread.id
    assert action.fact_id == "fact-1"
    assert action.role_id == "role-1"
    assert action.status == FactReviewActionStatus.PROPOSED
    assert action.rationale == "User clarified the wording."
    assert service.list_actions(thread_id=thread.id) == [action]


def test_fact_review_service_rejects_action_for_missing_thread() -> None:
    service, _review_repository, _fact_service = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.add_action(
            thread_id="thread-1",
            action_type=FactReviewActionType.ACTIVATE_FACT,
        )


def test_fact_review_service_applies_activate_action() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
        rationale="Fact is supported.",
        source_message_ids=["review-message-1"],
    )

    applied_action = service.apply_action(action.id, actor=FactChangeActor.LLM)

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert applied_action.applied_fact_id == "fact-1"
    assert review_repository.get_action(action.id) == applied_action
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.ACTIVE
    assert fact_service.calls == [
        (
            "activate_fact",
            FactChangeActor.LLM,
            "Fact is supported.",
            ["review-message-1"],
        )
    ]


def test_fact_review_service_applies_reject_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REJECT_FACT,
    )

    applied_action = service.apply_action(action.id)

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.REJECTED
    assert fact_service.calls[-1][0] == "reject_fact"


def test_fact_review_service_applies_revise_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REVISE_FACT,
        revised_text="Managed Power Platform reporting workflows.",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
    )

    applied_action = service.apply_action(action.id)
    fact = fact_service.get_fact("fact-1")

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact.text == "Managed Power Platform reporting workflows."
    assert fact.source_ids == ["source-1"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact_service.calls[-1][0] == "revise_fact"


def test_fact_review_service_applies_add_evidence_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ADD_EVIDENCE,
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
    )

    applied_action = service.apply_action(action.id)
    fact = fact_service.get_fact("fact-1")

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact.source_ids == ["source-1"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact_service.calls[-1][0] == "add_evidence"


def test_fact_review_service_rejects_apply_for_non_proposed_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )
    service.reject_action(action.id)

    with pytest.raises(InvalidFactReviewActionStatusTransitionError, match="rejected"):
        service.apply_action(action.id)


def test_fact_review_service_rejects_missing_action() -> None:
    service, _review_repository, _fact_service = build_service()

    with pytest.raises(FactReviewActionNotFoundError, match="action-1"):
        service.apply_action("action-1")


def test_fact_review_service_rejects_and_archives_actions() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )

    rejected_action = service.reject_action(action.id)
    archived_action = service.archive_action(action.id)

    assert rejected_action.status == FactReviewActionStatus.REJECTED
    assert archived_action.status == FactReviewActionStatus.ARCHIVED
    assert review_repository.get_action(action.id) == archived_action


def test_fact_review_service_rejects_invalid_action_status_transition() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )
    archived_action = service.archive_action(action.id)

    with pytest.raises(InvalidFactReviewActionStatusTransitionError, match="archived"):
        service.reject_action(archived_action.id)
