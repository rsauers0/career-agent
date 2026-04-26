from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from career_agent.application.dashboard import (
    DashboardCard,
    DashboardSection,
    DashboardStatus,
    JobWorkflowState,
)
from career_agent.application.status import (
    ComponentStatus,
    ComponentStatusState,
    format_status_field_names,
)

STATUS_LABELS = {
    ComponentStatusState.NOT_STARTED: "Not Started",
    ComponentStatusState.INCOMPLETE: "Incomplete",
    ComponentStatusState.PARTIAL: "Partial",
    ComponentStatusState.COMPLETE: "Complete",
}

JOB_STATUS_LABELS = {
    JobWorkflowState.IDLE: "Idle",
    JobWorkflowState.QUEUED: "Queued",
    JobWorkflowState.PROCESSING: "Processing",
    JobWorkflowState.COMPLETED: "Completed",
    JobWorkflowState.FAILED: "Failed",
}


def format_component_name(component: str) -> str:
    """Convert an internal component key into a display label."""

    return component.replace("_", " ").title()


def get_status_label(status: DashboardStatus) -> str:
    """Return the user-facing label for a dashboard status state."""

    if isinstance(status, ComponentStatus):
        return STATUS_LABELS[status.state]
    return JOB_STATUS_LABELS[status.state]


def get_status_class(status: DashboardStatus) -> str:
    """Return the CSS class suffix for a dashboard status state."""

    return status.state.value


def get_status_detail(status: ComponentStatus) -> tuple[str, str]:
    """Return detail text and CSS class for a dashboard card."""

    if status.missing_required:
        return (
            f"Missing required: {', '.join(format_status_field_names(status.missing_required))}",
            "status-detail required-detail",
        )

    if status.missing_recommended:
        return (
            f"Recommended: {', '.join(format_status_field_names(status.missing_recommended))}",
            "status-detail recommended-detail",
        )

    return "Ready for the next workflow step.", "status-detail"


class StatusCard(Static):
    """Dashboard card for one workflow component."""

    def __init__(self, card: DashboardCard) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        detail_classes = get_dashboard_card_detail_class(self.card.status)

        yield Static(self.card.title, classes="card-title")
        yield Static(
            get_status_label(self.card.status),
            classes=f"status-pill status-{get_status_class(self.card.status)}",
        )
        yield Static(self.card.detail, classes=detail_classes)

        if self.card.shortcut:
            yield Static(f"Shortcut: {self.card.shortcut}", classes="shortcut-hint")


def get_dashboard_card_detail_class(status: DashboardStatus) -> str:
    """Return the CSS class for dashboard card detail text."""

    if isinstance(status, ComponentStatus) and status.missing_required:
        return "status-detail required-detail"

    if isinstance(status, ComponentStatus) and status.missing_recommended:
        return "status-detail recommended-detail"

    return "status-detail"


class DashboardSectionView(Static):
    """TUI section containing related dashboard status cards."""

    def __init__(self, section: DashboardSection) -> None:
        super().__init__()
        self.section = section

    def compose(self) -> ComposeResult:
        yield Static(self.section.title, classes="section-title")
        for card in self.section.cards:
            yield StatusCard(card)
