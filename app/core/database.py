from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Async SQLModel engine + session
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Run SQLModel metadata.create_all() using an async connection.
    Note: in production, Alembic migrations should manage schema. This helper
    is useful for local dev / tests when MIGRATE_ON_START is enabled.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
