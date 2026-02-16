"""Database queries for the enrichment pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Posting, PostingEnrichment, PostingSnapshot
from compgraph.enrichment.schemas import Pass1Result


async def fetch_unenriched_postings(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
    batch_size: int = 50,
) -> list[tuple[Posting, PostingSnapshot]]:
    """Fetch postings that have no enrichment record yet.

    Returns postings paired with their latest snapshot (source of full_text_raw).
    Ordered by first_seen_at ASC so oldest postings are processed first.
    """
    # Subquery: latest snapshot per posting (most recent created_at)
    latest_snapshot = (
        select(
            PostingSnapshot.posting_id,
            PostingSnapshot.id.label("snapshot_id"),
        )
        .distinct(PostingSnapshot.posting_id)
        .order_by(PostingSnapshot.posting_id, PostingSnapshot.created_at.desc())
        .subquery()
    )

    # Main query: postings with no enrichment
    stmt = (
        select(Posting, PostingSnapshot)
        .join(
            latest_snapshot,
            Posting.id == latest_snapshot.c.posting_id,
        )
        .join(
            PostingSnapshot,
            PostingSnapshot.id == latest_snapshot.c.snapshot_id,
        )
        .outerjoin(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
        .where(PostingEnrichment.id.is_(None))
        .where(Posting.is_active.is_(True))
        .order_by(Posting.first_seen_at.asc())
        .limit(batch_size)
    )

    if company_id is not None:
        stmt = stmt.where(Posting.company_id == company_id)

    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def save_enrichment(
    session: AsyncSession,
    posting_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    result: Pass1Result,
    model: str,
    version: str,
) -> PostingEnrichment:
    """Create a new PostingEnrichment row (append-only, never update).

    Maps Pass1Result fields to PostingEnrichment columns.
    """
    enrichment = PostingEnrichment(
        posting_id=posting_id,
        # Classification
        role_archetype=result.role_archetype,
        role_level=result.role_level,
        employment_type=result.employment_type,
        travel_required=result.travel_required,
        # Compensation
        pay_type=result.pay_type,
        pay_min=result.pay_min,
        pay_max=result.pay_max,
        pay_frequency=result.pay_frequency,
        commission_mentioned=result.has_commission,
        benefits_mentioned=result.has_benefits,
        # Content sections
        content_role_specific=result.content_role_specific,
        content_boilerplate=result.content_boilerplate,
        content_qualifications=result.content_qualifications,
        content_responsibilities=result.content_responsibilities,
        # Metadata
        tools_mentioned=result.tools_mentioned or [],
        kpis_mentioned=result.kpis_mentioned or [],
        store_count_mentioned=result.store_count,
        # Tracking
        enrichment_model=model,
        enrichment_version=version,
        enriched_at=datetime.now(UTC),
    )
    session.add(enrichment)
    await session.flush()
    return enrichment


async def fetch_pass1_complete_postings(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
    batch_size: int = 50,
) -> list[tuple[Posting, PostingSnapshot, PostingEnrichment]]:
    """Fetch postings with Pass 1 enrichment but no Pass 2.

    Returns postings paired with their latest snapshot and enrichment record.
    Filters to enrichments that have Pass 1 done but Pass 2 not yet run.
    Uses enrichment_version to track completion (avoids infinite loop when
    Pass 2 extracts zero entities).
    """
    # Subquery: latest snapshot per posting
    latest_snapshot = (
        select(
            PostingSnapshot.posting_id,
            PostingSnapshot.id.label("snapshot_id"),
        )
        .distinct(PostingSnapshot.posting_id)
        .order_by(PostingSnapshot.posting_id, PostingSnapshot.created_at.desc())
        .subquery()
    )

    # Main query: postings with enrichment but Pass 2 not yet run
    stmt = (
        select(Posting, PostingSnapshot, PostingEnrichment)
        .join(
            latest_snapshot,
            Posting.id == latest_snapshot.c.posting_id,
        )
        .join(
            PostingSnapshot,
            PostingSnapshot.id == latest_snapshot.c.snapshot_id,
        )
        .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
        .where(
            PostingEnrichment.enrichment_version.not_like("%pass2%"),
        )
        .where(Posting.is_active.is_(True))
        .order_by(Posting.first_seen_at.asc())
        .limit(batch_size)
    )

    if company_id is not None:
        stmt = stmt.where(Posting.company_id == company_id)

    result = await session.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]
