"""
TruthChain SDK Data Models
Dataclasses that mirror the API response shapes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Auth ──────────────────────────────────────────────────────────────────────

@dataclass
class SignupResult:
    """Returned after a successful organization signup."""
    organization_id: str
    name: str
    email: str
    tier: str
    api_key: str          # Save this — shown only once!
    monthly_quota: int

    @classmethod
    def from_dict(cls, data: dict) -> "SignupResult":
        return cls(
            organization_id=data["organization_id"],
            name=data["name"],
            email=data["email"],
            tier=data["tier"],
            api_key=data["api_key"],
            monthly_quota=data["monthly_quota"],
        )


@dataclass
class LoginResult:
    """Returned after a successful login."""
    organization_id: str
    name: str
    email: str
    tier: str
    api_key: str          # Fresh key issued on login
    monthly_quota: int

    @classmethod
    def from_dict(cls, data: dict) -> "LoginResult":
        return cls(
            organization_id=data["organization_id"],
            name=data["name"],
            email=data["email"],
            tier=data["tier"],
            api_key=data["api_key"],
            monthly_quota=data["monthly_quota"],
        )


@dataclass
class APIKey:
    """Represents an API key (the secret value is only present on creation)."""
    id: str
    name: str
    is_active: bool
    created_at: str
    key: Optional[str] = None          # Only set at creation time
    key_prefix: Optional[str] = None   # First 20 chars, safe to display
    last_used_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "APIKey":
        return cls(
            id=data["id"],
            name=data["name"],
            is_active=data["is_active"],
            created_at=data["created_at"],
            key=data.get("key"),
            key_prefix=data.get("key_prefix"),
            last_used_at=data.get("last_used_at"),
        )


# ── Validation ────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    """A single rule violation found during validation."""
    rule_name: str
    violation_type: str
    message: str
    severity: str
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Violation":
        return cls(
            rule_name=data.get("rule_name", ""),
            violation_type=data.get("violation_type", ""),
            message=data.get("message", ""),
            severity=data.get("severity", "error"),
            field=data.get("field"),
            expected=data.get("expected"),
            actual=data.get("actual"),
        )


@dataclass
class ValidationResult:
    """Full result returned by POST /v1/validate."""
    validation_id: str
    status: str                             # "passed" | "failed" | "warning"
    is_valid: bool
    violations: List[Violation] = field(default_factory=list)
    corrected_output: Optional[Dict[str, Any]] = None
    auto_corrected: bool = False
    corrections_applied: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    latency_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        return cls(
            validation_id=data.get("validation_id", ""),
            status=data.get("status", ""),
            is_valid=data.get("is_valid", False),
            violations=[Violation.from_dict(v) for v in data.get("violations", [])],
            corrected_output=data.get("corrected_output"),
            auto_corrected=data.get("auto_corrected", False),
            corrections_applied=data.get("corrections_applied", []),
            confidence_score=data.get("confidence_score"),
            latency_ms=data.get("latency_ms"),
            metadata=data.get("metadata", {}),
        )


# ── Analytics ─────────────────────────────────────────────────────────────────

@dataclass
class ValidationStats:
    """Aggregated validation statistics for your organization."""
    total_validations: int
    passed: int
    failed: int
    warnings: int
    success_rate: float
    avg_latency_ms: float
    auto_corrections: int
    auto_correction_rate: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationStats":
        return cls(
            total_validations=data.get("total_validations", 0),
            passed=data.get("passed", 0),
            failed=data.get("failed", 0),
            warnings=data.get("warnings", 0),
            success_rate=data.get("success_rate", 0.0),
            # backend returns average_latency_ms; accept both spellings
            avg_latency_ms=data.get("average_latency_ms", data.get("avg_latency_ms", 0.0)),
            auto_corrections=data.get("auto_corrected_count", data.get("auto_corrections", 0)),
            auto_correction_rate=data.get("auto_correction_rate", 0.0),
        )


@dataclass
class AnalyticsOverview:
    """Full analytics overview — raw dict kept for flexibility."""
    raw: Dict[str, Any]

    # Convenience accessors
    @property
    def validation_stats(self) -> Dict[str, Any]:
        return self.raw.get("validation_stats", {})

    @property
    def usage_stats(self) -> Dict[str, Any]:
        return self.raw.get("usage_stats", {})

    @property
    def daily_stats(self) -> List[Dict[str, Any]]:
        return self.raw.get("daily_stats", [])

    @property
    def recent_validations(self) -> List[Dict[str, Any]]:
        return self.raw.get("recent_validations", [])

    @property
    def top_violations(self) -> List[Dict[str, Any]]:
        return self.raw.get("top_violations", [])

    @classmethod
    def from_dict(cls, data: dict) -> "AnalyticsOverview":
        return cls(raw=data)


# ── Billing ───────────────────────────────────────────────────────────────────

@dataclass
class Subscription:
    """Current subscription status."""
    tier: str
    subscription_status: str
    price_cents: int
    price_display: str
    monthly_quota: int
    rpm_limit: int
    quota_used: int
    quota_percentage: float
    current_period_end: Optional[str] = None
    canceled_at: Optional[str] = None
    trial_ends_at: Optional[str] = None
    billing_email: Optional[str] = None
    stripe_customer_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        return cls(
            tier=data["tier"],
            subscription_status=data["subscription_status"],
            price_cents=data["price_cents"],
            price_display=data["price_display"],
            monthly_quota=data["monthly_quota"],
            rpm_limit=data["rpm_limit"],
            quota_used=data["quota_used"],
            quota_percentage=data["quota_percentage"],
            current_period_end=data.get("current_period_end"),
            canceled_at=data.get("canceled_at"),
            trial_ends_at=data.get("trial_ends_at"),
            billing_email=data.get("billing_email"),
            stripe_customer_id=data.get("stripe_customer_id"),
        )


@dataclass
class BillingPlan:
    """A single available billing plan."""
    tier: str
    label: str
    price_cents: int
    price_display: str
    monthly_quota: int
    rpm_limit: int
    features: List[str]
    is_current: bool

    @classmethod
    def from_dict(cls, data: dict) -> "BillingPlan":
        return cls(
            tier=data["tier"],
            label=data["label"],
            price_cents=data["price_cents"],
            price_display=data["price_display"],
            monthly_quota=data["monthly_quota"],
            rpm_limit=data["rpm_limit"],
            features=data.get("features", []),
            is_current=data.get("is_current", False),
        )
