from career_agent.user_preferences.models import UserPreferences, WorkArrangement
from career_agent.user_preferences.service import UserPreferencesService


class FakeUserPreferencesRepository:
    def __init__(self) -> None:
        self.preferences: UserPreferences | None = None

    def load(self) -> UserPreferences | None:
        return self.preferences

    def save(self, preferences: UserPreferences) -> None:
        self.preferences = preferences


def build_preferences() -> UserPreferences:
    return UserPreferences(
        full_name="Randy Example",
        base_location="Aurora, IL 60504",
        preferred_work_arrangements=[WorkArrangement.REMOTE],
        work_authorization=True,
        requires_work_sponsorship=False,
    )


def test_user_preferences_service_returns_none_when_missing() -> None:
    repository = FakeUserPreferencesRepository()
    service = UserPreferencesService(repository)

    assert service.get_preferences() is None


def test_user_preferences_service_saves_and_returns_preferences() -> None:
    repository = FakeUserPreferencesRepository()
    service = UserPreferencesService(repository)
    preferences = build_preferences()

    service.save_preferences(preferences)

    assert service.get_preferences() == preferences
