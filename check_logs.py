"""Quick script to check validation logs"""
import asyncio
from sqlalchemy import select, func
from backend.db.connection import engine
from backend.models.validation_log import ValidationLog
from backend.models.organization import Organization
from sqlalchemy.ext.asyncio import AsyncSession


async def check_logs():
    async with AsyncSession(engine) as session:
        # Count total logs
        result = await session.execute(select(func.count()).select_from(ValidationLog))
        count = result.scalar()
        print(f'\n📊 Total validation logs: {count}')
        
        # Get recent logs
        result = await session.execute(
            select(ValidationLog)
            .order_by(ValidationLog.created_at.desc())
            .limit(5)
        )
        logs = result.scalars().all()
        
        if logs:
            print('\n📝 Recent validations:')
            for log in logs:
                print(f'  ✓ ID: {log.validation_id}')
                print(f'    Result: {log.result}, Latency: {log.latency_ms}ms')
                print(f'    Auto-corrected: {log.auto_corrected}')
                print(f'    Violations: {len(log.violations) if log.violations else 0}')
                print()
        else:
            print('\n❌ No validation logs found')
        
        # Check organization usage
        result = await session.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(3)
        )
        orgs = result.scalars().all()
        
        if orgs:
            print('👥 Recent organizations:')
            for org in orgs:
                print(f'  - {org.name}: {org.usage_current_month}/{org.monthly_quota} validations used')


if __name__ == "__main__":
    asyncio.run(check_logs())
