from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.location_norm import _LOC_NORM_SQL

_QUERY = f"""
WITH latest_enrichment AS (
    SELECT DISTINCT ON (posting_id)
        posting_id,
        id AS enrichment_id
    FROM posting_enrichments
    ORDER BY posting_id, enriched_at DESC NULLS LAST
),
latest_snapshots AS (
    SELECT DISTINCT ON (posting_id)
        posting_id,
        location_raw
    FROM posting_snapshots
    ORDER BY posting_id, snapshot_date DESC
),
normalized_locations AS (
    SELECT
        ls.posting_id,
        LOWER(TRIM(INITCAP(TRIM(SPLIT_PART({_LOC_NORM_SQL}, ',', 1))))) AS city_normalized,
        UPPER(TRIM(SPLIT_PART(TRIM(SPLIT_PART({_LOC_NORM_SQL}, ',', 2)), ' ', 1))) AS state
    FROM latest_snapshots ls
    WHERE ls.location_raw IS NOT NULL
      AND ls.location_raw LIKE '%,%'
),
posting_markets AS (
    SELECT
        nl.posting_id,
        m.id AS market_id
    FROM normalized_locations nl
    JOIN location_mappings lm
        ON nl.city_normalized = LOWER(lm.city_normalized)
        AND nl.state = UPPER(lm.state)
    JOIN markets m
        ON LOWER(m.name) = LOWER(lm.metro_name)
        AND LOWER(COALESCE(m.state, '')) = LOWER(lm.metro_state)
)
SELECT
    p.company_id,
    pe.role_archetype,
    COALESCE(pe.market_id, pm.market_id) AS market_id,
    pe.brand_id,
    DATE_TRUNC('month', p.first_seen_at)::date AS period,
    AVG(pe.pay_min) AS avg_pay_min,
    AVG(pe.pay_max) AS avg_pay_max,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pe.pay_min) AS median_pay_min,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pe.pay_max) AS median_pay_max,
    COUNT(*) AS sample_size
FROM postings p
JOIN latest_enrichment le ON le.posting_id = p.id
JOIN posting_enrichments pe ON pe.id = le.enrichment_id
LEFT JOIN posting_markets pm ON pm.posting_id = p.id
WHERE pe.pay_min IS NOT NULL
  AND pe.pay_max IS NOT NULL
GROUP BY p.company_id, pe.role_archetype, COALESCE(pe.market_id, pm.market_id), pe.brand_id,
         DATE_TRUNC('month', p.first_seen_at)
HAVING COUNT(*) >= 3
ORDER BY p.company_id, pe.role_archetype, period
"""


class PayBenchmarksJob(AggregationJob):
    table_name = "agg_pay_benchmarks"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        rows: list[dict] = []
        for row in result:
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "company_id": str(row.company_id),
                    "role_archetype": row.role_archetype,
                    "market_id": str(row.market_id) if row.market_id is not None else None,
                    "brand_id": str(row.brand_id) if row.brand_id is not None else None,
                    "period": row.period,
                    "avg_pay_min": float(row.avg_pay_min) if row.avg_pay_min is not None else None,
                    "avg_pay_max": float(row.avg_pay_max) if row.avg_pay_max is not None else None,
                    "median_pay_min": float(row.median_pay_min)
                    if row.median_pay_min is not None
                    else None,
                    "median_pay_max": float(row.median_pay_max)
                    if row.median_pay_max is not None
                    else None,
                    "sample_size": row.sample_size,
                }
            )
        return rows
