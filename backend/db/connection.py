"""
Database Connection Module
Handles PostgreSQL connections with fallback for development
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

# Import Base from db.base
from .base import Base

# Use the centralised settings object (which reads .env with an absolute path fix)
# so this module works regardless of the uvicorn working directory.
from ..config.settings import settings

DATABASE_URL = settings.DATABASE_URL
REDIS_URL    = settings.REDIS_URL

# For local development outside Docker, use this:
# DATABASE_URL = "sqlite+aiosqlite:///./truthchain.db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    
    Usage in FastAPI:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    await engine.dispose()


def get_redis_url() -> str:
    """Get Redis URL for caching"""
    return REDIS_URL
