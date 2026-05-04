from __future__ import annotations

from datetime import UTC, datetime

from career_agent.errors import (
    ActiveFactReviewThreadExistsError,
    FactNotFoundError,
    FactReviewThreadNotFoundError,
    InvalidFactReviewThreadStatusTransitionError,
)
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.fact_review.models import (
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
    FactReviewThreadStatus,
)
from career_agent.fact_review.repository import FactReviewRepository

ALLOWED_FACT_REVIEW_THREAD_STATUS_TRANSITIONS: dict[
    FactReviewThreadStatus,
    set[FactReviewThreadStatus],
] = {
    FactReviewThreadStatus.OPEN: {
        FactReviewThreadStatus.RESOLVED,
        FactReviewThreadStatus.ARCHIVED,
    },
    FactReviewThreadStatus.RESOLVED: {FactReviewThreadStatus.ARCHIVED},
    FactReviewThreadStatus.ARCHIVED: set(),
}


class FactReviewService:
    """Application behavior for fact review workflow artifacts."""

    def __init__(
        self,
        review_repository: FactReviewRepository,
        fact_repository: ExperienceFactRepository,
    ) -> None:
        self.review_repository = review_repository
        self.fact_repository = fact_repository

    def list_threads(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewThread]:
        """Return fact review threads, optionally filtered by fact or role."""

        return self.review_repository.list_threads(fact_id=fact_id, role_id=role_id)

    def get_thread(self, thread_id: str) -> FactReviewThread | None:
        """Return one fact review thread if it exists."""

        return self.review_repository.get_thread(thread_id)

    def list_messages(self, thread_id: str) -> list[FactReviewMessage]:
        """Return messages for one fact review thread."""

        return self.review_repository.list_messages(thread_id)

    def start_thread(self, fact_id: str) -> FactReviewThread:
        """Start a fact review thread for an existing fact."""

        fact = self.fact_repository.get(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)

        self.ensure_no_open_thread_for_fact(fact_id)
        thread = FactReviewThread(fact_id=fact.id, role_id=fact.role_id)
        self.review_repository.save_thread(thread)
        return thread

    def add_message(
        self,
        thread_id: str,
        author: FactReviewMessageAuthor,
        message_text: str,
        recommended_action: FactReviewRecommendedAction = FactReviewRecommendedAction.NONE,
    ) -> FactReviewMessage:
        """Append one message to an existing fact review thread."""

        self._get_required_thread(thread_id)
        message = FactReviewMessage(
            thread_id=thread_id,
            author=author,
            message_text=message_text,
            recommended_action=recommended_action,
        )
        self.review_repository.save_message(message)
        return message

    def resolve_thread(self, thread_id: str) -> FactReviewThread:
        """Mark an open fact review thread as resolved."""

        return self._set_thread_status(
            thread_id=thread_id,
            status=FactReviewThreadStatus.RESOLVED,
        )

    def archive_thread(self, thread_id: str) -> FactReviewThread:
        """Archive a fact review thread."""

        return self._set_thread_status(
            thread_id=thread_id,
            status=FactReviewThreadStatus.ARCHIVED,
        )

    def ensure_no_open_thread_for_fact(self, fact_id: str) -> None:
        """Validate that a fact does not already have an open review thread."""

        for thread in self.review_repository.list_threads(fact_id=fact_id):
            if thread.status == FactReviewThreadStatus.OPEN:
                msg = f"Open fact review thread already exists for fact {fact_id}: {thread.id}"
                raise ActiveFactReviewThreadExistsError(msg)

    def _get_required_thread(self, thread_id: str) -> FactReviewThread:
        """Return one fact review thread or raise a domain error."""

        thread = self.review_repository.get_thread(thread_id)
        if thread is None:
            msg = f"Fact review thread does not exist: {thread_id}"
            raise FactReviewThreadNotFoundError(msg)
        return thread

    def _set_thread_status(
        self,
        thread_id: str,
        status: FactReviewThreadStatus,
    ) -> FactReviewThread:
        """Persist an explicit fact review thread status transition."""

        thread = self._get_required_thread(thread_id)
        allowed_statuses = ALLOWED_FACT_REVIEW_THREAD_STATUS_TRANSITIONS[thread.status]
        if status not in allowed_statuses:
            msg = (
                f"Cannot transition fact review thread {thread.id} "
                f"from {thread.status.value} to {status.value}."
            )
            raise InvalidFactReviewThreadStatusTransitionError(msg)

        updated_thread = thread.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.review_repository.save_thread(updated_thread)
        return updated_thread
