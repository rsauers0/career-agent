"""Shared application-level exceptions."""


class CareerAgentError(Exception):
    """Base exception for Career Agent application errors."""


class RoleNotFoundError(CareerAgentError):
    """Raised when a referenced experience role does not exist."""


class SourceNotFoundError(CareerAgentError):
    """Raised when a referenced role source does not exist."""


class SourceRoleMismatchError(CareerAgentError):
    """Raised when a source does not belong to the expected role."""


class NoUnanalyzedSourcesError(CareerAgentError):
    """Raised when a workflow requires unanalyzed sources but none exist."""


class InvalidLLMOutputError(CareerAgentError):
    """Raised when LLM output fails required contract validation."""


class LLMClientError(CareerAgentError):
    """Raised when an LLM client cannot complete a request."""


class AnalysisRunNotFoundError(CareerAgentError):
    """Raised when a referenced source analysis run does not exist."""


class ActiveAnalysisRunExistsError(CareerAgentError):
    """Raised when an active source analysis run already exists for a role."""


class ClarificationQuestionNotFoundError(CareerAgentError):
    """Raised when a referenced clarification question does not exist."""


class SourceNotInAnalysisRunError(CareerAgentError):
    """Raised when a source is not part of the expected analysis run."""
