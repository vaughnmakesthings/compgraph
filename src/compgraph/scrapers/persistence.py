"""Shared posting persistence logic for all scraper adapters.

All adapters use this single function to upsert postings and append snapshots.
The posting row is upserted on (company_id, external_job_id); the snapshot row
is appended once per posting per calendar day (append-only -- never updated or
deleted).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Posting, PostingSnapshot
from compgraph.scrapers.base import RawPosting

logger = logging.getLogger(__name__)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def persist_posting(
    session: AsyncSession,
    company_id: uuid.UUID,
    raw: RawPosting,
    first_seen_at: datetime | None = None,
) -> bool:
    """Upsert a posting and append a snapshot for today.

    Args:
        session: Async SQLAlchemy session (caller owns transaction boundaries).
        company_id: UUID of the owning company.
        raw: Scraped posting data -- must have all fields populated including url.
        first_seen_at: Optional override for first_seen_at (e.g. from Workday
            startDate). Defaults to now on first insert.

    Returns:
        True if a new snapshot row was inserted, False if today's snapshot
        already existed (idempotent on repeated calls within the same day).
    """
    now = datetime.now(UTC)
    fingerprint = _hash_text(raw.full_text) if raw.full_text else None

    posting_stmt = (
        pg_insert(Posting)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            external_job_id=raw.external_job_id,
            fingerprint_hash=fingerprint,
            first_seen_at=first_seen_at or now,
            last_seen_at=now,
            is_active=True,
            times_reposted=0,
        )
        .on_conflict_do_update(
            index_elements=["company_id", "external_job_id"],
            set_={
                "last_seen_at": now,
                "is_active": True,
            },
        )
        .returning(Posting.id)
    )
    result = await session.execute(posting_stmt)
    posting_id = result.scalar_one()

    if raw.location:
        await _maybe_geocode_posting(session, posting_id, raw.location)

    today = now.date()

    # Early-return if we already wrote today's snapshot (idempotent within a day)
    existing = await session.execute(
        select(PostingSnapshot.id).where(
            PostingSnapshot.posting_id == posting_id,
            PostingSnapshot.snapshot_date == today,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    text_hash = _hash_text(raw.full_text) if raw.full_text else None
    prev_snapshot = await session.execute(
        select(PostingSnapshot.full_text_hash)
        .where(PostingSnapshot.posting_id == posting_id)
        .order_by(PostingSnapshot.snapshot_date.desc())
        .limit(1)
    )
    prev_hash = prev_snapshot.scalar_one_or_none()
    content_changed = prev_hash is not None and prev_hash != text_hash

    snapshot_stmt = (
        pg_insert(PostingSnapshot)
        .values(
            id=uuid.uuid4(),
            posting_id=posting_id,
            snapshot_date=today,
            title_raw=raw.title,
            location_raw=raw.location,
            url=raw.url,
            full_text_raw=raw.full_text,
            full_text_hash=text_hash,
            content_changed=content_changed,
        )
        .on_conflict_do_nothing(constraint="uq_snapshots_posting_date")
    )
    snapshot_result = await session.execute(snapshot_stmt)
    return snapshot_result.rowcount > 0  # type: ignore[no-any-return, attr-defined]


async def _maybe_geocode_posting(
    session: AsyncSession,
    posting_id: uuid.UUID,
    location_str: str,
) -> None:
    posting_row = await session.execute(select(Posting.latitude).where(Posting.id == posting_id))
    if posting_row.scalar_one_or_none() is not None:
        return

    try:
        from compgraph.geocoding import compute_h3_index, geocode_location

        coords = await geocode_location(location_str)
        if coords:
            from sqlalchemy import update

            await session.execute(
                update(Posting)
                .where(Posting.id == posting_id)
                .values(
                    latitude=coords[0],
                    longitude=coords[1],
                    h3_index=compute_h3_index(coords[0], coords[1]),
                )
            )
    except Exception:
        logger.warning("Geocoding failed for posting %s", posting_id, exc_info=True)
