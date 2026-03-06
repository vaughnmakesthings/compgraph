"""Alert generation — append-only alert detection after aggregation.

MVP alert types:
1. velocity_spike — >30% increase in active postings vs 30-day avg
2. new_brand — first-time brand appears in a company's postings
3. brand_lost — brand had 30+ day history but zero current active postings
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Alert
from compgraph.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def generate_alerts() -> dict[str, int]:
    """Run all alert detectors and return counts by type."""
    counts: dict[str, int] = {}
    async with async_session_factory() as session:
        counts["velocity_spike"] = await _detect_velocity_spikes(session)
        counts["new_brand"] = await _detect_new_brands(session)
        counts["brand_lost"] = await _detect_brand_lost(session)
        await session.commit()
    logger.info("Alert generation complete: %s", counts)
    return counts


async def _insert_alerts(session: AsyncSession, alerts: list[dict]) -> int:
    """Insert alerts with ON CONFLICT DO NOTHING for dedup safety.

    The uq_alert_dedup unique index ensures one alert per
    (type, company, brand, day). Reruns silently skip duplicates.
    """
    if not alerts:
        return 0
    stmt = (
        pg_insert(Alert)
        .values(alerts)
        .on_conflict_do_nothing(  # type: ignore[arg-type]
            index_elements=["alert_type", "company_id", "brand_id", text("(triggered_at::date)")],
        )
    )
    result = await session.execute(stmt)
    return result.rowcount  # type: ignore[attr-defined,no-any-return]


async def _detect_velocity_spikes(session: AsyncSession) -> int:
    """Detect >30% increase in active postings vs trailing 30-day average."""
    sql = text("""
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM agg_daily_velocity
            WHERE brand_id IS NULL
        ),
        latest AS (
            SELECT company_id, active_postings, date
            FROM agg_daily_velocity
            WHERE brand_id IS NULL AND market_id IS NULL
              AND date = (SELECT max_date FROM latest_date)
        ),
        trailing AS (
            SELECT company_id, AVG(active_postings) AS avg_active
            FROM agg_daily_velocity
            WHERE brand_id IS NULL AND market_id IS NULL
              AND date >= (SELECT max_date FROM latest_date) - 30
              AND date < (SELECT max_date FROM latest_date)
            GROUP BY company_id
        )
        SELECT l.company_id, l.active_postings, t.avg_active
        FROM latest l
        JOIN trailing t ON l.company_id = t.company_id
        WHERE t.avg_active > 0
          AND l.active_postings > t.avg_active * 1.3
    """)
    result = await session.execute(sql)
    rows = result.all()
    now = datetime.now(UTC)
    alerts = [
        {
            "id": uuid.uuid4(),
            "alert_type": "velocity_spike",
            "company_id": row.company_id,
            "brand_id": None,
            "triggered_at": now,
            "metadata_json": {
                "active_postings": row.active_postings,
                "avg_30d": round(float(row.avg_active), 1),
                "pct_increase": round(
                    (row.active_postings - float(row.avg_active)) / float(row.avg_active) * 100,
                    1,
                ),
            },
        }
        for row in rows
    ]
    return await _insert_alerts(session, alerts)


async def _detect_new_brands(session: AsyncSession) -> int:
    """Detect brands appearing for the first time at a company (first_seen within last 7 days)."""
    sql = text("""
        SELECT company_id, brand_id, first_seen_at
        FROM agg_brand_timeline
        WHERE first_seen_at >= NOW() - INTERVAL '7 days'
          AND total_postings_all_time <= 3
    """)
    result = await session.execute(sql)
    rows = result.all()
    now = datetime.now(UTC)
    alerts = [
        {
            "id": uuid.uuid4(),
            "alert_type": "new_brand",
            "company_id": row.company_id,
            "brand_id": row.brand_id,
            "triggered_at": now,
            "metadata_json": {
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            },
        }
        for row in rows
    ]
    return await _insert_alerts(session, alerts)


async def _detect_brand_lost(session: AsyncSession) -> int:
    """Detect brands that had 30+ day presence but now have zero active postings."""
    sql = text("""
        SELECT company_id, brand_id, first_seen_at, last_seen_at,
               total_postings_all_time, peak_active_postings
        FROM agg_brand_timeline
        WHERE is_currently_active = false
          AND total_postings_all_time >= 5
          AND last_seen_at >= NOW() - INTERVAL '60 days'
          AND last_seen_at <= NOW() - INTERVAL '14 days'
          AND first_seen_at <= last_seen_at - INTERVAL '30 days'
    """)
    result = await session.execute(sql)
    rows = result.all()
    now = datetime.now(UTC)
    alerts = [
        {
            "id": uuid.uuid4(),
            "alert_type": "brand_lost",
            "company_id": row.company_id,
            "brand_id": row.brand_id,
            "triggered_at": now,
            "metadata_json": {
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "total_postings": row.total_postings_all_time,
                "peak_active": row.peak_active_postings,
            },
        }
        for row in rows
    ]
    return await _insert_alerts(session, alerts)
