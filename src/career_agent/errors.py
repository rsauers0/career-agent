"""Shared application-level exceptions."""


class CareerAgentError(Exception):
    """Base exception for Career Agent application errors."""


class RoleNotFoundError(CareerAgentError):
    """Raised when a referenced experience role does not exist."""


class SourceNotFoundError(CareerAgentError):
    """Raised when a referenced role source does not exist."""


class SourceRoleMismatchError(CareerAgentError):
    """Raised when a source does not belong to the expected role."""


class FactNotFoundError(CareerAgentError):
    """Raised when a referenced experience fact does not exist."""


class FactRoleMismatchError(CareerAgentError):
    """Raised when a fact does not belong to the expected role."""


class EvidenceReferenceRemovalError(CareerAgentError):
    """Raised when immutable evidence references would be removed."""


class InvalidFactStatusTransitionError(CareerAgentError):
    """Raised when an experience fact status transition is not allowed."""


class FactRevisionNotAllowedError(CareerAgentError):
    """Raised when an experience fact cannot be revised in its current state."""


class NoUnanalyzedSourcesError(CareerAgentError):
    """Raised when a workflow requires unanalyzed sources but none exist."""


class InvalidLLMOutputError(CareerAgentError):
    """Raised when LLM output fails required contract validation."""


class LLMClientError(CareerAgentError):
    """Raised when an LLM client cannot complete a request."""


class LLMConfigurationError(CareerAgentError):
    """Raised when LLM configuration is incomplete or invalid."""


class AnalysisRunNotFoundError(CareerAgentError):
    """Raised when a referenced source analysis run does not exist."""


class ActiveAnalysisRunExistsError(CareerAgentError):
    """Raised when an active source analysis run already exists for a role."""


class ClarificationQuestionNotFoundError(CareerAgentError):
    """Raised when a referenced clarification question does not exist."""


class SourceNotInAnalysisRunError(CareerAgentError):
    """Raised when a source is not part of the expected analysis run."""


class SourceFindingNotFoundError(CareerAgentError):
    """Raised when a referenced source finding does not exist."""


class InvalidSourceFindingStatusTransitionError(CareerAgentError):
    """Raised when a source finding status transition is not allowed."""


class OpenClarificationQuestionsError(CareerAgentError):
    """Raised when a workflow requires closed clarification questions."""


class SourceFindingsAlreadyExistError(CareerAgentError):
    """Raised when findings already exist for a source analysis run."""


class FactReviewThreadNotFoundError(CareerAgentError):
    """Raised when a referenced fact review thread does not exist."""


class FactReviewActionNotFoundError(CareerAgentError):
    """Raised when a referenced fact review action does not exist."""


class FactReviewActionsAlreadyExistError(CareerAgentError):
    """Raised when proposed fact review actions already exist for a thread."""


class ActiveFactReviewThreadExistsError(CareerAgentError):
    """Raised when an open fact review thread already exists for a fact."""


class InvalidFactReviewThreadStatusTransitionError(CareerAgentError):
    """Raised when a fact review thread status transition is not allowed."""


class InvalidFactReviewActionStatusTransitionError(CareerAgentError):
    """Raised when a fact review action status transition is not allowed."""


class ScopedConstraintNotFoundError(CareerAgentError):
    """Raised when a referenced scoped constraint does not exist."""


class InvalidScopedConstraintStatusTransitionError(CareerAgentError):
    """Raised when a scoped constraint status transition is not allowed."""
