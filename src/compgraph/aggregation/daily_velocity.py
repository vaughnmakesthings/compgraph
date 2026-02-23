from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """
WITH daily_stats AS (
    SELECT
        ps.snapshot_date AS date,
        p.company_id,
        COUNT(DISTINCT ps.posting_id) AS active_postings,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.first_seen_at::date = ps.snapshot_date
        ) AS new_postings,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.is_active = false
            AND p.last_seen_at::date = ps.snapshot_date
        ) AS closed_postings
    FROM posting_snapshots ps
    JOIN postings p ON p.id = ps.posting_id
    GROUP BY ps.snapshot_date, p.company_id
)
SELECT
    date,
    company_id,
    active_postings,
    new_postings,
    closed_postings,
    new_postings - closed_postings AS net_change
FROM daily_stats
ORDER BY date, company_id
"""


class DailyVelocityJob(AggregationJob):
    table_name = "agg_daily_velocity"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        rows: list[dict] = []
        for row in result:
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "date": row.date,
                    "company_id": str(row.company_id),
                    "brand_id": None,
                    "market_id": None,
                    "active_postings": row.active_postings,
                    "new_postings": row.new_postings,
                    "closed_postings": row.closed_postings,
                    "net_change": row.net_change,
                }
            )
        return rows
