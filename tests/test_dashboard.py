from __future__ import annotations

from career_agent.application.dashboard import build_dashboard_statuses
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatusState
from career_agent.domain.models import CareerProfile, UserPreferences, WorkArrangement


class FakeProfileRepository:
    def __init__(self) -> None:
        self.user_preferences: UserPreferences | None = None

    def profile_storage_initialized(self) -> bool:
        return True

    def initialize_profile_storage(self) -> None:
        pass

    def load_user_preferences(self) -> UserPreferences | None:
        return self.user_preferences

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        self.user_preferences = preferences

    def load_career_profile(self) -> CareerProfile | None:
        return None

    def save_career_profile(self, profile: CareerProfile) -> None:
        pass


def test_build_dashboard_statuses_includes_all_initial_components() -> None:
    service = ProfileService(FakeProfileRepository())

    statuses = build_dashboard_statuses(service)

    assert [status.component for status in statuses] == [
        "user_preferences",
        "career_profile",
        "experience",
        "jobs",
        "documents",
    ]
    assert [status.state for status in statuses] == [
        ComponentStatusState.NOT_STARTED,
        ComponentStatusState.NOT_STARTED,
        ComponentStatusState.NOT_STARTED,
        ComponentStatusState.NOT_STARTED,
        ComponentStatusState.NOT_STARTED,
    ]


def test_build_dashboard_statuses_uses_real_user_preferences_status() -> None:
    repository = FakeProfileRepository()
    repository.user_preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )
    service = ProfileService(repository)

    statuses = build_dashboard_statuses(service)

    assert statuses[0].component == "user_preferences"
    assert statuses[0].state == ComponentStatusState.PARTIAL
