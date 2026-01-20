import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.user import User
from app.models.contractor import Contractor
from app.models.project import Project
from sqlmodel import SQLModel

from app.models import *


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# target metadata
target_metadata = SQLModel.metadata

# -----------------------
# SYNC migration
# -----------------------
def run_migrations_offline():
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# -----------------------
# ASYNC migration
# -----------------------
async def run_migrations_online():
    """Run migrations in async mode."""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection: Connection):
    """Run the migrations on the connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    context.run_migrations()  # must NOT pass arguments

# -----------------------
# Entry point
# -----------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
