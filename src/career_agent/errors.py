"""Shared application-level exceptions."""


class CareerAgentError(Exception):
    """Base exception for Career Agent application errors."""


class RoleNotFoundError(CareerAgentError):
    """Raised when a referenced experience role does not exist."""


class SourceNotFoundError(CareerAgentError):
    """Raised when a referenced role source does not exist."""


class SourceRoleMismatchError(CareerAgentError):
    """Raised when a source does not belong to the expected role."""
