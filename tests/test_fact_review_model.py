import pytest
from pydantic import ValidationError

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
from career_agent.scoped_constraints.models import ConstraintScopeType, ConstraintType


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


def test_fact_review_action_json_round_trip() -> None:
    action = FactReviewAction(
        thread_id="thread-1",
        fact_id="fact-1",
        role_id="role-1",
        action_type=FactReviewActionType.REVISE_FACT,
        rationale="User clarified the wording.",
        source_message_ids=["message-1"],
        revised_text="Managed reporting workflows.",
    )

    restored = FactReviewAction.model_validate_json(action.model_dump_json())

    assert restored == action
    assert restored.id
    assert restored.status == FactReviewActionStatus.PROPOSED


def test_fact_review_action_normalizes_text_and_list_fields() -> None:
    action = FactReviewAction(
        thread_id="  thread-1  ",
        fact_id="  fact-1  ",
        role_id="  role-1  ",
        action_type=FactReviewActionType.ADD_EVIDENCE,
        rationale="  Added source context.  ",
        source_message_ids=["  message-1  ", ""],
        source_ids=["  source-1  ", ""],
        question_ids=["  question-1  "],
        message_ids=["  clarification-message-1  "],
    )

    assert action.thread_id == "thread-1"
    assert action.fact_id == "fact-1"
    assert action.role_id == "role-1"
    assert action.rationale == "Added source context."
    assert action.source_message_ids == ["message-1"]
    assert action.source_ids == ["source-1"]
    assert action.question_ids == ["question-1"]
    assert action.message_ids == ["clarification-message-1"]


def test_fact_review_action_normalizes_constraint_fields() -> None:
    action = FactReviewAction(
        thread_id="thread-1",
        fact_id="fact-1",
        role_id="role-1",
        action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
        constraint_scope_type=ConstraintScopeType.ROLE,
        constraint_scope_id="  role-1  ",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="  Do not describe this role as enterprise-level.  ",
    )

    assert action.constraint_scope_id == "role-1"
    assert action.rule_text == "Do not describe this role as enterprise-level."


def test_fact_review_action_requires_revised_text_for_revise_fact() -> None:
    with pytest.raises(ValidationError, match="revised_text is required"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.REVISE_FACT,
        )


def test_fact_review_action_requires_evidence_for_add_evidence() -> None:
    with pytest.raises(ValidationError, match="at least one evidence reference"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.ADD_EVIDENCE,
        )


def test_fact_review_action_requires_applied_fact_id_when_applied() -> None:
    with pytest.raises(ValidationError, match="applied_fact_id is required"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.ACTIVATE_FACT,
            status=FactReviewActionStatus.APPLIED,
        )


def test_fact_review_action_requires_constraint_fields_for_propose_constraint() -> None:
    with pytest.raises(ValidationError, match="constraint_scope_type is required"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
        )


def test_fact_review_action_rejects_global_constraint_scope_id() -> None:
    with pytest.raises(ValidationError, match="global constraint actions cannot have"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
            constraint_scope_type=ConstraintScopeType.GLOBAL,
            constraint_scope_id="role-1",
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not use em dashes.",
        )


def test_fact_review_action_requires_constraint_scope_id_for_role_constraint() -> None:
    with pytest.raises(ValidationError, match="role constraint actions require"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
            constraint_scope_type=ConstraintScopeType.ROLE,
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not describe this role as enterprise-level.",
        )


def test_fact_review_action_requires_applied_constraint_id_when_applied() -> None:
    with pytest.raises(ValidationError, match="applied_constraint_id is required"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
            constraint_scope_type=ConstraintScopeType.GLOBAL,
            constraint_type=ConstraintType.PREFERENCE,
            rule_text="Prefer direct wording.",
            status=FactReviewActionStatus.APPLIED,
        )


def test_fact_review_action_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timestamp values must be timezone-aware"):
        FactReviewAction(
            thread_id="thread-1",
            fact_id="fact-1",
            role_id="role-1",
            action_type=FactReviewActionType.ACTIVATE_FACT,
            created_at="2026-01-01T00:00:00",
        )
