from career_agent.user_preferences.models import UserPreferences, WorkArrangement
from career_agent.user_preferences.repository import (
    SNAPSHOTS_DIRNAME,
    USER_PREFERENCES_DIRNAME,
    USER_PREFERENCES_FILENAME,
    UserPreferencesRepository,
)


def test_user_preferences_repository_builds_storage_paths(tmp_path) -> None:
    repository = UserPreferencesRepository(tmp_path)

    assert repository.preferences_dir == tmp_path / USER_PREFERENCES_DIRNAME
    assert repository.preferences_path == (
        tmp_path / USER_PREFERENCES_DIRNAME / USER_PREFERENCES_FILENAME
    )
    assert repository.snapshots_dir == (tmp_path / SNAPSHOTS_DIRNAME / USER_PREFERENCES_DIRNAME)


def test_user_preferences_repository_saves_preferences_json(tmp_path) -> None:
    repository = UserPreferencesRepository(tmp_path)
    preferences = UserPreferences(
        full_name="John Doe",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )

    repository.save(preferences)

    assert repository.preferences_path.exists()
    restored = UserPreferences.model_validate_json(repository.preferences_path.read_text())
    assert restored == preferences


def test_user_preferences_repository_load_returns_none_when_missing(tmp_path) -> None:
    repository = UserPreferencesRepository(tmp_path)

    assert repository.load() is None


def test_user_preferences_repository_loads_saved_preferences(tmp_path) -> None:
    repository = UserPreferencesRepository(tmp_path)
    preferences = UserPreferences(
        full_name="John Doe",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )
    repository.save(preferences)

    assert repository.load() == preferences


def test_user_preferences_repository_snapshots_existing_file_before_overwrite(
    tmp_path,
) -> None:
    repository = UserPreferencesRepository(tmp_path)
    first_preferences = UserPreferences(
        full_name="John Doe",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )
    second_preferences = UserPreferences(
        full_name="John Updated",
        base_location="Chicago, IL 60601",
        preferred_work_arrangements=[WorkArrangement.HYBRID],
        work_authorization=True,
        requires_work_sponsorship=False,
    )
    repository.save(first_preferences)

    repository.save(second_preferences)

    snapshots = list(repository.snapshots_dir.glob(f"*-{USER_PREFERENCES_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_preferences = UserPreferences.model_validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_preferences == first_preferences
    assert repository.load() == second_preferences
