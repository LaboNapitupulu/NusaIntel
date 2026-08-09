from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DatabaseProbe = Callable[[], Awaitable[None]]


def create_database_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def create_database_probe(
    session_factory: async_sessionmaker[AsyncSession],
) -> DatabaseProbe:
    async def probe() -> None:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))

    return probe
