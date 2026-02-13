"""Shared test fixtures for CompGraph.

Fixtures are organized into tiers:
- Unit test fixtures (no DB): client, settings_override
- Integration test fixtures (live DB): async_session, seeded_db

Integration fixtures require DATABASE_PASSWORD in env and are marked with
@pytest.mark.integration so they're skipped by default in CI/local.
"""

from __future__ import annotations

import os

# Set placeholder before any compgraph imports trigger Settings() validation
os.environ.setdefault("DATABASE_PASSWORD", "test-placeholder")

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Unit test fixtures (no database required)
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Sync test client for unit-testing API endpoints without DB."""
    os.environ.setdefault("DATABASE_PASSWORD", "test-placeholder")
    from compgraph.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def settings_override():
    """Override settings for isolated unit tests.

    Usage:
        def test_something(settings_override):
            with settings_override(ENVIRONMENT="test", PORT=9999):
                from compgraph.config import settings
                assert settings.ENVIRONMENT == "test"
    """
    from compgraph.config import Settings

    def _override(**overrides):
        props = {k: property(lambda self, v=v: v) for k, v in overrides.items()}
        return patch.multiple(Settings, **props)

    return _override


# ---------------------------------------------------------------------------
# Integration test fixtures (requires live Supabase connection)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def integration_engine():
    """Create a test engine for integration tests.

    Uses the real DATABASE_PASSWORD from env but connects to the same
    Supabase instance. Integration tests are isolated via transactions.
    """
    db_password = os.environ.get("DATABASE_PASSWORD")
    if not db_password or db_password == "test-placeholder":  # noqa: S105
        pytest.skip("DATABASE_PASSWORD not set — skipping integration tests")

    from compgraph.config import settings

    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=2,
        max_overflow=0,
        connect_args={"ssl": "require"},
    )
    return engine


@pytest.fixture
async def async_session(integration_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session that rolls back after each test.

    This gives each integration test a clean slate without mutating the DB.
    """
    async with integration_engine.connect() as conn:
        transaction = await conn.begin()
        session_factory = async_sessionmaker(bind=conn, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            yield session

        # Roll back the outer transaction — nothing persists
        await transaction.rollback()


@pytest.fixture
async def seeded_db(async_session: AsyncSession) -> AsyncSession:
    """Session with seed data for integration tests.

    Inserts the 4 target companies so tests can reference them.
    Add more seed data here as needed.
    """
    from compgraph.db.models import Company

    companies = [
        Company(
            name="Advantage Solutions",
            slug="advantage",
            ats_platform="workday",
            career_site_url="https://careers.advantagesolutions.net",
        ),
        Company(
            name="Acosta Group",
            slug="acosta",
            ats_platform="workday",
            career_site_url="https://careers.acosta.com",
        ),
        Company(
            name="BDS Connected Solutions",
            slug="bds",
            ats_platform="icims",
            career_site_url="https://bdsconnected.com/careers",
        ),
        Company(
            name="MarketSource",
            slug="marketsource",
            ats_platform="icims",
            career_site_url="https://www.marketsource.com/careers",
        ),
    ]
    async_session.add_all(companies)
    await async_session.flush()
    return async_session
