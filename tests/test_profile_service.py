from __future__ import annotations

from career_agent.application.profile_service import ProfileService
from career_agent.domain.models import CareerProfile, ExperienceEntry, UserPreferences


class FakeProfileRepository:
    def __init__(self) -> None:
        self.storage_initialized = False
        self.user_preferences: UserPreferences | None = None
        self.career_profile: CareerProfile | None = None

    def profile_storage_initialized(self) -> bool:
        return self.storage_initialized

    def initialize_profile_storage(self) -> None:
        self.storage_initialized = True

    def load_user_preferences(self) -> UserPreferences | None:
        return self.user_preferences

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        self.user_preferences = preferences

    def load_career_profile(self) -> CareerProfile | None:
        return self.career_profile

    def save_career_profile(self, profile: CareerProfile) -> None:
        self.career_profile = profile


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


def test_get_user_preferences_returns_repository_value() -> None:
    repository = FakeProfileRepository()
    preferences = build_user_preferences()
    repository.user_preferences = preferences
    service = ProfileService(repository)

    assert service.get_user_preferences() == preferences


def test_initialize_profile_storage_delegates_to_repository() -> None:
    repository = FakeProfileRepository()
    service = ProfileService(repository)

    service.initialize_profile_storage()

    assert repository.storage_initialized is True


def test_save_user_preferences_persists_to_repository() -> None:
    repository = FakeProfileRepository()
    service = ProfileService(repository)
    preferences = build_user_preferences()

    service.save_user_preferences(preferences)

    assert repository.user_preferences == preferences


def test_get_career_profile_returns_repository_value() -> None:
    repository = FakeProfileRepository()
    profile = build_career_profile()
    repository.career_profile = profile
    service = ProfileService(repository)

    assert service.get_career_profile() == profile


def test_save_career_profile_persists_to_repository() -> None:
    repository = FakeProfileRepository()
    service = ProfileService(repository)
    profile = build_career_profile()

    service.save_career_profile(profile)

    assert repository.career_profile == profile
