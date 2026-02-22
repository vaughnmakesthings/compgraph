from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """
SELECT
    p.company_id,
    pe.role_archetype,
    pe.market_id,
    pe.brand_id,
    DATE_TRUNC('month', p.first_seen_at)::date AS period,
    AVG(pe.pay_min) AS avg_pay_min,
    AVG(pe.pay_max) AS avg_pay_max,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pe.pay_min) AS median_pay_min,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pe.pay_max) AS median_pay_max,
    COUNT(*) AS sample_size
FROM postings p
JOIN posting_enrichments pe ON pe.posting_id = p.id
WHERE pe.pay_min IS NOT NULL
  AND pe.pay_max IS NOT NULL
GROUP BY p.company_id, pe.role_archetype, pe.market_id, pe.brand_id,
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
