from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH active_postings AS (
    SELECT
        p.id AS posting_id,
        p.company_id,
        pbm.resolved_brand_id AS brand_id,
        p.first_seen_at,
        p.times_reposted,
        EXTRACT(EPOCH FROM (NOW() - p.first_seen_at)) / 86400.0 AS days_active
    FROM postings p
    JOIN posting_brand_mentions pbm ON pbm.posting_id = p.id
    WHERE p.is_active = true
      AND pbm.resolved_brand_id IS NOT NULL
),
new_last_7d AS (
    SELECT
        p.company_id,
        pbm.resolved_brand_id AS brand_id,
        COUNT(*) AS cnt
    FROM postings p
    JOIN posting_brand_mentions pbm ON pbm.posting_id = p.id
    WHERE pbm.resolved_brand_id IS NOT NULL
      AND p.first_seen_at >= NOW() - INTERVAL '7 days'
    GROUP BY p.company_id, pbm.resolved_brand_id
),
new_prior_7d AS (
    SELECT
        p.company_id,
        pbm.resolved_brand_id AS brand_id,
        COUNT(*) AS cnt
    FROM postings p
    JOIN posting_brand_mentions pbm ON pbm.posting_id = p.id
    WHERE pbm.resolved_brand_id IS NOT NULL
      AND p.first_seen_at >= NOW() - INTERVAL '14 days'
      AND p.first_seen_at < NOW() - INTERVAL '7 days'
    GROUP BY p.company_id, pbm.resolved_brand_id
),
stats AS (
    SELECT
        ap.company_id,
        ap.brand_id,
        COUNT(*) AS active_posting_count,
        AVG(ap.days_active) AS avg_days_active,
        CASE
            WHEN COUNT(*) > 0
            THEN COUNT(*) FILTER (WHERE ap.times_reposted > 0)::FLOAT / COUNT(*)
            ELSE 0
        END AS repost_rate
    FROM active_postings ap
    GROUP BY ap.company_id, ap.brand_id
)
SELECT
    s.company_id,
    s.brand_id,
    s.active_posting_count,
    COALESCE(np.cnt, 0) AS prior_period_count,
    CASE
        WHEN COALESCE(np.cnt, 0) > 0
        THEN (COALESCE(nl.cnt, 0) - np.cnt)::FLOAT / np.cnt
        ELSE NULL
    END AS velocity_delta,
    s.avg_days_active,
    s.repost_rate,
    LEAST(1.0,
        0.4 * CASE
            WHEN COALESCE(np.cnt, 0) > 0
                 AND (COALESCE(nl.cnt, 0) - np.cnt)::FLOAT / np.cnt < 0
            THEN ABS((COALESCE(nl.cnt, 0) - np.cnt)::FLOAT / np.cnt)
            ELSE 0
        END
        + 0.3 * LEAST(1.0, COALESCE(s.avg_days_active, 0) / 90.0)
        + 0.3 * COALESCE(s.repost_rate, 0)
    ) AS churn_signal_score
FROM stats s
LEFT JOIN new_last_7d nl ON nl.company_id = s.company_id AND nl.brand_id = s.brand_id
LEFT JOIN new_prior_7d np ON np.company_id = s.company_id AND np.brand_id = s.brand_id
"""


class BrandChurnSignalsJob(AggregationJob):
    table_name = "agg_brand_churn_signals"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        today = datetime.now(UTC).date()
        rows: list[dict] = []
        for row in result.mappings().all():
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "company_id": str(row["company_id"]),
                    "brand_id": str(row["brand_id"]),
                    "period": today,
                    "active_posting_count": row["active_posting_count"],
                    "prior_period_count": row["prior_period_count"],
                    "velocity_delta": row["velocity_delta"],
                    "avg_days_active": row["avg_days_active"],
                    "repost_rate": row["repost_rate"],
                    "churn_signal_score": row["churn_signal_score"],
                }
            )
        return rows
