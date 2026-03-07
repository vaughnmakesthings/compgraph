from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.helpers import new_row_id

_QUERY = """
SELECT
    p.company_id,
    pbm.resolved_brand_id AS brand_id,
    MIN(p.first_seen_at) AS first_seen_at,
    MAX(COALESCE(p.last_seen_at, p.first_seen_at)) AS last_seen_at,
    BOOL_OR(p.is_active) AS is_currently_active,
    COUNT(DISTINCT p.id) AS total_postings_all_time,
    COUNT(DISTINCT p.id) FILTER (WHERE p.is_active = true) AS current_active_postings
FROM posting_brand_mentions pbm
JOIN postings p ON p.id = pbm.posting_id
WHERE pbm.resolved_brand_id IS NOT NULL
GROUP BY p.company_id, pbm.resolved_brand_id
ORDER BY p.company_id, pbm.resolved_brand_id
"""


class BrandTimelineJob(AggregationJob):
    table_name = "agg_brand_timeline"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": new_row_id(),
                "company_id": str(row["company_id"]),
                "brand_id": str(row["brand_id"]),
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "is_currently_active": row["is_currently_active"],
                "total_postings_all_time": row["total_postings_all_time"],
                "current_active_postings": row["current_active_postings"],
                "peak_active_postings": row["current_active_postings"],
                "peak_date": None,
            }
            for row in result.mappings().all()
        ]
