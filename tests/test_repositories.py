from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from career_agent.domain.models import CareerProfile, ExperienceEntry, UserPreferences
from career_agent.infrastructure.repositories import FileProfileRepository


def build_user_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        target_job_titles=["Senior Data Engineer"],
        preferred_locations=["Remote", "Chicago, IL"],
        time_zone="America/Chicago",
        desired_salary_min=150000,
        desired_salary_max=190000,
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


def test_load_invalid_profile_json_raises_validation_error(tmp_path: Path) -> None:
    repository = FileProfileRepository(tmp_path)
    repository.profile_dir.mkdir(parents=True, exist_ok=True)
    repository.user_preferences_path.write_text(
        json.dumps({"full_name": "Randy Example"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        repository.load_user_preferences()
