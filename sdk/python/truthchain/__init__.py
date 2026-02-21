"""
TruthChain Python SDK
~~~~~~~~~~~~~~~~~~~~~

Validate AI outputs against any business rules in <100ms.

Basic usage::

    from truthchain import TruthChain, signup

    # One-time: create an account
    result = signup("Acme Corp", "dev@acme.com", "s3cretPW!")
    API_KEY = result.api_key   # save this!

    # Every request
    client = TruthChain(api_key=API_KEY)
    result = client.validate(
        output={"user_id": 42, "hours": 8},
        rules=[{"type": "range", "name": "hours", "field": "hours", "min": 0, "max": 24}],
    )
    print(result.status)    # "passed"

"""

from .client import AsyncTruthChain, TruthChain, login, signup
from .exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    TruthChainError,
    ValidationError,
)
from .models import (
    APIKey,
    AnalyticsOverview,
    BillingPlan,
    LoginResult,
    SignupResult,
    Subscription,
    ValidationResult,
    ValidationStats,
    Violation,
)

__all__ = [
    # Clients
    "TruthChain",
    "AsyncTruthChain",
    # Auth helpers
    "signup",
    "login",
    # Models
    "SignupResult",
    "LoginResult",
    "APIKey",
    "ValidationResult",
    "Violation",
    "ValidationStats",
    "AnalyticsOverview",
    "Subscription",
    "BillingPlan",
    # Exceptions
    "TruthChainError",
    "AuthenticationError",
    "QuotaExceededError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
    "ConflictError",
]

__version__ = "1.0.0"
