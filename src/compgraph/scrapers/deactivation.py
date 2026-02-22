"""Posting deactivation: marks postings as inactive after consecutive missed scrape runs."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from compgraph.db.models import Posting, ScrapeRun, ScrapeRunStatus

logger = logging.getLogger(__name__)

GRACE_PERIOD_RUNS = 1


async def deactivate_stale_postings(
    session: AsyncSession,
    company_id: uuid.UUID,
    scrape_run_id: uuid.UUID,
) -> int:
    pending_cutoff = (
        select(func.min(ScrapeRun.started_at))
        .where(
            ScrapeRun.company_id == company_id,
            ScrapeRun.status == ScrapeRunStatus.PENDING,
        )
        .correlate(None)
        .scalar_subquery()
    )

    cutoff_query = (
        select(ScrapeRun.started_at)
        .where(
            ScrapeRun.company_id == company_id,
            ScrapeRun.status == ScrapeRunStatus.COMPLETED,
            ScrapeRun.id != scrape_run_id,
            or_(
                pending_cutoff.is_(None),
                ScrapeRun.completed_at < pending_cutoff,
            ),
        )
        .order_by(ScrapeRun.completed_at.desc())
        .offset(GRACE_PERIOD_RUNS - 1)
        .limit(1)
    )
    cutoff_result = await session.execute(cutoff_query)
    cutoff_time = cutoff_result.scalar_one_or_none()

    if cutoff_time is None:
        logger.debug(
            "Fewer than %d safe completed runs for company %s — skipping deactivation",
            GRACE_PERIOD_RUNS,
            company_id,
        )
        return 0

    deactivate_stmt = (
        update(Posting)
        .where(
            Posting.company_id == company_id,
            Posting.is_active.is_(True),
            Posting.last_seen_at < cutoff_time,
        )
        .values(is_active=False)
    )
    cursor_result = await session.execute(deactivate_stmt)
    count: int = cursor_result.rowcount  # type: ignore[attr-defined]

    if count > 0:
        logger.info(
            "Deactivated %d stale postings for company %s (cutoff: %s, run: %s)",
            count,
            company_id,
            cutoff_time,
            scrape_run_id,
        )

    return count
