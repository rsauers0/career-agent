from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class WorkflowApprovalRequestType(StrEnum):
    """Workflow approval request categories."""

    FACT_ACTIVATION = "fact_activation"


class WorkflowApprovalStatus(StrEnum):
    """Outcome of a workflow approval request."""

    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class WorkflowApprovalRequest:
    """Generic workflow approval request."""

    request_type: WorkflowApprovalRequestType
    subject_id: str
    role_id: str | None = None
    rationale: str | None = None
    source_message_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowApprovalResult:
    """Result returned by an approval workflow."""

    status: WorkflowApprovalStatus
    rationale: str | None = None


class WorkflowApprovalService(Protocol):
    """Approval boundary for replaceable workflow approval/eval routing."""

    def request_approval(self, request: WorkflowApprovalRequest) -> WorkflowApprovalResult:
        """Return an approval decision for a workflow request."""


class DummyWorkflowApprovalService:
    """Dummy approval service for local workflow validation."""

    def request_approval(self, request: WorkflowApprovalRequest) -> WorkflowApprovalResult:
        """Approve every request without external evals."""

        del request
        return WorkflowApprovalResult(
            status=WorkflowApprovalStatus.APPROVED,
            rationale="Dummy approval granted for local workflow validation.",
        )
