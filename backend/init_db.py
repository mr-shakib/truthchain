"""
Initialize Database Tables
Run this script to create all database tables
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from db.base import Base

# Import all models to register them with Base
from backend.models.organization import Organization
from backend.models.api_key import APIKey
from backend.models.validation_log import ValidationLog

# Use localhost for local development
LOCAL_DB_URL = "postgresql+asyncpg://truthchain:devpass123@localhost:5432/truthchain"

# Create engine
engine = create_async_engine(LOCAL_DB_URL, echo=True)


async def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    
    try:
        async with engine.begin() as conn:
            # Drop all tables (use carefully!)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("\n✅ Database tables created successfully!")
        
        # Show created tables using docker exec
        print("\nVerifying tables in database...")
        import subprocess
        result = subprocess.run(
            [
                "docker", "exec", "truthchain_db",
                "psql", "-U", "truthchain", "-d", "truthchain",
                "-c", "\\dt"
            ],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        print("\nNote: Since local connection doesn't work, let's use Docker exec instead...")
        print("\nRun these commands to create tables:")
        print("  docker exec -it truthchain_db psql -U truthchain -d truthchain")
        print("  Then paste the CREATE TABLE commands")
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
