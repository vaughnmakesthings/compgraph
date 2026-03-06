from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH brand_company_counts AS (
    SELECT
        pbm.resolved_brand_id AS brand_id,
        p.company_id,
        c.name AS company_name,
        COUNT(*) AS posting_count
    FROM posting_brand_mentions pbm
    JOIN postings p ON p.id = pbm.posting_id
    JOIN companies c ON c.id = p.company_id
    WHERE p.is_active = true
      AND pbm.resolved_brand_id IS NOT NULL
    GROUP BY pbm.resolved_brand_id, p.company_id, c.name
),
brand_totals AS (
    SELECT
        brand_id,
        SUM(posting_count) AS total_postings,
        COUNT(DISTINCT company_id) AS agency_count,
        ARRAY_AGG(DISTINCT company_name ORDER BY company_name) AS agency_names
    FROM brand_company_counts
    GROUP BY brand_id
),
primary_agency AS (
    SELECT DISTINCT ON (brand_id)
        brand_id,
        company_id AS primary_company_id,
        posting_count AS primary_count
    FROM brand_company_counts
    ORDER BY brand_id, posting_count DESC
)
SELECT
    bt.brand_id,
    bt.agency_count,
    bt.agency_names,
    pa.primary_company_id,
    CASE
        WHEN bt.total_postings > 0
        THEN pa.primary_count::FLOAT / bt.total_postings
        ELSE NULL
    END AS primary_share,
    bt.agency_count = 1 AS is_exclusive,
    bt.agency_count >= 2
        AND CASE
            WHEN bt.total_postings > 0
            THEN pa.primary_count::FLOAT / bt.total_postings
            ELSE 1
        END <= 0.6 AS is_contested,
    bt.total_postings
FROM brand_totals bt
JOIN primary_agency pa ON pa.brand_id = bt.brand_id
"""


class BrandAgencyOverlapJob(AggregationJob):
    table_name = "agg_brand_agency_overlap"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        today = datetime.now(UTC).date()
        rows: list[dict] = []
        for row in result.mappings().all():
            agency_names = row["agency_names"]
            if agency_names is not None:
                agency_names = list(agency_names)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "brand_id": str(row["brand_id"]),
                    "period": today,
                    "agency_count": row["agency_count"],
                    "agency_names": agency_names,
                    "primary_company_id": str(row["primary_company_id"])
                    if row["primary_company_id"]
                    else None,
                    "primary_share": row["primary_share"],
                    "is_exclusive": row["is_exclusive"],
                    "is_contested": row["is_contested"],
                    "total_postings": row["total_postings"],
                }
            )
        return rows
