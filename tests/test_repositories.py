from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from career_agent.domain.models import (
    CareerProfile,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    UserPreferences,
    WorkArrangement,
)
from career_agent.infrastructure.repositories import (
    FileExperienceIntakeRepository,
    FileProfileRepository,
)


def build_user_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Chicago, IL"],
        time_zone="America/Chicago",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        desired_salary_min=150000,
        work_authorization=True,
        requires_work_sponsorship=False,
    )


def build_career_profile() -> CareerProfile:
    return CareerProfile(
        core_narrative_notes=["Position as a data platform leader."],
        experience_entries=[
            ExperienceEntry(
                employer_name="Acme Analytics",
                job_title="Senior Data Engineer",
                start_date="05/2021",
                responsibilities=["Owned orchestration and reliability for ETL pipelines."],
            )
        ],
        skills=["data engineering", "technical leadership"],
    )


def build_intake_session(
    session_id: str = "session-123",
    status: ExperienceIntakeStatus = ExperienceIntakeStatus.DRAFT,
) -> ExperienceIntakeSession:
    return ExperienceIntakeSession(
        id=session_id,
        status=status,
        source_text="- Built reporting pipeline",
    )


def test_load_missing_profile_data_returns_none(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)

    assert repository.load_user_preferences() is None
    assert repository.load_career_profile() is None


def test_initialize_profile_storage_creates_expected_directories(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)

    repository.initialize_profile_storage()

    assert repository.profile_dir.exists()
    assert repository.profile_snapshot_dir.exists()


def test_save_and_load_user_preferences_round_trip(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    preferences = build_user_preferences()

    repository.save_user_preferences(preferences)

    assert repository.load_user_preferences() == preferences


def test_save_and_load_career_profile_round_trip(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    profile = build_career_profile()

    repository.save_career_profile(profile)

    assert repository.load_career_profile() == profile


def test_saving_over_existing_profile_creates_snapshot(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    first = build_career_profile()
    second = build_career_profile()
    second.additional_notes = "Updated after review."

    repository.save_career_profile(first)
    repository.save_career_profile(second)

    snapshots = sorted((tmp_path / "snapshots" / "profile").glob("career_profile-*.json"))

    assert len(snapshots) == 1
    snapshot_profile = CareerProfile.model_validate_json(snapshots[0].read_text(encoding="utf-8"))
    assert snapshot_profile == first


def test_saving_over_existing_user_preferences_creates_snapshot(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    first = build_user_preferences()
    second = build_user_preferences()
    second.target_job_titles = ["Systems Analyst"]

    repository.save_user_preferences(first)
    repository.save_user_preferences(second)

    snapshots = sorted((tmp_path / "snapshots" / "profile").glob("user_preferences-*.json"))

    assert len(snapshots) == 1
    snapshot_preferences = UserPreferences.model_validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshot_preferences == first


def test_load_invalid_profile_json_raises_validation_error(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    repository.profile_dir.mkdir(parents=True, exist_ok=True)
    repository.user_preferences_path.write_text(
        json.dumps({"full_name": "Randy Example"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        repository.load_user_preferences()


def test_load_missing_experience_intake_session_returns_none(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)

    assert repository.load_session("missing") is None


def test_experience_intake_session_ids_must_be_file_safe(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)

    with pytest.raises(ValueError, match="file-safe identifier"):
        repository.load_session("../outside")

    with pytest.raises(ValueError, match="file-safe identifier"):
        repository.save_session(build_intake_session("nested/session"))


def test_save_and_load_experience_intake_session_round_trip(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    session = build_intake_session()

    repository.save_session(session)

    assert repository.load_session(session.id) == session


def test_list_experience_intake_sessions_sorted_by_updated_at(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    older = build_intake_session("older")
    newer = build_intake_session("newer")
    newer.updated_at = newer.updated_at.replace(year=older.updated_at.year + 1)

    repository.save_session(older)
    repository.save_session(newer)

    assert [session.id for session in repository.list_sessions()] == ["newer", "older"]


def test_list_experience_intake_sessions_by_status(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    draft = build_intake_session("draft", ExperienceIntakeStatus.DRAFT)
    captured = build_intake_session("captured", ExperienceIntakeStatus.SOURCE_CAPTURED)

    repository.save_session(draft)
    repository.save_session(captured)

    sessions = repository.list_sessions_by_status(ExperienceIntakeStatus.SOURCE_CAPTURED)

    assert sessions == [captured]


def test_saving_over_existing_experience_intake_session_creates_snapshot(
    tmp_path: Path,
) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    first = build_intake_session()
    second = first.model_copy(
        update={
            "source_text": "- Built reporting pipeline\n- Added alerting",
            "status": ExperienceIntakeStatus.SOURCE_CAPTURED,
        }
    )

    repository.save_session(first)
    repository.save_session(second)

    snapshots = sorted(
        (tmp_path / "snapshots" / "intake" / "experience").glob("session-123-*.json")
    )

    assert len(snapshots) == 1
    snapshot_session = ExperienceIntakeSession.model_validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshot_session == first


def test_delete_experience_intake_session_removes_file_and_creates_snapshot(
    tmp_path: Path,
) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    session = build_intake_session()

    repository.save_session(session)

    assert repository.delete_session(session.id) is True
    assert repository.load_session(session.id) is None

    snapshots = sorted(
        (tmp_path / "snapshots" / "intake" / "experience").glob("session-123-*.json")
    )
    assert len(snapshots) == 1
    snapshot_session = ExperienceIntakeSession.model_validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshot_session == session


def test_delete_missing_experience_intake_session_returns_false(tmp_path: Path) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)

    assert repository.delete_session("missing") is False


def test_load_invalid_experience_intake_session_json_raises_validation_error(
    tmp_path: Path,
) -> None:
    repository = FileExperienceIntakeRepository(tmp_path)
    repository.session_dir.mkdir(parents=True, exist_ok=True)
    repository._session_path("invalid").write_text(
        json.dumps({"status": "not-real"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        repository.load_session("invalid")
