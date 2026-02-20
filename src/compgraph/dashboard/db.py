"""Sync database layer for Streamlit dashboard.

Uses psycopg2 (sync) instead of asyncpg — Streamlit is synchronous.
Does NOT import from compgraph.db.session (that's async-only).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from compgraph.config import settings

logger = logging.getLogger(__name__)

# Swap async driver for sync psycopg2
_sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

engine = create_engine(
    _sync_url,
    pool_size=settings.DASHBOARD_DB_POOL_SIZE,
    max_overflow=settings.DASHBOARD_DB_MAX_OVERFLOW,
    pool_timeout=settings.DASHBOARD_DB_POOL_TIMEOUT,
    pool_recycle=settings.DASHBOARD_DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

_SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a sync SQLAlchemy session (read-only queries)."""
    start = time.perf_counter()
    logger.debug("db.session.open pool=%s", engine.pool.status())
    session = _SessionFactory()
    try:
        yield session
    except Exception:
        logger.exception("Dashboard database session error")
        raise
    finally:
        elapsed = time.perf_counter() - start
        session.close()
        if elapsed > 2.0:
            logger.warning("db.session.slow duration=%.3fs", elapsed)
        logger.debug("db.session.close duration=%.3fs", elapsed)
