from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH latest_snapshots AS (
    SELECT DISTINCT ON (ps.posting_id)
        ps.posting_id,
        ps.location_raw
    FROM posting_snapshots ps
    ORDER BY ps.posting_id, ps.snapshot_date DESC
),
-- Normalize location_raw to match seed_location_mappings (normalize_location_raw logic)
-- Strip: ", US"/", CA" suffix, ZIP codes, company suffixes (e.g. "- 2020 Companies")
normalized_locations AS (
    SELECT
        ls.posting_id,
        ls.location_raw,
        LOWER(TRIM(INITCAP(TRIM(SPLIT_PART(
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(COALESCE(ls.location_raw, ''), ',\\s*(US|CA)\\s*$', '', 'i'),
                        '\\s+\\d{5}(-\\d{4})?', '', 'g'),
                    '\\s*[-\x2013\x2014]\\s*(2020 companies|bds connected solutions|'
                    'marketsource|t-roc|mosaic sales solutions|advantage solutions|acosta)'
                    '\\s*$', '', 'i'),
                '\\s+', ' ', 'g'),
            ',', 1)))) AS city_normalized,
        UPPER(TRIM(SPLIT_PART(TRIM(SPLIT_PART(
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(COALESCE(ls.location_raw, ''), ',\\s*(US|CA)\\s*$', '', 'i'),
                        '\\s+\\d{5}(-\\d{4})?', '', 'g'),
                    '\\s*[-\x2013\x2014]\\s*(2020 companies|bds connected solutions|'
                    'marketsource|t-roc|mosaic sales solutions|advantage solutions|acosta)'
                    '\\s*$', '', 'i'),
                '\\s+', ' ', 'g'),
            ',', 2)), ' ', 1))) AS state
    FROM latest_snapshots ls
    WHERE ls.location_raw IS NOT NULL
      AND ls.location_raw LIKE '%,%'
),
posting_markets AS (
    SELECT
        p.id AS posting_id,
        p.company_id,
        m.id AS market_id
    FROM postings p
    JOIN normalized_locations nl ON nl.posting_id = p.id
    JOIN location_mappings lm
        ON nl.city_normalized = LOWER(lm.city_normalized)
        AND nl.state = lm.state
    JOIN markets m
        ON LOWER(m.name) = LOWER(lm.metro_name)
        AND LOWER(COALESCE(m.state, '')) = LOWER(lm.metro_state)
    WHERE p.is_active = true
),
posting_brands AS (
    SELECT
        pm.company_id,
        pm.market_id,
        pm.posting_id,
        b.name AS brand_name
    FROM posting_markets pm
    LEFT JOIN posting_brand_mentions pbm ON pbm.posting_id = pm.posting_id
    LEFT JOIN brands b ON b.id = pbm.resolved_brand_id
)
SELECT
    pb.company_id,
    pb.market_id,
    COUNT(DISTINCT pb.posting_id) AS total_active_postings,
    COUNT(DISTINCT pb.brand_name) FILTER (WHERE pb.brand_name IS NOT NULL) AS brand_count,
    ARRAY_AGG(DISTINCT pb.brand_name ORDER BY pb.brand_name)
        FILTER (WHERE pb.brand_name IS NOT NULL) AS brand_names
FROM posting_brands pb
GROUP BY pb.company_id, pb.market_id
"""


class MarketCoverageGapsJob(AggregationJob):
    table_name = "agg_market_coverage_gaps"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        today = date.today()
        rows: list[dict] = []
        for row in result.mappings().all():
            brand_names = row["brand_names"]
            if brand_names is not None:
                brand_names = list(brand_names)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "company_id": str(row["company_id"]),
                    "market_id": str(row["market_id"]),
                    "period": today.isoformat(),
                    "total_active_postings": row["total_active_postings"],
                    "brand_count": row["brand_count"],
                    "brand_names": brand_names,
                }
            )
        return rows
