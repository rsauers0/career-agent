from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from career_agent.application.experience_intake_service import ExperienceIntakeService
from career_agent.application.profile_service import ProfileService
from career_agent.domain.models import CareerProfile
from career_agent.interfaces.tui_experience import ExperienceIntakeScreen


@dataclass(frozen=True)
class CareerProfileSummary:
    """Small display summary for the canonical career profile."""

    experience_count: int
    education_count: int
    certification_count: int
    skills_count: int
    tools_count: int


def build_career_profile_summary(
    profile: CareerProfile | None,
) -> CareerProfileSummary:
    """Build count-based overview data for the profile screen."""

    if profile is None:
        return CareerProfileSummary(
            experience_count=0,
            education_count=0,
            certification_count=0,
            skills_count=0,
            tools_count=0,
        )

    return CareerProfileSummary(
        experience_count=len(profile.experience_entries),
        education_count=len(profile.education_entries),
        certification_count=len(profile.certification_entries),
        skills_count=len(profile.skills),
        tools_count=len(profile.tools_and_technologies),
    )


class ProfileMetricCard(Static):
    """Small card for one Career Profile overview metric."""

    def __init__(self, label: str, value: int, help_text: str) -> None:
        super().__init__()
        self.label = label
        self.value = value
        self.help_text = help_text

    def compose(self) -> ComposeResult:
        yield Static(str(self.value), classes="metric-value")
        yield Static(self.label, classes="metric-label")
        yield Static(self.help_text, classes="status-detail")


class CareerProfileScreen(Screen[None]):
    """Career Profile overview and workflow entry screen."""

    BINDINGS: ClassVar[list[tuple[str, str, str] | Binding]] = [
        ("b", "back", "Back"),
        ("escape", "back", "Back"),
        Binding("e", "open_experience", "Experience"),
    ]

    def __init__(
        self,
        profile_service: ProfileService,
        experience_intake_service: ExperienceIntakeService,
    ) -> None:
        super().__init__()
        self.profile_service = profile_service
        self.experience_intake_service = experience_intake_service

    def compose(self) -> ComposeResult:
        profile = self.profile_service.get_career_profile()
        preferences = self.profile_service.get_user_preferences()
        summary = build_career_profile_summary(profile)

        yield Header(show_clock=True)
        with Container(id="career-profile-screen"):
            yield Static("Career Profile", id="screen-title")
            yield Static(
                (
                    "Review the structured profile that will eventually power job analysis, "
                    "resumes, and cover letters."
                ),
                classes="help-text",
            )

            if preferences is None:
                yield Static(
                    (
                        "User Preferences have not been saved yet. Complete preferences first "
                        "so profile workflows have basic targeting context."
                    ),
                    classes="message-error",
                )

            with Horizontal(id="profile-metrics"):
                yield ProfileMetricCard(
                    "Experience",
                    summary.experience_count,
                    "Accepted role entries in the canonical profile.",
                )
                yield ProfileMetricCard(
                    "Education",
                    summary.education_count,
                    "Education records will be managed separately.",
                )
                yield ProfileMetricCard(
                    "Certifications",
                    summary.certification_count,
                    "Certification records will be managed separately.",
                )

            with VerticalScroll(id="career-profile-actions"):
                yield Static("Profile Workflows", classes="section-title")
                with Horizontal(classes="profile-action-row"):
                    with Vertical(classes="profile-action-copy"):
                        yield Static("Experience", classes="card-title")
                        yield Static(
                            (
                                "Create, review, and accept role-specific experience entries. "
                                "This is where the current experience intake workflow lives."
                            ),
                            classes="status-detail",
                        )
                    yield Button(
                        "Manage Experience",
                        id="open-experience-intake",
                        variant="primary",
                    )

                with Horizontal(classes="profile-action-row"):
                    with Vertical(classes="profile-action-copy"):
                        yield Static("Education", classes="card-title")
                        yield Static(
                            "Education entry management is planned as a separate workflow.",
                            classes="status-detail",
                        )
                    yield Button("Coming Soon", disabled=True)

                with Horizontal(classes="profile-action-row"):
                    with Vertical(classes="profile-action-copy"):
                        yield Static("Certifications", classes="card-title")
                        yield Static(
                            "Certification entry management is planned as a separate workflow.",
                            classes="status-detail",
                        )
                    yield Button("Coming Soon", disabled=True)

                yield Static("Derived Profile Signals", classes="section-title")
                yield Static(
                    (
                        f"Skills: {summary.skills_count} | "
                        f"Tools and technologies: {summary.tools_count}"
                    ),
                    classes="read-only-panel",
                )
        yield Footer()

    def action_back(self) -> None:
        """Return to the dashboard."""

        self.app.pop_screen()
        self.app.refresh(recompose=True)

    def action_open_experience(self) -> None:
        """Open experience intake from the Career Profile overview."""

        self.app.push_screen(ExperienceIntakeScreen(self.experience_intake_service))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Career Profile workflow buttons."""

        if event.button.id == "open-experience-intake":
            self.action_open_experience()
