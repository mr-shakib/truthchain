"""
Analytics Module for TruthChain
Provides analytics queries for organization dashboards
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from ..models.validation_log import ValidationLog
from ..models.organization import Organization


class ValidationStats(BaseModel):
    """Statistics about validations"""
    total_validations: int
    passed: int
    failed: int
    warnings: int
    success_rate: float
    average_latency_ms: float
    auto_corrected_count: int
    auto_correction_rate: float


class UsageStats(BaseModel):
    """Usage statistics for an organization"""
    current_usage: int
    monthly_quota: int
    usage_percentage: float
    remaining_quota: int
    tier: str


class DailyStats(BaseModel):
    """Daily validation statistics"""
    date: str
    total: int
    passed: int
    failed: int
    warnings: int


class ViolationSummary(BaseModel):
    """Summary of common violations"""
    rule_name: str
    violation_count: int
    severity: str
    most_common_field: Optional[str] = None


class OrganizationAnalytics:
    """Analytics service for organization data"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_validation_stats(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ValidationStats:
        """
        Get validation statistics for an organization
        
        Args:
            organization_id: Organization UUID
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            ValidationStats with aggregated metrics
        """
        # Build query filters
        filters = [ValidationLog.organization_id == organization_id]
        if start_date:
            filters.append(ValidationLog.created_at >= start_date)
        if end_date:
            filters.append(ValidationLog.created_at <= end_date)
        
        # Query for aggregated stats
        query = select(
            func.count(ValidationLog.id).label("total"),
            func.count(case((ValidationLog.result == "passed", 1))).label("passed"),
            func.count(case((ValidationLog.result == "failed", 1))).label("failed"),
            func.count(case((ValidationLog.result == "warning", 1))).label("warnings"),
            func.avg(ValidationLog.latency_ms).label("avg_latency"),
            func.count(case((ValidationLog.auto_corrected == True, 1))).label("auto_corrected")
        ).where(and_(*filters))
        
        result = await self.db.execute(query)
        row = result.one()
        
        # Calculate rates
        total = row.total or 0
        success_rate = (row.passed / total * 100) if total > 0 else 0.0
        auto_correction_rate = (row.auto_corrected / total * 100) if total > 0 else 0.0
        
        return ValidationStats(
            total_validations=total,
            passed=row.passed or 0,
            failed=row.failed or 0,
            warnings=row.warnings or 0,
            success_rate=round(success_rate, 2),
            average_latency_ms=round(row.avg_latency or 0, 2),
            auto_corrected_count=row.auto_corrected or 0,
            auto_correction_rate=round(auto_correction_rate, 2)
        )
    
    async def get_usage_stats(self, organization_id: str) -> UsageStats:
        """
        Get quota usage statistics for an organization
        
        Args:
            organization_id: Organization UUID
        
        Returns:
            UsageStats with quota information
        """
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        usage_percentage = (org.usage_current_month / org.monthly_quota * 100) if org.monthly_quota > 0 else 0.0
        
        return UsageStats(
            current_usage=org.usage_current_month,
            monthly_quota=org.monthly_quota,
            usage_percentage=round(usage_percentage, 2),
            remaining_quota=org.monthly_quota - org.usage_current_month,
            tier=org.tier
        )
    
    async def get_daily_stats(
        self,
        organization_id: str,
        days: int = 30
    ) -> List[DailyStats]:
        """
        Get daily validation statistics for the last N days
        
        Args:
            organization_id: Organization UUID
            days: Number of days to retrieve (default 30)
        
        Returns:
            List of DailyStats for each day
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query grouped by date
        query = select(
            func.date(ValidationLog.created_at).label("date"),
            func.count(ValidationLog.id).label("total"),
            func.count(case((ValidationLog.result == "passed", 1))).label("passed"),
            func.count(case((ValidationLog.result == "failed", 1))).label("failed"),
            func.count(case((ValidationLog.result == "warning", 1))).label("warnings")
        ).where(
            and_(
                ValidationLog.organization_id == organization_id,
                ValidationLog.created_at >= start_date
            )
        ).group_by(
            func.date(ValidationLog.created_at)
        ).order_by(
            desc(func.date(ValidationLog.created_at))
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            DailyStats(
                date=row.date.isoformat() if row.date else "",
                total=row.total or 0,
                passed=row.passed or 0,
                failed=row.failed or 0,
                warnings=row.warnings or 0
            )
            for row in rows
        ]
    
    async def get_recent_validations(
        self,
        organization_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent validation logs for an organization
        
        Args:
            organization_id: Organization UUID
            limit: Number of recent logs to retrieve (default 10)
        
        Returns:
            List of validation log dictionaries
        """
        query = select(ValidationLog).where(
            ValidationLog.organization_id == organization_id
        ).order_by(
            desc(ValidationLog.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "validation_id": log.validation_id,
                "result": log.result,
                "latency_ms": log.latency_ms,
                "auto_corrected": log.auto_corrected,
                "violations_count": len(log.violations) if log.violations else 0,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    
    async def get_top_violations(
        self,
        organization_id: str,
        limit: int = 10
    ) -> List[ViolationSummary]:
        """
        Get the most common validation violations
        
        Args:
            organization_id: Organization UUID
            limit: Number of top violations to return (default 10)
        
        Returns:
            List of ViolationSummary with most common violations
        """
        # Get all logs with violations
        query = select(ValidationLog.violations).where(
            and_(
                ValidationLog.organization_id == organization_id,
                ValidationLog.violations.isnot(None)
            )
        )
        
        result = await self.db.execute(query)
        all_violations = result.scalars().all()
        
        # Count violations by rule_name
        violation_counts: Dict[str, Dict] = {}
        for violations_list in all_violations:
            if not violations_list:
                continue
            for violation in violations_list:
                rule_name = violation.get("rule_name", "unknown")
                if rule_name not in violation_counts:
                    violation_counts[rule_name] = {
                        "count": 0,
                        "severity": violation.get("severity", "unknown"),
                        "fields": {}
                    }
                violation_counts[rule_name]["count"] += 1
                field = violation.get("field", "")
                if field:
                    violation_counts[rule_name]["fields"][field] = violation_counts[rule_name]["fields"].get(field, 0) + 1
        
        # Convert to list and sort by count
        violation_list = [
            ViolationSummary(
                rule_name=rule_name,
                violation_count=data["count"],
                severity=data["severity"],
                most_common_field=max(data["fields"].items(), key=lambda x: x[1])[0] if data["fields"] else None
            )
            for rule_name, data in violation_counts.items()
        ]
        
        # Sort by count descending and limit
        violation_list.sort(key=lambda x: x.violation_count, reverse=True)
        return violation_list[:limit]


# Convenience function for quick analytics access
async def get_analytics(db: AsyncSession, organization_id: str) -> Dict[str, Any]:
    """
    Get a comprehensive analytics overview for an organization
    
    Args:
        db: Database session
        organization_id: Organization UUID
    
    Returns:
        Dictionary with all analytics data
    """
    analytics = OrganizationAnalytics(db)
    
    # Get all analytics in parallel would be ideal, but for simplicity we'll do sequential
    validation_stats = await analytics.get_validation_stats(organization_id)
    usage_stats = await analytics.get_usage_stats(organization_id)
    daily_stats = await analytics.get_daily_stats(organization_id, days=7)
    recent_validations = await analytics.get_recent_validations(organization_id, limit=5)
    top_violations = await analytics.get_top_violations(organization_id, limit=5)
    
    return {
        "validation_stats": validation_stats.dict(),
        "usage_stats": usage_stats.dict(),
        "daily_stats": [stat.dict() for stat in daily_stats],
        "recent_validations": recent_validations,
        "top_violations": [v.dict() for v in top_violations]
    }
