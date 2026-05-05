import pytest
from pydantic import ValidationError

from career_agent.errors import InvalidLLMOutputError
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.action_generator import (
    DeterministicFactReviewActionGenerator,
    GeneratedFactReviewAction,
    LLMFactReviewActionGenerator,
)
from career_agent.fact_review.models import (
    FactReviewActionType,
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
)
from career_agent.llm.client import FakeLLMClient
from career_agent.scoped_constraints.models import ConstraintScopeType, ConstraintType


def build_role() -> ExperienceRole:
    return ExperienceRole(
        id="role-1",
        employer_name="Acme Analytics",
        job_title="Systems Analyst",
        start_date="01/2020",
        end_date="02/2024",
    )


def build_fact() -> ExperienceFact:
    return ExperienceFact(
        id="fact-1",
        role_id="role-1",
        source_ids=["source-1"],
        text="Managed reporting workflows.",
        details=["Weekly leadership reporting."],
    )


def build_thread() -> FactReviewThread:
    return FactReviewThread(
        id="thread-1",
        fact_id="fact-1",
        role_id="role-1",
    )


def build_message() -> FactReviewMessage:
    return FactReviewMessage(
        id="message-1",
        thread_id="thread-1",
        author=FactReviewMessageAuthor.USER,
        message_text="Looks good to me.",
        recommended_action=FactReviewRecommendedAction.ACTIVATE_FACT,
    )


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
    role = build_role()
    fact = build_fact()
    thread = build_thread()
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
    role = build_role()
    fact = build_fact()
    thread = build_thread()

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


def test_llm_fact_review_action_generator_parses_wrapped_action_json() -> None:
    client = FakeLLMClient(
        response_content="""
        {
          "actions": [
            {
              "action_type": "activate_fact",
              "rationale": "The user explicitly agreed with the fact.",
              "source_message_ids": ["message-1"],
              "revised_text": null,
              "source_ids": [],
              "question_ids": [],
              "message_ids": [],
              "constraint_scope_type": null,
              "constraint_scope_id": null,
              "constraint_type": null,
              "rule_text": null
            }
          ]
        }
        """
    )
    generator = LLMFactReviewActionGenerator(client, model="fake-model", temperature=0.1)

    actions = generator.generate_actions(
        role=build_role(),
        fact=build_fact(),
        thread=build_thread(),
        messages=[build_message()],
        existing_actions=[],
        constraints=[],
    )

    assert generator.generator_name == "llm"
    assert actions == [
        GeneratedFactReviewAction(
            action_type=FactReviewActionType.ACTIVATE_FACT,
            rationale="The user explicitly agreed with the fact.",
            source_message_ids=["message-1"],
        )
    ]
    assert len(client.requests) == 1
    assert client.requests[0].model == "fake-model"
    assert client.requests[0].temperature == 0.1
    assert "Fact ID: fact-1" in client.requests[0].user_prompt
    assert "Message ID: message-1" in client.requests[0].user_prompt
    assert "Allowed action_type values" in client.requests[0].system_prompt


def test_llm_fact_review_action_generator_allows_empty_actions() -> None:
    generator = LLMFactReviewActionGenerator(FakeLLMClient(response_content='{"actions": []}'))

    actions = generator.generate_actions(
        role=build_role(),
        fact=build_fact(),
        thread=build_thread(),
        messages=[build_message()],
        existing_actions=[],
        constraints=[],
    )

    assert actions == []


def test_llm_fact_review_action_generator_allows_multiple_actions() -> None:
    generator = LLMFactReviewActionGenerator(
        FakeLLMClient(
            response_content="""
            {
              "actions": [
                {
                  "action_type": "revise_fact",
                  "rationale": "The user clarified the scope.",
                  "source_message_ids": ["message-1"],
                  "revised_text": "Managed weekly reporting workflows.",
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": null,
                  "constraint_scope_id": null,
                  "constraint_type": null,
                  "rule_text": null
                },
                {
                  "action_type": "propose_constraint",
                  "rationale": "The user stated a durable role rule.",
                  "source_message_ids": ["message-1"],
                  "revised_text": null,
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": "role",
                  "constraint_scope_id": "role-1",
                  "constraint_type": "hard_rule",
                  "rule_text": "Do not describe this role as enterprise-level."
                }
              ]
            }
            """
        )
    )

    actions = generator.generate_actions(
        role=build_role(),
        fact=build_fact(),
        thread=build_thread(),
        messages=[build_message()],
        existing_actions=[],
        constraints=[],
    )

    assert len(actions) == 2
    assert actions[0].action_type == FactReviewActionType.REVISE_FACT
    assert actions[0].revised_text == "Managed weekly reporting workflows."
    assert actions[1].action_type == FactReviewActionType.PROPOSE_CONSTRAINT
    assert actions[1].constraint_scope_type == ConstraintScopeType.ROLE
    assert actions[1].constraint_scope_id == "role-1"
    assert actions[1].constraint_type == ConstraintType.HARD_RULE


