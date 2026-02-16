"""Sync database layer for Streamlit dashboard.

Uses psycopg2 (sync) instead of asyncpg — Streamlit is synchronous.
Does NOT import from compgraph.db.session (that's async-only).
"""

import logging
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
    pool_size=2,
    max_overflow=1,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)

_SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a sync SQLAlchemy session (read-only queries)."""
    session = _SessionFactory()
    try:
        yield session
    except Exception:
        logger.exception("Dashboard database session error")
        raise
    finally:
        session.close()
