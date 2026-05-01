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
        text="Automated reporting workflows, reducing manual reconciliation time.",
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
    assert fact.created_at.tzinfo is not None
    assert fact.updated_at.tzinfo is not None


def test_experience_fact_normalizes_text_fields() -> None:
    fact = ExperienceFact(
        role_id="  role-1  ",
        source_ids=["  source-1  ", "", "  source-2  "],
        text="  Automated reporting workflows.  ",
    )

    assert fact.role_id == "role-1"
    assert fact.source_ids == ["source-1", "source-2"]
    assert fact.text == "Automated reporting workflows."


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
