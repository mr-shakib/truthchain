"""
Analytics API Routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta

from ...core.analytics import (
    OrganizationAnalytics,
    ValidationStats,
    UsageStats,
    DailyStats,
    ViolationSummary,
    get_analytics
)
from ...models.organization import Organization
from ...models.api_key import APIKey
from ...db.connection import get_db
from ..dependencies import get_current_organization


router = APIRouter(prefix="/v1/analytics", tags=["Analytics"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive analytics overview for the current organization
    
    Returns:
        - Validation statistics (total, passed, failed, success rate, etc.)
        - Usage statistics (quota, current usage, remaining)
        - Daily statistics for the last 7 days
        - Recent validations
        - Top violations
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    return await get_analytics(db, organization.id)


@router.get("/validation-stats", response_model=ValidationStats)
async def get_validation_statistics(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get validation statistics for the current organization
    
    Includes:
    - Total validations
    - Count by status (passed/failed/warning)
    - Success rate percentage
    - Average latency
    - Auto-correction statistics
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    analytics = OrganizationAnalytics(db)
    return await analytics.get_validation_stats(organization.id)


@router.get("/usage-stats", response_model=UsageStats)
async def get_usage_statistics(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get quota usage statistics for the current organization
    
    Includes:
    - Current monthly usage
    - Monthly quota
    - Usage percentage
    - Remaining quota
    - Tier information
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    analytics = OrganizationAnalytics(db)
    return await analytics.get_usage_stats(organization.id)


@router.get("/daily-stats")
async def get_daily_statistics(
    days: int = 30,
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily validation statistics for the last N days
    
    Args:
        days: Number of days to retrieve (default: 30, max: 90)
    
    Returns:
        List of daily statistics with date, total, passed, failed, warnings
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    
    # Limit to 90 days maximum
    days = min(days, 90)
    
    analytics = OrganizationAnalytics(db)
    stats = await analytics.get_daily_stats(organization.id, days)
    return [stat.dict() for stat in stats]


@router.get("/recent-validations")
async def get_recent_validation_logs(
    limit: int = 10,
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent validation logs for the current organization
    
    Args:
        limit: Number of recent logs to retrieve (default: 10, max: 100)
    
    Returns:
        List of recent validation logs with summary information
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    
    # Limit to 100 maximum
    limit = min(limit, 100)
    
    analytics = OrganizationAnalytics(db)
    return await analytics.get_recent_validations(organization.id, limit)


@router.get("/top-violations")
async def get_top_violation_summary(
    limit: int = 10,
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most common validation violations for the current organization
    
    Args:
        limit: Number of top violations to return (default: 10, max: 50)
    
    Returns:
        List of violations sorted by frequency
    
    **Requires authentication via X-API-Key header**
    """
    organization, _ = org_data
    
    # Limit to 50 maximum
    limit = min(limit, 50)
    
    analytics = OrganizationAnalytics(db)
    violations = await analytics.get_top_violations(organization.id, limit)
    return [v.dict() for v in violations]


@router.get("/health")
async def analytics_health():
    """Health check for analytics service"""
    return {
        "status": "healthy",
        "service": "analytics",
        "version": "1.0.0"
    }
