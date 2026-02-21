"""
TruthChain Python SDK – Main Client

Usage (sync):
    from truthchain import TruthChain
    client = TruthChain(api_key="tc_...")
    result = client.validate(output={...}, rules=[...])

Usage (async):
    from truthchain import AsyncTruthChain
    client = AsyncTruthChain(api_key="tc_...")
    result = await client.validate(output={...}, rules=[...])
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    ValidationError,
    TruthChainError,
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
)

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0


def _raise_for_status(response: httpx.Response) -> None:
    """Convert HTTP error responses to typed SDK exceptions."""
    if response.is_success:
        return

    try:
        body = response.json()
        detail = body.get("detail", response.text)
    except Exception:
        detail = response.text

    status = response.status_code

    if status == 401:
        raise AuthenticationError(detail, status_code=status, response=body if isinstance(body, dict) else {})
    if status == 403:
        raise PermissionError(detail, status_code=status)
    if status == 404:
        raise NotFoundError(detail, status_code=status)
    if status == 422:
        raise ValidationError(str(detail), status_code=status)
    if status == 429:
        retry_after = None
        try:
            retry_after = float(response.headers.get("Retry-After", 0))
        except (TypeError, ValueError):
            pass
        if "quota" in str(detail).lower():
            raise QuotaExceededError(detail, status_code=status)
        raise RateLimitError(detail, retry_after=retry_after, status_code=status)
    if status in (400, 409):
        raise ConflictError(detail, status_code=status)
    if status >= 500:
        raise ServerError(detail, status_code=status)

    raise TruthChainError(detail, status_code=status)


# ── Synchronous Client ────────────────────────────────────────────────────────

class TruthChain:
    """
    Synchronous TruthChain client.

    Args:
        api_key:  Your TruthChain API key (``tc_live_...``).
        base_url: Base URL of the TruthChain API server.
                  Defaults to ``http://localhost:8000`` for local development.
        timeout:  Request timeout in seconds. Default: 30.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    def close(self):
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Internal helper ───────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        response = self._client.request(method, path, **kwargs)
        _raise_for_status(response)
        if response.status_code == 204:
            return None
        return response.json()

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate AI output against a set of rules.

        Args:
            output:  The JSON object produced by your AI / LLM.
            rules:   List of validation rule dicts (schema, range, pattern, etc.).
            context: Optional extra context, e.g. ``{"auto_correct": True}``.

        Returns:
            :class:`~truthchain.models.ValidationResult`

        Example::

            result = client.validate(
                output={"user_id": 42, "hours": 8, "project": "Acme"},
                rules=[
                    {
                        "type": "range",
                        "name": "hours_check",
                        "field": "hours",
                        "min": 0,
                        "max": 24,
                    }
                ],
            )
            print(result.status)        # "passed"
            print(result.is_valid)      # True
        """
        payload: Dict[str, Any] = {"output": output, "rules": rules}
        if context:
            payload["context"] = context
        data = self._request("POST", "/v1/validate", json=payload)
        return ValidationResult.from_dict(data)

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_analytics(self) -> AnalyticsOverview:
        """Fetch a full analytics overview (stats, daily breakdown, top violations)."""
        data = self._request("GET", "/v1/analytics/overview")
        return AnalyticsOverview.from_dict(data)

    def get_validation_stats(self) -> ValidationStats:
        """Fetch aggregated validation statistics."""
        data = self._request("GET", "/v1/analytics/validation-stats")
        return ValidationStats.from_dict(data)

    # ── Billing ───────────────────────────────────────────────────────────────

    def get_subscription(self) -> Subscription:
        """Fetch the current subscription details for your organization."""
        data = self._request("GET", "/v1/billing/subscription")
        return Subscription.from_dict(data)

    def get_plans(self) -> List[BillingPlan]:
        """List all available billing plans."""
        data = self._request("GET", "/v1/billing/plans")
        return [BillingPlan.from_dict(p) for p in data]

    def upgrade(self, tier: str) -> Subscription:
        """
        Upgrade or downgrade the subscription tier.

        Args:
            tier: One of ``"free"``, ``"startup"``, ``"business"``, ``"enterprise"``.

        Returns:
            Updated :class:`~truthchain.models.Subscription`.
        """
        data = self._request("POST", "/v1/billing/upgrade", json={"tier": tier})
        return Subscription.from_dict(data)

    # ── API Key Management ────────────────────────────────────────────────────

    def list_api_keys(self) -> List[APIKey]:
        """List all API keys for your organization."""
        data = self._request("GET", "/v1/auth/api-keys")
        return [APIKey.from_dict(k) for k in data]

    def create_api_key(self, name: str = "API Key") -> APIKey:
        """
        Create a new API key.

        .. warning::
            Save the returned ``key`` immediately — it is shown **only once**.

        Args:
            name: Human-readable label for the key.

        Returns:
            :class:`~truthchain.models.APIKey`  (with ``key`` set)
        """
        data = self._request("POST", f"/v1/auth/api-keys?name={name}")
        return APIKey.from_dict(data)

    def rotate_api_key(self, key_id: str) -> APIKey:
        """
        Rotate an existing API key (old key is revoked, new one is issued).

        Args:
            key_id: The ``id`` of the key to rotate.

        Returns:
            New :class:`~truthchain.models.APIKey`  (with ``key`` set)
        """
        data = self._request("POST", f"/v1/auth/api-keys/{key_id}/rotate")
        return APIKey.from_dict(data)

    def revoke_api_key(self, key_id: str) -> None:
        """
        Revoke (deactivate) an API key.

        Args:
            key_id: The ``id`` of the key to revoke.
        """
        self._request("DELETE", f"/v1/auth/api-keys/{key_id}")


# ── Async Client ──────────────────────────────────────────────────────────────

class AsyncTruthChain:
    """
    Asynchronous TruthChain client (same interface as :class:`TruthChain`).

    Args:
        api_key:  Your TruthChain API key.
        base_url: Base URL of the TruthChain API server.
        timeout:  Request timeout in seconds. Default: 30.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    async def close(self):
        """Close the underlying async HTTP connection pool."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        response = await self._client.request(method, path, **kwargs)
        _raise_for_status(response)
        if response.status_code == 204:
            return None
        return response.json()

    # ── Validation ────────────────────────────────────────────────────────────

    async def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Async version of :meth:`TruthChain.validate`."""
        payload: Dict[str, Any] = {"output": output, "rules": rules}
        if context:
            payload["context"] = context
        data = await self._request("POST", "/v1/validate", json=payload)
        return ValidationResult.from_dict(data)

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def get_analytics(self) -> AnalyticsOverview:
        """Async version of :meth:`TruthChain.get_analytics`."""
        data = await self._request("GET", "/v1/analytics/overview")
        return AnalyticsOverview.from_dict(data)

    async def get_validation_stats(self) -> ValidationStats:
        """Async version of :meth:`TruthChain.get_validation_stats`."""
        data = await self._request("GET", "/v1/analytics/validation-stats")
        return ValidationStats.from_dict(data)

    # ── Billing ───────────────────────────────────────────────────────────────

    async def get_subscription(self) -> Subscription:
        """Async version of :meth:`TruthChain.get_subscription`."""
        data = await self._request("GET", "/v1/billing/subscription")
        return Subscription.from_dict(data)

    async def get_plans(self) -> List[BillingPlan]:
        """Async version of :meth:`TruthChain.get_plans`."""
        data = await self._request("GET", "/v1/billing/plans")
        return [BillingPlan.from_dict(p) for p in data]

    async def upgrade(self, tier: str) -> Subscription:
        """Async version of :meth:`TruthChain.upgrade`."""
        data = await self._request("POST", "/v1/billing/upgrade", json={"tier": tier})
        return Subscription.from_dict(data)

    # ── API Key Management ────────────────────────────────────────────────────

    async def list_api_keys(self) -> List[APIKey]:
        """Async version of :meth:`TruthChain.list_api_keys`."""
        data = await self._request("GET", "/v1/auth/api-keys")
        return [APIKey.from_dict(k) for k in data]

    async def create_api_key(self, name: str = "API Key") -> APIKey:
        """Async version of :meth:`TruthChain.create_api_key`."""
        data = await self._request("POST", f"/v1/auth/api-keys?name={name}")
        return APIKey.from_dict(data)

    async def rotate_api_key(self, key_id: str) -> APIKey:
        """Async version of :meth:`TruthChain.rotate_api_key`."""
        data = await self._request("POST", f"/v1/auth/api-keys/{key_id}/rotate")
        return APIKey.from_dict(data)

    async def revoke_api_key(self, key_id: str) -> None:
        """Async version of :meth:`TruthChain.revoke_api_key`."""
        await self._request("DELETE", f"/v1/auth/api-keys/{key_id}")


