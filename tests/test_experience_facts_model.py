import pytest
from pydantic import ValidationError

from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
)


def test_experience_fact_json_round_trip() -> None:
    fact = ExperienceFact(
        role_id="role-1",
        source_ids=["source-1", "source-2"],
        question_ids=["question-1"],
        message_ids=["message-1"],
        text="Automated reporting workflows, reducing manual reconciliation time.",
        details=["Supported recurring monthly reconciliation."],
        systems=["Power Platform"],
        skills=["Power Automate"],
        functions=["workflow automation"],
        supersedes_fact_id="fact-0",
        superseded_by_fact_id="fact-2",
        status=ExperienceFactStatus.ACTIVE,
    )

    restored = ExperienceFact.model_validate_json(fact.model_dump_json())

    assert restored == fact
    assert restored.id


def test_experience_fact_defaults_to_draft() -> None:
    fact = ExperienceFact(
        role_id="role-1",
        text="Automated reporting workflows, reducing manual reconciliation time.",
    )

    assert fact.status == ExperienceFactStatus.DRAFT
    assert fact.source_ids == []
    assert fact.question_ids == []
    assert fact.message_ids == []
    assert fact.details == []
    assert fact.systems == []
    assert fact.skills == []
    assert fact.functions == []
    assert fact.supersedes_fact_id is None
    assert fact.superseded_by_fact_id is None
    assert fact.created_at.tzinfo is not None
    assert fact.updated_at.tzinfo is not None


def test_experience_fact_normalizes_text_fields() -> None:
    fact = ExperienceFact(
        role_id="  role-1  ",
        source_ids=["  source-1  ", "", "  source-2  "],
        question_ids=["  question-1  ", ""],
        message_ids=["  message-1  ", ""],
        text="  Automated reporting workflows.  ",
        details=["  Reduced manual reconciliation.  ", ""],
        systems=["  Power Platform  ", ""],
        skills=["  Power Automate  ", ""],
        functions=["  workflow automation  ", ""],
        supersedes_fact_id="  fact-0  ",
        superseded_by_fact_id="  fact-2  ",
    )

    assert fact.role_id == "role-1"
    assert fact.source_ids == ["source-1", "source-2"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact.text == "Automated reporting workflows."
    assert fact.details == ["Reduced manual reconciliation."]
    assert fact.systems == ["Power Platform"]
    assert fact.skills == ["Power Automate"]
    assert fact.functions == ["workflow automation"]
    assert fact.supersedes_fact_id == "fact-0"
    assert fact.superseded_by_fact_id == "fact-2"


def test_experience_fact_supports_superseded_status() -> None:
    fact = ExperienceFact(
        role_id="role-1",
        text="Automated reporting workflows.",
        status=ExperienceFactStatus.SUPERSEDED,
        superseded_by_fact_id="fact-2",
    )

    assert fact.status == ExperienceFactStatus.SUPERSEDED
    assert fact.superseded_by_fact_id == "fact-2"


def test_experience_fact_supports_review_statuses() -> None:
    needs_clarification_fact = ExperienceFact(
        role_id="role-1",
        text="Automated reporting workflows.",
        status=ExperienceFactStatus.NEEDS_CLARIFICATION,
    )
    rejected_fact = ExperienceFact(
        role_id="role-1",
        text="Automated reporting workflows.",
        status=ExperienceFactStatus.REJECTED,
    )

    assert needs_clarification_fact.status == ExperienceFactStatus.NEEDS_CLARIFICATION
    assert rejected_fact.status == ExperienceFactStatus.REJECTED


def test_experience_fact_requires_role_id() -> None:
    with pytest.raises(ValidationError):
        ExperienceFact(
            role_id="",
            text="Automated reporting workflows.",
        )


def test_experience_fact_requires_text() -> None:
    with pytest.raises(ValidationError):
        ExperienceFact(
            role_id="role-1",
            text="   ",
        )


def test_experience_fact_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ExperienceFact(
            role_id="role-1",
            text="Automated reporting workflows.",
            created_at="2026-01-01T00:00:00",
        )
