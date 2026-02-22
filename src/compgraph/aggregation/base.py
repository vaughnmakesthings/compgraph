"""Base class for truncate+insert aggregation jobs."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AggregationJob(ABC):
    """Base for all aggregation rebuild jobs.

    Subclasses define table_name and compute_rows().
    The run() method handles truncate+insert in a transaction.
    """

    table_name: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "table_name", None) and not getattr(cls, "__abstractmethods__", None):
            raise TypeError(f"{cls.__name__} must define table_name")

    @abstractmethod
    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        """Compute aggregated rows from source tables. Returns list of dicts."""
        ...

    async def run(self, session: AsyncSession) -> int:
        """Truncate the target table and insert freshly computed rows."""
        logger.info("[AGG] Starting rebuild of %s", self.table_name)

        await session.execute(text(f"TRUNCATE TABLE {self.table_name}"))

        rows = await self.compute_rows(session)
        if not rows:
            logger.warning("[AGG] %s: compute_rows returned 0 rows", self.table_name)
            await session.commit()
            return 0

        columns = rows[0].keys()
        col_list = ", ".join(columns)
        val_list = ", ".join(f":{c}" for c in columns)
        stmt = text(
            f"INSERT INTO {self.table_name} ({col_list}) VALUES ({val_list})"  # noqa: S608
        )

        await session.execute(stmt, rows)
        await session.commit()

        logger.info("[AGG] %s: inserted %d rows", self.table_name, len(rows))
        return len(rows)