# ── Top-level auth helpers (no API key required) ──────────────────────────────

def signup(
    name: str,
    email: str,
    password: str,
    tier: str = "free",
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> SignupResult:
    """
    Register a new organization and receive an API key.

    .. warning::
        Save the returned ``api_key`` immediately — it is shown **only once**.

    Args:
        name:     Organization name.
        email:    Email address.
        password: Password (min 8 characters).
        tier:     Subscription tier — ``"free"`` | ``"startup"`` | ``"business"`` | ``"enterprise"``.
        base_url: API server URL.

    Returns:
        :class:`~truthchain.models.SignupResult`

    Example::

        from truthchain import signup
        result = signup("Acme Corp", "dev@acme.com", "s3cretPW!")
        print(result.api_key)   # tc_live_...  ← save this!
    """
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        response = client.post(
            "/v1/auth/signup",
            json={"name": name, "email": email, "password": password, "tier": tier},
        )
        _raise_for_status(response)
        return SignupResult.from_dict(response.json())


def login(
    email: str,
    password: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> LoginResult:
    """
    Login with email and password to receive a fresh API key.

    Args:
        email:    Organization email.
        password: Account password.
        base_url: API server URL.

    Returns:
        :class:`~truthchain.models.LoginResult`

    Example::

        from truthchain import login
        result = login("dev@acme.com", "s3cretPW!")
        client = TruthChain(api_key=result.api_key)
    """
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        response = client.post(
            "/v1/auth/login",
            json={"email": email, "password": password},
        )
        _raise_for_status(response)
        return LoginResult.from_dict(response.json())
