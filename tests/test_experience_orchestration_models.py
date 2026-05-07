import pytest
from pydantic import ValidationError

from career_agent.experience_orchestration.models import (
    EvalFinding,
    EvalResult,
    EvalSeverity,
    OrchestrationStepName,
    OrchestrationStepStatus,
    RetryRequest,
    StepInput,
    StepOutput,
)


def test_step_input_and_output_store_structured_payloads() -> None:
    step_input = StepInput(
        step_name=OrchestrationStepName.SEGMENT_SOURCE,
        context_id=" context-1 ",
        payload={"source_id": "source-1"},
    )
    step_output = StepOutput(
        step_name=OrchestrationStepName.SEGMENT_SOURCE,
        status=OrchestrationStepStatus.GENERATED,
        payload={"segment_ids": ["segment-1"]},
    )

    assert step_input.context_id == "context-1"
    assert step_input.attempt_number == 1
    assert step_input.payload == {"source_id": "source-1"}
    assert step_output.status == OrchestrationStepStatus.GENERATED
    assert step_output.payload == {"segment_ids": ["segment-1"]}


def test_eval_result_accepts_warning_findings_when_passed() -> None:
    result = EvalResult(
        step_name=OrchestrationStepName.EVALUATE_GROUNDING,
        passed=True,
        findings=[
            EvalFinding(
                code="minor_style_note",
                message="Consider preserving the source term.",
                severity=EvalSeverity.WARNING,
            )
        ],
    )

    assert result.passed is True
    assert result.findings[0].severity == EvalSeverity.WARNING


def test_eval_result_rejects_passed_state_with_error_findings() -> None:
    with pytest.raises(ValidationError, match="passed eval results"):
        EvalResult(
            step_name=OrchestrationStepName.EVALUATE_GROUNDING,
            passed=True,
            findings=[
                EvalFinding(
                    code="missing_metric",
                    message="The generated text dropped a supported metric.",
                    severity=EvalSeverity.ERROR,
                )
            ],
        )


def test_eval_result_rejects_failed_state_without_error_findings() -> None:
    with pytest.raises(ValidationError, match="failed eval results"):
        EvalResult(
            step_name=OrchestrationStepName.EVALUATE_GROUNDING,
            passed=False,
            findings=[
                EvalFinding(
                    code="style_warning",
                    message="This wording may be too polished.",
                    severity=EvalSeverity.WARNING,
                )
            ],
        )


def test_retry_request_requires_failed_findings_and_valid_attempt_budget() -> None:
    finding = EvalFinding(
        code="unsupported_scope",
        message="The output used broader scope than the source supports.",
        severity=EvalSeverity.ERROR,
        source_excerpt="managed delivery in a highly regulated environment",
    )

    request = RetryRequest(
        step_name=OrchestrationStepName.PROPOSE_FINDINGS,
        attempt_number=2,
        max_attempts=3,
        failed_findings=[finding],
        revision_rules=[" Do not expand scope beyond source evidence. ", ""],
    )

    assert request.failed_findings == [finding]
    assert request.revision_rules == ["Do not expand scope beyond source evidence."]

    with pytest.raises(ValidationError, match="attempt_number cannot exceed"):
        RetryRequest(
            step_name=OrchestrationStepName.PROPOSE_FINDINGS,
            attempt_number=4,
            max_attempts=3,
            failed_findings=[finding],
        )
