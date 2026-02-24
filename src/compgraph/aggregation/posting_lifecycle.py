from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """
WITH latest_enrichment AS (
    SELECT DISTINCT ON (posting_id)
        posting_id,
        id AS enrichment_id
    FROM posting_enrichments
    ORDER BY posting_id, enriched_at DESC NULLS LAST
),
posting_durations AS (
    SELECT
        p.company_id,
        pe.role_archetype,
        DATE_TRUNC('month', p.first_seen_at)::date AS period,
        GREATEST(0, EXTRACT(EPOCH FROM (
            COALESCE(p.last_seen_at, NOW()) - p.first_seen_at
        )) / 86400.0) AS days_open,
        p.times_reposted
    FROM postings p
    JOIN latest_enrichment le ON le.posting_id = p.id
    JOIN posting_enrichments pe ON pe.id = le.enrichment_id
    WHERE p.first_seen_at IS NOT NULL
)
SELECT
    company_id,
    role_archetype,
    period,
    AVG(days_open) AS avg_days_open,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_open) AS median_days_open,
    CASE
        WHEN COUNT(*) > 0
        THEN COUNT(*) FILTER (WHERE times_reposted > 0)::float / COUNT(*)
        ELSE 0
    END AS repost_rate,
    COALESCE(
        AVG(days_open / NULLIF(times_reposted, 0)) FILTER (WHERE times_reposted > 0),
        0
    ) AS avg_repost_gap_days
FROM posting_durations
GROUP BY company_id, role_archetype, period
ORDER BY company_id, role_archetype, period
"""


class PostingLifecycleJob(AggregationJob):
    table_name = "agg_posting_lifecycle"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        rows: list[dict] = []
        for row in result:
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "company_id": str(row.company_id),
                    "role_archetype": row.role_archetype,
                    "brand_id": None,
                    "market_id": None,
                    "period": row.period,
                    "avg_days_open": float(row.avg_days_open)
                    if row.avg_days_open is not None
                    else None,
                    "median_days_open": float(row.median_days_open)
                    if row.median_days_open is not None
                    else None,
                    "repost_rate": float(row.repost_rate) if row.repost_rate is not None else None,
                    "avg_repost_gap_days": float(row.avg_repost_gap_days)
                    if row.avg_repost_gap_days is not None
                    else None,
                }
            )
        return rows
