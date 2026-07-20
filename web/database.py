<<<<<<< ours
import os
=======
"""
Async SQLAlchemy engine + session factory, pointed at Postgres
(Supabase in production; any Postgres works for local dev).

Table creation is handled by Alembic (see web/alembic/) -- `init_db()`
below is a dev-only convenience for spinning up a scratch database
without running migrations, not something production startup should call.
"""
from __future__ import annotations

>>>>>>> theirs
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

<<<<<<< ours
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://researchos:researchos@localhost:5432/researchos",
)

ECHO_SQL = os.environ.get("SQL_ECHO", "false").lower() == "true"

engine = create_async_engine(
    DATABASE_URL,
    echo=ECHO_SQL,
    pool_pre_ping=True,   
=======
from core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
>>>>>>> theirs
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
<<<<<<< ours
    """FastAPI dependency — yields a session and guarantees cleanup."""
=======
    """FastAPI dependency -- yields a session and guarantees cleanup."""
>>>>>>> theirs
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
<<<<<<< ours
    Dev convenience only — creates tables directly from models.
    In every real environment, use Alembic migrations instead
    (see web/backend/alembic/).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
=======
    Dev convenience only -- creates tables directly from models.py.
    Everywhere else, use Alembic migrations instead:

        cd web && alembic upgrade head
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
>>>>>>> theirs
