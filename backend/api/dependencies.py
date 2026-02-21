"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple

from ..db.connection import get_db
from ..models.organization import Organization
from ..models.api_key import APIKey
from ..core.auth import verify_api_key as verify_api_key_util, check_quota
from ..core.rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded


async def get_current_organization(
    x_api_key: str = Header(..., description="API key for authentication"),
    db: AsyncSession = Depends(get_db)
) -> Tuple[Organization, APIKey]:
    """
    Verify API key and return the current organization
    
    Usage:
        @router.get("/protected")
        async def protected_route(
            org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
        ):
            organization, api_key = org_data
            ...
    """
    result = await verify_api_key_util(db, x_api_key)
    
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key"
        )
    
    return result


async def require_quota(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
) -> Tuple[Organization, APIKey]:
    """
    Verify API key and check that organization has quota remaining
    
    Usage:
        @router.post("/validate")
        async def validate(
            org_data: Tuple[Organization, APIKey] = Depends(require_quota)
        ):
            organization, api_key = org_data
            ...
    """
    organization, api_key = org_data

    # Block if subscription is canceled or past_due
    status = organization.subscription_status or "active"
    if status in ("canceled", "past_due"):
        raise HTTPException(
            status_code=402,
            detail=f"Subscription {status}. Please update your billing to continue using the API."
        )

    if not check_quota(organization):
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exhausted. Quota: {organization.monthly_quota}, Used: {organization.usage_current_month}"
        )

    return organization, api_key


async def check_rate_limit(
    request: Request,
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
) -> Tuple[Organization, APIKey]:
    """
    Check rate limits for the organization
    
    Returns organization and API key if rate limit not exceeded.
    Raises 429 HTTPException if rate limit exceeded.
    
    Usage:
        @router.post("/validate")
        async def validate(
            org_data: Tuple[Organization, APIKey] = Depends(check_rate_limit)
        ):
            organization, api_key = org_data
            ...
    """
    organization, api_key = org_data
    
    # Create rate limiter
    rate_limiter = RateLimiter()
    
    try:
        # Get rate limit config based on organization tier
        tier_str = organization.tier if isinstance(organization.tier, str) else organization.tier.value
        config = RateLimitConfig(tier=tier_str)
        
        # Check rate limit
        result = await rate_limiter.check_rate_limit(
            organization_id=str(organization.id),
            config=config
        )
        
        # Add rate limit headers to response
        # These will be added by the endpoint
        request.state.rate_limit_result = result
        
    except RateLimitExceeded as e:
        # Rate limit exceeded - raise 429
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {e.retry_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(e.result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": e.result.reset_at.isoformat(),
                "Retry-After": str(e.retry_after)
            }
        )
    finally:
        await rate_limiter.close()
    
    return organization, api_key


async def require_quota_and_rate_limit(
    request: Request,
    org_data: Tuple[Organization, APIKey] = Depends(check_rate_limit)
) -> Tuple[Organization, APIKey]:
    """
    Combined dependency: check both quota and rate limits
    
    This is the recommended dependency for production validation endpoints.
    
    Usage:
        @router.post("/validate")
        async def validate(
            org_data: Tuple[Organization, APIKey] = Depends(require_quota_and_rate_limit)
        ):
            organization, api_key = org_data
            ...
    """
    organization, api_key = org_data
    
    # Check quota
    if not check_quota(organization):
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exhausted. Quota: {organization.monthly_quota}, Used: {organization.usage_current_month}"
        )
    
    return organization, api_key
