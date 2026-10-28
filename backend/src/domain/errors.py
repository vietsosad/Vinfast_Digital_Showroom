"""Business errors raised by the domain and application layers.

The API layer maps each subclass to one HTTP status code, so use cases never
need to know about HTTP.
"""


class DomainError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """The requested resource does not exist (404)."""


class AuthenticationError(DomainError):
    """Credentials or token are missing, invalid or expired (401)."""


class PermissionDeniedError(DomainError):
    """The actor is authenticated but not allowed to perform the action (403)."""


class ConflictError(DomainError):
    """The request conflicts with the current state, e.g. a duplicate email (409)."""


class InvalidStateTransitionError(ConflictError):
    """A status change is not allowed by the workflow (409)."""


class ValidationError(DomainError):
    """Input violates a business rule (422)."""


class FileTooLargeError(DomainError):
    """An uploaded file exceeds the configured size limit (413)."""
