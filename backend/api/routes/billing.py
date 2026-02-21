"""
Billing & Subscription routes for TruthChain
Implements simulated billing with Stripe-ready structure.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import uuid
import json

from ...db.connection import get_db
from ...models.organization import Organization, OrganizationTier
from ..dependencies import get_current_organization
from ...models.api_key import APIKey

router = APIRouter(prefix="/v1/billing", tags=["Billing"])

# ── Tier pricing catalogue ──────────────────────────────────────────────────

TIER_CATALOGUE = {
    "free":       {"price_cents": 0,     "monthly_quota": 1_000,     "rpm": 10,  "label": "Free"},
    "startup":    {"price_cents": 2900,  "monthly_quota": 10_000,    "rpm": 30,  "label": "Startup"},
    "business":   {"price_cents": 9900,  "monthly_quota": 100_000,   "rpm": 100, "label": "Business"},
    "enterprise": {"price_cents": 49900, "monthly_quota": 1_000_000, "rpm": 500, "label": "Enterprise"},
}

# ── Response / Request models ───────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    tier: str
    subscription_status: str
    price_cents: int
    price_display: str
    monthly_quota: int
    rpm_limit: int
    quota_used: int
    quota_percentage: float
    current_period_end: Optional[str]
    canceled_at: Optional[str]
    trial_ends_at: Optional[str]
    billing_email: Optional[str]
    stripe_customer_id: Optional[str]


class BillingPlan(BaseModel):
    tier: str
    label: str
    price_cents: int
    price_display: str
    monthly_quota: int
    rpm_limit: int
    features: List[str]
    is_current: bool


class UpgradeRequest(BaseModel):
    tier: str
    billing_email: Optional[EmailStr] = None


class UpgradeResponse(BaseModel):
    success: bool
    message: str
    new_tier: str
    new_monthly_quota: int
    effective_from: str


class CancelResponse(BaseModel):
    success: bool
    message: str
    canceled_at: str
    downgrade_at: str  # end of current period / immediate for simulated


class InvoiceItem(BaseModel):
    id: str
    tier: str
    amount_cents: int
    amount_display: str
    status: str   # 'paid' | 'pending' | 'failed'
    period_start: str
    period_end: str
    created_at: str
    pdf_url: Optional[str]


# ── Feature descriptions ────────────────────────────────────────────────────

TIER_FEATURES = {
    "free":       ["10 req/min", "1,000 validations/month", "Schema validation", "Basic rules"],
    "startup":    ["30 req/min", "10,000 validations/month", "Auto-correction", "Anomaly detection", "Confidence scoring"],
    "business":   ["100 req/min", "100,000 validations/month", "All Startup features", "Priority support", "Analytics API"],
    "enterprise": ["500 req/min", "1M+ validations/month", "All Business features", "Dedicated support", "SLA guarantee", "Custom integrations"],
}


def _price_display(cents: int) -> str:
    if cents == 0:
        return "$0 / month"
    return f"${cents // 100} / month"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _period_end() -> datetime:
    """Simulated: billing period ends in ~30 days."""
    return datetime.now(timezone.utc) + timedelta(days=30)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[BillingPlan], summary="List all available plans")
async def list_plans(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
):
    """Return all tiers with pricing, features, and whether it's the current plan."""
    organization, _ = org_data
    current = organization.tier if isinstance(organization.tier, str) else organization.tier.value

    plans = []
    for tier, info in TIER_CATALOGUE.items():
        plans.append(BillingPlan(
            tier=tier,
            label=info["label"],
            price_cents=info["price_cents"],
            price_display=_price_display(info["price_cents"]),
            monthly_quota=info["monthly_quota"],
            rpm_limit=info["rpm"],
            features=TIER_FEATURES[tier],
            is_current=(tier == current),
        ))
    return plans


