"""Service layer for posting queries — extracted from api/routes/postings.py."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import (
    Brand,
    Company,
    Posting,
    PostingBrandMention,
    PostingEnrichment,
    PostingSnapshot,
)

if TYPE_CHECKING:
    from sqlalchemy import Subquery

SORT_BY_ALLOWED = frozenset(
    {"first_seen_desc", "first_seen_asc", "pay_desc", "pay_asc", "title_asc"}
)


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _latest_snapshot_subquery() -> Subquery:
    return (
        select(PostingSnapshot)
        .distinct(PostingSnapshot.posting_id)
        .order_by(PostingSnapshot.posting_id, PostingSnapshot.snapshot_date.desc())
        .subquery()
    )


def _build_filters(
    company_id: uuid.UUID | None,
    is_active: bool | None,
    role_archetype: str | None,
    search: str | None,
    snapshot_subq: Any = None,
) -> tuple[list, bool]:
    filters: list = []
    if company_id is not None:
        filters.append(Posting.company_id == company_id)
    if is_active is not None:
        filters.append(Posting.is_active == is_active)
    if role_archetype is not None:
        filters.append(PostingEnrichment.role_archetype == role_archetype)
    search_trimmed = search.strip() if search else ""
    needs_snapshot = bool(search_trimmed)
    if needs_snapshot:
        escaped = _escape_like(search_trimmed)
        title_col = (
            snapshot_subq.c.title_raw if snapshot_subq is not None else PostingSnapshot.title_raw
        )
        filters.append(title_col.ilike(f"%{escaped}%", escape="\\"))
    return filters, needs_snapshot


def _order_by_clause(sort_by: str, snapshot_subq: Any) -> Any:
    from sqlalchemy.sql import nulls_last

    mapping = {
        "first_seen_desc": Posting.first_seen_at.desc(),
        "first_seen_asc": Posting.first_seen_at.asc(),
        "pay_desc": nulls_last(PostingEnrichment.pay_max.desc()),
        "pay_asc": nulls_last(PostingEnrichment.pay_max.asc()),
        "title_asc": nulls_last(snapshot_subq.c.title_raw.asc()),
    }
    return mapping.get(sort_by, Posting.first_seen_at.desc())


class PostingService:
    @staticmethod
    async def list_postings(
        db: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0,
        company_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        role_archetype: str | None = None,
        sort_by: str = "first_seen_desc",
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        latest_snap = _latest_snapshot_subquery()
        filters, needs_snapshot = _build_filters(
            company_id, is_active, role_archetype, search, snapshot_subq=latest_snap
        )

        # Count query
        count_base = select(Posting).outerjoin(
            PostingEnrichment, PostingEnrichment.posting_id == Posting.id
        )
        if needs_snapshot:
            count_base = count_base.outerjoin(latest_snap, latest_snap.c.posting_id == Posting.id)
        count_subq = count_base.where(*filters).subquery()
        count_result = await db.execute(select(func.count()).select_from(count_subq))
        total = count_result.scalar_one()

        # Data query
        rows_result = await db.execute(
            select(
                Posting,
                PostingEnrichment.role_archetype,
                PostingEnrichment.pay_min,
                PostingEnrichment.pay_max,
                PostingEnrichment.pay_currency,
                PostingEnrichment.employment_type,
                latest_snap.c.title_raw,
                latest_snap.c.location_raw,
                Company.name.label("company_name"),
                Company.slug.label("company_slug"),
            )
            .outerjoin(PostingEnrichment, PostingEnrichment.posting_id == Posting.id)
            .outerjoin(Company, Company.id == Posting.company_id)
            .outerjoin(latest_snap, latest_snap.c.posting_id == Posting.id)
            .where(*filters)
            .order_by(_order_by_clause(sort_by, latest_snap))
            .limit(limit)
            .offset(offset)
        )
        rows = rows_result.all()

        items = [
            {
                "id": row[0].id,
                "company_id": row[0].company_id,
                "company_name": row[8],
                "company_slug": row[9],
                "title": row[6],
                "location": row[7],
                "first_seen_at": row[0].first_seen_at,
                "last_seen_at": row[0].last_seen_at,
                "is_active": row[0].is_active,
                "role_archetype": row[1],
                "pay_min": row[2],
                "pay_max": row[3],
                "pay_currency": row[4],
                "employment_type": row[5],
            }
            for row in rows
        ]
        return items, total

    @staticmethod
    async def get_posting(
        db: AsyncSession,
        posting_id: uuid.UUID,
    ) -> dict | None:
        posting_result = await db.execute(select(Posting).where(Posting.id == posting_id))
        posting = posting_result.scalar_one_or_none()
        if posting is None:
            return None

        enrichment_result = await db.execute(
            select(PostingEnrichment)
            .where(PostingEnrichment.posting_id == posting_id)
            .order_by(PostingEnrichment.enriched_at.desc())
            .limit(1)
        )
        enrichment = enrichment_result.scalar_one_or_none()

        snapshot_result = await db.execute(
            select(PostingSnapshot)
            .where(PostingSnapshot.posting_id == posting_id)
            .order_by(PostingSnapshot.snapshot_date.desc())
            .limit(1)
        )
        latest_snapshot = snapshot_result.scalar_one_or_none()

        mentions_result = await db.execute(
            select(PostingBrandMention, Brand.id, Brand.name)
            .outerjoin(Brand, Brand.id == PostingBrandMention.resolved_brand_id)
            .where(PostingBrandMention.posting_id == posting_id)
            .order_by(PostingBrandMention.entity_name)
        )
        mention_rows = mentions_result.all()

        enrichment_dict: dict | None = None
        if enrichment is not None:
            enrichment_dict = {
                "id": enrichment.id,
                "title_normalized": enrichment.title_normalized,
                "role_archetype": enrichment.role_archetype,
                "role_level": enrichment.role_level,
                "pay_type": enrichment.pay_type,
                "pay_min": enrichment.pay_min,
                "pay_max": enrichment.pay_max,
                "pay_currency": enrichment.pay_currency,
                "pay_frequency": enrichment.pay_frequency,
                "employment_type": enrichment.employment_type,
                "commission_mentioned": enrichment.commission_mentioned,
                "benefits_mentioned": enrichment.benefits_mentioned,
                "enrichment_version": enrichment.enrichment_version,
                "enriched_at": enrichment.enriched_at,
            }

        brand_mentions = [
            {
                "id": mention.id,
                "brand_id": brand_id,
                "brand_name": brand_name,
                "entity_name": mention.entity_name,
                "entity_type": mention.entity_type,
                "confidence_score": mention.confidence_score,
            }
            for mention, brand_id, brand_name in mention_rows
        ]

        return {
            "id": posting.id,
            "company_id": posting.company_id,
            "external_job_id": posting.external_job_id,
            "title": latest_snapshot.title_raw if latest_snapshot else None,
            "location": latest_snapshot.location_raw if latest_snapshot else None,
            "url": latest_snapshot.url if latest_snapshot else None,
            "first_seen_at": posting.first_seen_at,
            "last_seen_at": posting.last_seen_at,
            "is_active": posting.is_active,
            "times_reposted": posting.times_reposted,
            "enrichment": enrichment_dict,
            "brand_mentions": brand_mentions,
        }
