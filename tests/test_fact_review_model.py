import pytest
from pydantic import ValidationError

from career_agent.fact_review.models import (
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
    FactReviewThreadStatus,
)


def test_fact_review_thread_json_round_trip() -> None:
    thread = FactReviewThread(
        fact_id="fact-1",
        role_id="role-1",
        status=FactReviewThreadStatus.RESOLVED,
    )

    restored = FactReviewThread.model_validate_json(thread.model_dump_json())

    assert restored == thread
    assert restored.id


def test_fact_review_thread_defaults_to_open() -> None:
    thread = FactReviewThread(fact_id="fact-1", role_id="role-1")

    assert thread.status == FactReviewThreadStatus.OPEN
    assert thread.created_at.tzinfo is not None
    assert thread.updated_at.tzinfo is not None


def test_fact_review_thread_normalizes_text_fields() -> None:
    thread = FactReviewThread(fact_id="  fact-1  ", role_id="  role-1  ")

    assert thread.fact_id == "fact-1"
    assert thread.role_id == "role-1"


def test_fact_review_thread_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        FactReviewThread(
            fact_id="fact-1",
            role_id="role-1",
            created_at="2026-01-01T00:00:00",
        )


def test_fact_review_message_json_round_trip() -> None:
    message = FactReviewMessage(
        thread_id="thread-1",
        author=FactReviewMessageAuthor.USER,
        message_text="Please split this into two facts.",
        recommended_action=FactReviewRecommendedAction.SPLIT_FACT,
    )

    restored = FactReviewMessage.model_validate_json(message.model_dump_json())

    assert restored == message
    assert restored.id


def test_fact_review_message_defaults_recommended_action_to_none() -> None:
    message = FactReviewMessage(
        thread_id="thread-1",
        author=FactReviewMessageAuthor.USER,
        message_text="Looks good.",
    )

    assert message.recommended_action == FactReviewRecommendedAction.NONE
    assert message.created_at.tzinfo is not None


def test_fact_review_message_normalizes_text_fields() -> None:
    message = FactReviewMessage(
        thread_id="  thread-1  ",
        author=FactReviewMessageAuthor.ASSISTANT,
        message_text="  This fact may need a source.  ",
    )

    assert message.thread_id == "thread-1"
    assert message.message_text == "This fact may need a source."


def test_fact_review_message_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        FactReviewMessage(
            thread_id="thread-1",
            author=FactReviewMessageAuthor.USER,
            message_text="Looks good.",
            created_at="2026-01-01T00:00:00",
        )
