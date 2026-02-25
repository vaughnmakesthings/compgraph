from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.config import Settings, settings
from compgraph.db.session import async_session_factory


def get_settings() -> Settings:
    """Shared settings dependency — override in tests via app.dependency_overrides."""
    return settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