@router.get("/subscription", response_model=SubscriptionResponse, summary="Current subscription details")
async def get_subscription(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
):
    """Return full subscription state for the authenticated org."""
    organization, _ = org_data
    tier = organization.tier if isinstance(organization.tier, str) else organization.tier.value
    info = TIER_CATALOGUE.get(tier, TIER_CATALOGUE["free"])

    used = organization.usage_current_month
    quota = organization.monthly_quota
    pct = round((used / quota) * 100, 1) if quota > 0 else 0.0

    return SubscriptionResponse(
        tier=tier,
        subscription_status=organization.subscription_status or "active",
        price_cents=info["price_cents"],
        price_display=_price_display(info["price_cents"]),
        monthly_quota=quota,
        rpm_limit=info["rpm"],
        quota_used=used,
        quota_percentage=pct,
        current_period_end=organization.current_period_end.isoformat() if organization.current_period_end else None,
        canceled_at=organization.canceled_at.isoformat() if organization.canceled_at else None,
        trial_ends_at=organization.trial_ends_at.isoformat() if organization.trial_ends_at else None,
        billing_email=organization.billing_email,
        stripe_customer_id=organization.stripe_customer_id,
    )


@router.post("/upgrade", response_model=UpgradeResponse, summary="Upgrade or change subscription tier")
async def upgrade_subscription(
    body: UpgradeRequest,
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the organization's subscription tier (simulated — no real payment).
    Immediately applies new quota and rate limits.
    """
    organization, _ = org_data

    if body.tier not in TIER_CATALOGUE:
        raise HTTPException(status_code=400, detail=f"Unknown tier '{body.tier}'. Valid: {list(TIER_CATALOGUE.keys())}")

    current = organization.tier if isinstance(organization.tier, str) else organization.tier.value
    if body.tier == current:
        raise HTTPException(status_code=400, detail=f"Already on the '{body.tier}' plan.")

    info = TIER_CATALOGUE[body.tier]
    now = datetime.now(timezone.utc)
    period_end = _period_end()

    # Apply changes
    organization.tier = body.tier
    organization.monthly_quota = info["monthly_quota"]
    organization.subscription_status = "active"
    organization.current_period_end = period_end
    organization.canceled_at = None  # re-activate if was canceled

    if body.billing_email:
        organization.billing_email = str(body.billing_email)

    # Append a simulated paid invoice
    _append_invoice(organization, tier=body.tier, cents=info["price_cents"], now=now, period_end=period_end)

    await db.commit()
    await db.refresh(organization)

    return UpgradeResponse(
        success=True,
        message=f"Successfully switched to {info['label']} plan.",
        new_tier=body.tier,
        new_monthly_quota=info["monthly_quota"],
        effective_from=now.isoformat(),
    )


@router.post("/cancel", response_model=CancelResponse, summary="Cancel subscription (downgrades to Free)")
async def cancel_subscription(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the active subscription and downgrade to Free immediately (simulated)."""
    organization, _ = org_data
    current = organization.tier if isinstance(organization.tier, str) else organization.tier.value

    if current == "free":
        raise HTTPException(status_code=400, detail="Already on the Free plan — nothing to cancel.")

    now = datetime.now(timezone.utc)
    organization.subscription_status = "canceled"
    organization.canceled_at = now
    organization.tier = "free"
    organization.monthly_quota = TIER_CATALOGUE["free"]["monthly_quota"]
    organization.current_period_end = None

    await db.commit()

    return CancelResponse(
        success=True,
        message="Subscription canceled. You have been downgraded to the Free plan.",
        canceled_at=now.isoformat(),
        downgrade_at=now.isoformat(),
    )


@router.get("/invoices", response_model=List[InvoiceItem], summary="List invoice history")
async def list_invoices(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
):
    """Return all invoices stored for the organization."""
    organization, _ = org_data
    raw = organization.invoices_json
    if not raw:
        return []
    try:
        items = json.loads(raw)
        return [InvoiceItem(**item) for item in items]
    except Exception:
        return []


# ── Internal helper ────────────────────────────────────────────────────────

def _append_invoice(org: Organization, tier: str, cents: int, now: datetime, period_end: datetime) -> None:
    """Append a simulated invoice record to the org's JSON invoice list."""
    existing: list = []
    if org.invoices_json:
        try:
            existing = json.loads(org.invoices_json)
        except Exception:
            existing = []

    invoice = {
        "id": f"inv_{uuid.uuid4().hex[:12]}",
        "tier": tier,
        "amount_cents": cents,
        "amount_display": _price_display(cents),
        "status": "paid" if cents > 0 else "free",
        "period_start": now.isoformat(),
        "period_end": period_end.isoformat(),
        "created_at": now.isoformat(),
        "pdf_url": None,
    }
    existing.insert(0, invoice)  # newest first
    org.invoices_json = json.dumps(existing)
