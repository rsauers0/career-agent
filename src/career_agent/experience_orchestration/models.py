from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class OrchestrationStepName(StrEnum):
    """Known Experience orchestration step names."""

    ROUTE_SOURCE = "route_source"
    SEGMENT_SOURCE = "segment_source"
    EXTRACT_EVIDENCE = "extract_evidence"
    COMPARE_FACTS = "compare_facts"
    PROPOSE_FINDINGS = "propose_findings"
    EVALUATE_GROUNDING = "evaluate_grounding"


class OrchestrationStepStatus(StrEnum):
    """Lifecycle status for one orchestrated LLM/eval step."""

    PENDING = "pending"
    GENERATED = "generated"
    EVAL_FAILED = "eval_failed"
    REGENERATED = "regenerated"
    ACCEPTED = "accepted"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class EvalSeverity(StrEnum):
    """Severity for one orchestration eval finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class StepInput(BaseModel):
    """Controlled input passed into one orchestration step."""

    step_name: OrchestrationStepName = Field(
        description="Name of the orchestration step receiving this input.",
    )
    context_id: str = Field(
        min_length=1,
        description="Identifier for the context object used by this step.",
    )
    attempt_number: int = Field(
        default=1,
        ge=1,
        description="One-based attempt number for this step input.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured step-specific input payload.",
    )

    @field_validator("context_id", mode="before")
    @classmethod
    def normalize_context_id(cls, value: Any) -> Any:
        """Trim context ids before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value


class StepOutput(BaseModel):
    """Structured output produced by one orchestration step."""

    step_name: OrchestrationStepName = Field(
        description="Name of the orchestration step that produced this output.",
    )
    status: OrchestrationStepStatus = Field(
        default=OrchestrationStepStatus.GENERATED,
        description="Lifecycle status for this output.",
    )
    attempt_number: int = Field(
        default=1,
        ge=1,
        description="One-based attempt number that produced this output.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured step-specific output payload.",
    )


class EvalFinding(BaseModel):
    """One validation, grounding, or quality finding for a step output."""

    code: str = Field(
        min_length=1,
        description="Stable machine-readable finding code.",
    )
    message: str = Field(
        min_length=1,
        description="Human-readable finding message.",
    )
    severity: EvalSeverity = Field(
        description="Severity for this eval finding.",
    )
    source_excerpt: str | None = Field(
        default=None,
        description="Optional source excerpt that supports this finding.",
    )

    @field_validator("code", "message", "source_excerpt", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        """Trim finding text fields before normal Pydantic validation."""

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class EvalResult(BaseModel):
    """Eval outcome for one orchestration step output."""

    step_name: OrchestrationStepName = Field(
        description="Name of the orchestration step evaluated.",
    )
    passed: bool = Field(
        description="Whether the evaluated output passed blocking checks.",
    )
    findings: list[EvalFinding] = Field(
        default_factory=list,
        description="Eval findings produced for the step output.",
    )

    @model_validator(mode="after")
    def validate_passed_state(self) -> EvalResult:
        """Require failed evals to include at least one error finding."""

        has_error = any(finding.severity == EvalSeverity.ERROR for finding in self.findings)
        if self.passed and has_error:
            msg = "passed eval results cannot include error findings."
            raise ValueError(msg)
        if not self.passed and not has_error:
            msg = "failed eval results require at least one error finding."
            raise ValueError(msg)
        return self


class RetryRequest(BaseModel):
    """Structured retry request sent back to a failed orchestration step."""

    step_name: OrchestrationStepName = Field(
        description="Name of the orchestration step that should be retried.",
    )
    attempt_number: int = Field(
        ge=1,
        description="Next one-based attempt number requested.",
    )
    max_attempts: int = Field(
        ge=1,
        description="Maximum allowed attempts for this step.",
    )
    failed_findings: list[EvalFinding] = Field(
        min_length=1,
        description="Blocking findings that caused the retry.",
    )
    revision_rules: list[str] = Field(
        default_factory=list,
        description="Concrete rules the next attempt must follow.",
    )

    @field_validator("revision_rules", mode="before")
    @classmethod
    def normalize_revision_rules(cls, values: list[str] | None) -> list[str]:
        """Trim revision rules and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]

    @model_validator(mode="after")
    def validate_retry_budget(self) -> RetryRequest:
        """Ensure retry attempt values describe a valid retry."""

        if self.attempt_number > self.max_attempts:
            msg = "attempt_number cannot exceed max_attempts."
            raise ValueError(msg)
        return self
