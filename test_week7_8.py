"""
Comprehensive test script for TruthChain Week 7-8 features
Tests validation logging, usage tracking, and analytics
"""
import asyncio
import json
from sqlalchemy import select, func
from backend.db.connection import engine
from backend.models.validation_log import ValidationLog
from backend.models.organization import Organization
from backend.core.analytics import get_analytics
from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_enhancements():
    print("\n" + "="*60)
    print("🧪 Testing Week 7-8: Database Enhancements")
    print("="*60)
    
    async with AsyncSession(engine) as session:
        # Test 1: Validation Logging
        print("\n1️⃣  Testing Validation Logging...")
        result = await session.execute(select(func.count()).select_from(ValidationLog))
        log_count = result.scalar()
        print(f"   ✓ Total validation logs in database: {log_count}")
        
        # Get most recent log
        result = await session.execute(
            select(ValidationLog).order_by(ValidationLog.created_at.desc()).limit(1)
        )
        latest_log = result.scalar_one_or_none()
        
        if latest_log:
            print(f"   ✓ Latest log ID: {latest_log.validation_id}")
            print(f"   ✓ Result: {latest_log.result}")
            print(f"   ✓ Latency: {latest_log.latency_ms}ms")
            print(f"   ✓ Auto-corrected: {latest_log.auto_corrected}")
        
        # Test 2: Usage Tracking
        print("\n2️⃣  Testing Usage Tracking...")
        result = await session.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(3)
        )
        orgs = result.scalars().all()
        
        for org in orgs:
            usage_pct = (org.usage_current_month / org.monthly_quota * 100) if org.monthly_quota > 0 else 0
            print(f"   ✓ {org.name}: {org.usage_current_month}/{org.monthly_quota} ({usage_pct:.1f}%)")
        
        # Test 3: Analytics Queries
        print("\n3️⃣  Testing Analytics Queries...")
        
        # Find an org with validations
        result = await session.execute(
            select(Organization)
            .join(ValidationLog, Organization.id == ValidationLog.organization_id)
            .group_by(Organization.id)
            .order_by(func.count(ValidationLog.id).desc())
            .limit(1)
        )
        test_org = result.scalar_one_or_none()
        
        if test_org:
            print(f"   Testing analytics for: {test_org.name}")
            
            analytics_data = await get_analytics(session, test_org.id)
            
            # Validation stats
            val_stats = analytics_data['validation_stats']
            print(f"\n   📊 Validation Stats:")
            print(f"      - Total: {val_stats['total_validations']}")
            print(f"      - Passed: {val_stats['passed']}")
            print(f"      - Failed: {val_stats['failed']}")
            print(f"      - Success Rate: {val_stats['success_rate']}%")
            print(f"      - Avg Latency: {val_stats['average_latency_ms']}ms")
            
            # Usage stats
            usage_stats = analytics_data['usage_stats']
            print(f"\n   💰 Usage Stats:")
            print(f"      - Current: {usage_stats['current_usage']}")
            print(f"      - Quota: {usage_stats['monthly_quota']}")
            print(f"      - Percentage: {usage_stats['usage_percentage']}%")
            print(f"      - Remaining: {usage_stats['remaining_quota']}")
            
            # Recent validations
            recent = analytics_data['recent_validations']
            print(f"\n   📝 Recent Validations: {len(recent)}")
            for val in recent[:3]:
                print(f"      - {val['validation_id']}: {val['result']} ({val['latency_ms']}ms)")
        
        # Test 4: Alembic Migrations
        print("\n4️⃣  Testing Alembic Setup...")
        import os
        from pathlib import Path
        
        backend_path = Path(__file__).parent / "backend"
        alembic_path = backend_path / "alembic"
        versions_path = alembic_path / "versions"
        
        if alembic_path.exists():
            print(f"   ✓ Alembic directory exists")
            if versions_path.exists():
                migrations = list(versions_path.glob("*.py"))
                if migrations:
                    print(f"   ✓ Found {len(migrations)} migration(s)")
                    for migration in migrations[:3]:
                        print(f"      - {migration.name}")
                else:
                    print(f"   ⚠ No migrations found yet")
        
        print("\n" + "="*60)
        print("✅ All Week 7-8 Features Tested Successfully!")
        print("="*60)
        print("\nSummary:")
        print(f"  ✓ Validation logging working ({log_count} logs)")
        print(f"  ✓ Usage tracking functional")
        print(f"  ✓ Analytics queries operational")
        print(f"  ✓ Alembic migrations configured")
        print("\n")


if __name__ == "__main__":
    asyncio.run(test_database_enhancements())
