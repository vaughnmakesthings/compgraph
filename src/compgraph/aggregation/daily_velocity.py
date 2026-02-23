from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """
WITH active_by_date AS (
    SELECT
        ps.snapshot_date AS date,
        p.company_id,
        COUNT(DISTINCT ps.posting_id) AS active_postings,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.first_seen_at::date = ps.snapshot_date
        ) AS new_postings
    FROM posting_snapshots ps
    JOIN postings p ON p.id = ps.posting_id
    GROUP BY ps.snapshot_date, p.company_id
),
closed_by_date AS (
    SELECT
        (p.last_seen_at::date + INTERVAL '1 day')::date AS date,
        p.company_id,
        COUNT(DISTINCT p.id) AS closed_postings
    FROM postings p
    WHERE p.is_active = false
    AND p.last_seen_at IS NOT NULL
    GROUP BY (p.last_seen_at::date + INTERVAL '1 day')::date, p.company_id
)
SELECT
    a.date,
    a.company_id,
    a.active_postings,
    a.new_postings,
    COALESCE(c.closed_postings, 0) AS closed_postings,
    a.new_postings - COALESCE(c.closed_postings, 0) AS net_change
FROM active_by_date a
LEFT JOIN closed_by_date c ON c.date = a.date AND c.company_id = a.company_id
ORDER BY a.date, a.company_id
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
