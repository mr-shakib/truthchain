from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from dotenv import load_dotenv

# Add the backend directory and its parent to sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
parent_dir = str(Path(__file__).resolve().parent.parent.parent)

# Add both paths
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models for autogenerate support
import sys
import os

# Make sure the backend directory is in the path
backend_path = str(Path(__file__).resolve().parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Now we can import from backend modules
from backend.db.base import Base
from backend.models.organization import Organization
from backend.models.api_key import APIKey
from backend.models.validation_log import ValidationLog

# Set target_metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url from environment
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:nacht0905@localhost:5432/truthchain")
config.set_main_option("sqlalchemy.url", database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # For async engine, we need to handle this differently
    import asyncio
    
    async def run_async_migrations():
        """Run migrations in async mode"""
        # Use the database URL from config
        database_url = config.get_main_option("sqlalchemy.url")
        
        # Create async engine
        connectable = create_async_engine(
            database_url,
            poolclass=pool.NullPool,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

        await connectable.dispose()

    def do_run_migrations(connection):
        """Synchronous function to run migrations"""
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
    
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
