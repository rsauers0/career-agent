import pytest
from pydantic import ValidationError

from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus


def test_role_source_entry_json_round_trip() -> None:
    source = RoleSourceEntry(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
        status=RoleSourceStatus.ANALYZED,
    )

    restored = RoleSourceEntry.model_validate_json(source.model_dump_json())

    assert restored == source
    assert restored.id


def test_role_source_entry_defaults_to_not_analyzed() -> None:
    source = RoleSourceEntry(
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )

    assert source.status == RoleSourceStatus.NOT_ANALYZED
    assert source.created_at.tzinfo is not None


def test_role_source_entry_normalizes_role_id_only() -> None:
    source_text = "  - Keep this exact source text, including outer spacing.  "

    source = RoleSourceEntry(
        role_id="  role-1  ",
        source_text=source_text,
    )

    assert source.role_id == "role-1"
    assert source.source_text == source_text


def test_role_source_entry_requires_role_id() -> None:
    with pytest.raises(ValidationError):
        RoleSourceEntry(
            role_id="",
            source_text="- Led a reporting automation project.",
        )


def test_role_source_entry_rejects_blank_source_text() -> None:
    with pytest.raises(ValidationError, match="source_text"):
        RoleSourceEntry(
            role_id="role-1",
            source_text="   ",
        )


def test_role_source_entry_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        RoleSourceEntry(
            role_id="role-1",
            source_text="- Led a reporting automation project.",
            created_at="2026-01-01T00:00:00",
        )
