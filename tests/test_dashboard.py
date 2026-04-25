from __future__ import annotations

from career_agent.application.dashboard import (
    JobWorkflowState,
    JobWorkflowStatus,
    build_dashboard_sections,
)
from career_agent.application.profile_service import ProfileService
from career_agent.application.status import ComponentStatus, ComponentStatusState
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


def test_build_dashboard_sections_groups_profile_readiness_and_job_workflow() -> None:
    service = ProfileService(FakeProfileRepository())

    sections = build_dashboard_sections(service)

    assert [section.title for section in sections] == [
        "Profile Readiness",
        "Job Workflow",
    ]
    assert [card.title for card in sections[0].cards] == [
        "User Preferences",
        "Career Profile",
    ]
    assert isinstance(sections[0].cards[0].status, ComponentStatus)
    assert isinstance(sections[0].cards[1].status, ComponentStatus)
    assert sections[0].cards[0].status.state == ComponentStatusState.NOT_STARTED
    assert sections[0].cards[1].status.state == ComponentStatusState.NOT_STARTED
    assert sections[0].cards[0].detail == "Press p to complete preferences setup."
    assert sections[0].cards[0].shortcut == "p"

    assert [card.title for card in sections[1].cards] == ["Jobs"]
    assert isinstance(sections[1].cards[0].status, JobWorkflowStatus)
    assert sections[1].cards[0].status.state == JobWorkflowState.IDLE
    assert sections[1].cards[0].detail == "No job URLs queued for analysis."


def test_build_dashboard_sections_uses_real_user_preferences_status() -> None:
    repository = FakeProfileRepository()
    repository.user_preferences = UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )
    service = ProfileService(repository)

    sections = build_dashboard_sections(service)
    user_preferences_card = sections[0].cards[0]

    assert user_preferences_card.status.component == "user_preferences"
    assert user_preferences_card.status.state == ComponentStatusState.PARTIAL
    assert user_preferences_card.detail == "Press p to complete preferences setup."
