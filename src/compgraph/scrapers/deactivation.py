"""Posting deactivation: marks postings as inactive after consecutive missed scrape runs."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Posting, ScrapeRun, ScrapeRunStatus

logger = logging.getLogger(__name__)

GRACE_PERIOD_RUNS = 1


async def deactivate_stale_postings(
    session: AsyncSession,
    company_id: uuid.UUID,
    scrape_run_id: uuid.UUID,
) -> int:
    """Deactivate postings not seen since the most recent completed scrape run.

    Uses a grace period of 1 completed run. We order by completed_at to correctly
    identify which runs completed most recently (handles overlapping runs), but use
    started_at as the cutoff value since last_seen_at is recorded during the run
    (after started_at but before completed_at).

    Returns the number of postings deactivated.
    """
    # Get the started_at of the most recent completed run (ordered by completion)
    cutoff_query = (
        select(ScrapeRun.started_at)
        .where(
            ScrapeRun.company_id == company_id,
            ScrapeRun.status == ScrapeRunStatus.COMPLETED,
        )
        .order_by(ScrapeRun.completed_at.desc())
        .offset(GRACE_PERIOD_RUNS - 1)
        .limit(1)
    )
    cutoff_result = await session.execute(cutoff_query)
    cutoff_time = cutoff_result.scalar_one_or_none()

    if cutoff_time is None:
        logger.debug(
            "Fewer than %d completed runs for company %s — skipping deactivation",
            GRACE_PERIOD_RUNS,
            company_id,
        )
        return 0

    # Deactivate postings whose last_seen_at is before the cutoff
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
