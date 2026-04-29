import pytest
from pydantic import ValidationError

from career_agent.experience_bullets.models import (
    ExperienceBullet,
    ExperienceBulletStatus,
)


def test_experience_bullet_json_round_trip() -> None:
    bullet = ExperienceBullet(
        role_id="role-1",
        source_ids=["source-1", "source-2"],
        text="Automated reporting workflows, reducing manual reconciliation time.",
        status=ExperienceBulletStatus.ACTIVE,
    )

    restored = ExperienceBullet.model_validate_json(bullet.model_dump_json())

    assert restored == bullet
    assert restored.id


def test_experience_bullet_defaults_to_draft() -> None:
    bullet = ExperienceBullet(
        role_id="role-1",
        text="Automated reporting workflows, reducing manual reconciliation time.",
    )

    assert bullet.status == ExperienceBulletStatus.DRAFT
    assert bullet.source_ids == []
    assert bullet.created_at.tzinfo is not None
    assert bullet.updated_at.tzinfo is not None


def test_experience_bullet_normalizes_text_fields() -> None:
    bullet = ExperienceBullet(
        role_id="  role-1  ",
        source_ids=["  source-1  ", "", "  source-2  "],
        text="  Automated reporting workflows.  ",
    )

    assert bullet.role_id == "role-1"
    assert bullet.source_ids == ["source-1", "source-2"]
    assert bullet.text == "Automated reporting workflows."


def test_experience_bullet_requires_role_id() -> None:
    with pytest.raises(ValidationError):
        ExperienceBullet(
            role_id="",
            text="Automated reporting workflows.",
        )


def test_experience_bullet_requires_text() -> None:
    with pytest.raises(ValidationError):
        ExperienceBullet(
            role_id="role-1",
            text="   ",
        )


def test_experience_bullet_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ExperienceBullet(
            role_id="role-1",
            text="Automated reporting workflows.",
            created_at="2026-01-01T00:00:00",
        )
