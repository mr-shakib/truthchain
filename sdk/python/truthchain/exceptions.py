"""
TruthChain SDK Exceptions
"""


class TruthChainError(Exception):
    """Base exception for all TruthChain SDK errors."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}

    def __repr__(self):
        return f"{self.__class__.__name__}(message={self.message!r}, status_code={self.status_code})"


class AuthenticationError(TruthChainError):
    """Raised when the API key is missing, invalid, or revoked (HTTP 401)."""


class PermissionError(TruthChainError):
    """Raised when the API key lacks permission for the requested action (HTTP 403)."""


class QuotaExceededError(TruthChainError):
    """Raised when the monthly validation quota has been exhausted (HTTP 429 quota)."""


class RateLimitError(TruthChainError):
    """Raised when requests-per-minute limit is hit (HTTP 429 rate-limit)."""

    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after  # seconds to wait before retrying


class NotFoundError(TruthChainError):
    """Raised when a requested resource does not exist (HTTP 404)."""


class ValidationError(TruthChainError):
    """Raised when the request payload is invalid (HTTP 422)."""


class ServerError(TruthChainError):
    """Raised on unexpected server-side errors (HTTP 5xx)."""


class ConflictError(TruthChainError):
    """Raised when there is a conflict, e.g. duplicate email (HTTP 400 / 409)."""