def test_llm_fact_review_action_generator_parses_fenced_action_json() -> None:
    generator = LLMFactReviewActionGenerator(
        FakeLLMClient(
            response_content="""
            ```json
            {
              "actions": [
                {
                  "action_type": "reject_fact",
                  "rationale": "The user rejected the fact.",
                  "source_message_ids": ["message-1"],
                  "revised_text": null,
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": null,
                  "constraint_scope_id": null,
                  "constraint_type": null,
                  "rule_text": null
                }
              ]
            }
            ```
            """
        )
    )

    actions = generator.generate_actions(
        role=build_role(),
        fact=build_fact(),
        thread=build_thread(),
        messages=[build_message()],
        existing_actions=[],
        constraints=[],
    )

    assert len(actions) == 1
    assert actions[0].action_type == FactReviewActionType.REJECT_FACT


def test_llm_fact_review_action_generator_rejects_invalid_json() -> None:
    generator = LLMFactReviewActionGenerator(FakeLLMClient(response_content="not json"))

    with pytest.raises(InvalidLLMOutputError, match="valid JSON"):
        generator.generate_actions(
            role=build_role(),
            fact=build_fact(),
            thread=build_thread(),
            messages=[build_message()],
            existing_actions=[],
            constraints=[],
        )


def test_llm_fact_review_action_generator_rejects_malformed_contract() -> None:
    generator = LLMFactReviewActionGenerator(
        FakeLLMClient(response_content='{"actions": [{"action_type": "split_fact"}]}')
    )

    with pytest.raises(InvalidLLMOutputError, match="fact review action contract"):
        generator.generate_actions(
            role=build_role(),
            fact=build_fact(),
            thread=build_thread(),
            messages=[build_message()],
            existing_actions=[],
            constraints=[],
        )


def test_llm_fact_review_action_generator_rejects_unknown_message_id() -> None:
    generator = LLMFactReviewActionGenerator(
        FakeLLMClient(
            response_content="""
            {
              "actions": [
                {
                  "action_type": "activate_fact",
                  "rationale": "Unknown message.",
                  "source_message_ids": ["message-2"],
                  "revised_text": null,
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": null,
                  "constraint_scope_id": null,
                  "constraint_type": null,
                  "rule_text": null
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="message-2"):
        generator.generate_actions(
            role=build_role(),
            fact=build_fact(),
            thread=build_thread(),
            messages=[build_message()],
            existing_actions=[],
            constraints=[],
        )


def test_llm_fact_review_action_generator_rejects_duplicates() -> None:
    generator = LLMFactReviewActionGenerator(
        FakeLLMClient(
            response_content="""
            {
              "actions": [
                {
                  "action_type": "activate_fact",
                  "rationale": "First.",
                  "source_message_ids": ["message-1"],
                  "revised_text": null,
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": null,
                  "constraint_scope_id": null,
                  "constraint_type": null,
                  "rule_text": null
                },
                {
                  "action_type": "activate_fact",
                  "rationale": "Second.",
                  "source_message_ids": ["message-1"],
                  "revised_text": null,
                  "source_ids": [],
                  "question_ids": [],
                  "message_ids": [],
                  "constraint_scope_type": null,
                  "constraint_scope_id": null,
                  "constraint_type": null,
                  "rule_text": null
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="duplicate"):
        generator.generate_actions(
            role=build_role(),
            fact=build_fact(),
            thread=build_thread(),
            messages=[build_message()],
            existing_actions=[],
            constraints=[],
        )
