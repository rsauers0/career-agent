from career_agent.workflow_approval import (
    DummyWorkflowApprovalService,
    WorkflowApprovalRequest,
    WorkflowApprovalRequestType,
    WorkflowApprovalStatus,
)


def test_dummy_workflow_approval_service_approves_requests() -> None:
    service = DummyWorkflowApprovalService()

    result = service.request_approval(
        WorkflowApprovalRequest(
            request_type=WorkflowApprovalRequestType.FACT_ACTIVATION,
            subject_id="fact-1",
            role_id="role-1",
            rationale="User agreed with the fact.",
            source_message_ids=["review-message-1"],
        )
    )

    assert result.status == WorkflowApprovalStatus.APPROVED
    assert result.rationale == "Dummy approval granted for local workflow validation."
