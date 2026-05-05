import pytest
from pydantic import ValidationError

from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.action_generator import (
    DeterministicFactReviewActionGenerator,
    GeneratedFactReviewAction,
)
from career_agent.fact_review.models import (
    FactReviewActionType,
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
)
from career_agent.scoped_constraints.models import ConstraintScopeType, ConstraintType


def test_generated_fact_review_action_requires_source_message_ids() -> None:
    with pytest.raises(ValidationError, match="source_message_ids"):
        GeneratedFactReviewAction(
            action_type=FactReviewActionType.ACTIVATE_FACT,
            source_message_ids=[],
        )


def test_generated_fact_review_action_validates_revise_shape() -> None:
    with pytest.raises(ValidationError, match="revised_text"):
        GeneratedFactReviewAction(
            action_type=FactReviewActionType.REVISE_FACT,
            source_message_ids=["message-1"],
        )


def test_generated_fact_review_action_validates_add_evidence_shape() -> None:
    with pytest.raises(ValidationError, match="evidence reference"):
        GeneratedFactReviewAction(
            action_type=FactReviewActionType.ADD_EVIDENCE,
            source_message_ids=["message-1"],
        )


def test_generated_fact_review_action_validates_constraint_shape() -> None:
    with pytest.raises(ValidationError, match="constraint_scope_type"):
        GeneratedFactReviewAction(
            action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
            source_message_ids=["message-1"],
            constraint_type=ConstraintType.HARD_RULE,
            rule_text="Do not imply enterprise-wide scope.",
        )

    action = GeneratedFactReviewAction(
        action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
        source_message_ids=["message-1"],
        constraint_scope_type=ConstraintScopeType.GLOBAL,
        constraint_type=ConstraintType.PREFERENCE,
        rule_text="Prefer direct wording.",
    )

    assert action.constraint_scope_type == ConstraintScopeType.GLOBAL
    assert action.constraint_scope_id is None
    assert action.rule_text == "Prefer direct wording."


def test_deterministic_fact_review_action_generator_uses_latest_actionable_recommendation() -> None:
    generator = DeterministicFactReviewActionGenerator()
    role = ExperienceRole(
        id="role-1",
        employer_name="Acme Analytics",
        job_title="Systems Analyst",
        start_date="01/2020",
        end_date="02/2024",
    )
    fact = ExperienceFact(
        id="fact-1",
        role_id="role-1",
        text="Managed reporting workflows.",
    )
    thread = FactReviewThread(
        id="thread-1",
        fact_id="fact-1",
        role_id="role-1",
    )
    messages = [
        FactReviewMessage(
            id="message-1",
            thread_id="thread-1",
            author=FactReviewMessageAuthor.USER,
            message_text="Please split this.",
            recommended_action=FactReviewRecommendedAction.SPLIT_FACT,
        ),
        FactReviewMessage(
            id="message-2",
            thread_id="thread-1",
            author=FactReviewMessageAuthor.USER,
            message_text="Actually, this is ready.",
            recommended_action=FactReviewRecommendedAction.ACTIVATE_FACT,
        ),
    ]

    actions = generator.generate_actions(
        role=role,
        fact=fact,
        thread=thread,
        messages=messages,
        existing_actions=[],
        constraints=[],
    )

    assert len(actions) == 1
    assert actions[0].action_type == FactReviewActionType.ACTIVATE_FACT
    assert actions[0].source_message_ids == ["message-2"]


def test_deterministic_generator_returns_empty_without_actionable_metadata() -> None:
    generator = DeterministicFactReviewActionGenerator()
    role = ExperienceRole(
        id="role-1",
        employer_name="Acme Analytics",
        job_title="Systems Analyst",
        start_date="01/2020",
        end_date="02/2024",
    )
    fact = ExperienceFact(
        id="fact-1",
        role_id="role-1",
        text="Managed reporting workflows.",
    )
    thread = FactReviewThread(
        id="thread-1",
        fact_id="fact-1",
        role_id="role-1",
    )

    actions = generator.generate_actions(
        role=role,
        fact=fact,
        thread=thread,
        messages=[
            FactReviewMessage(
                id="message-1",
                thread_id="thread-1",
                author=FactReviewMessageAuthor.USER,
                message_text="Please revise this.",
                recommended_action=FactReviewRecommendedAction.REVISE_FACT,
            )
        ],
        existing_actions=[],
        constraints=[],
    )

    assert actions == []
