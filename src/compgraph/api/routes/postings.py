from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import (
    Brand,
    Posting,
    PostingBrandMention,
    PostingEnrichment,
    PostingSnapshot,
)

router = APIRouter()


class PostingListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str | None
    location: str | None
    first_seen_at: datetime
    last_seen_at: datetime | None
    is_active: bool
    role_archetype: str | None
    pay_min: float | None
    pay_max: float | None
    employment_type: str | None


class PostingListResponse(BaseModel):
    items: list[PostingListItem]
    total: int


class EnrichmentDetail(BaseModel):
    id: uuid.UUID
    title_normalized: str | None
    role_archetype: str | None
    role_level: str | None
    pay_type: str | None
    pay_min: float | None
    pay_max: float | None
    pay_currency: str | None
    pay_frequency: str | None
    employment_type: str | None
    commission_mentioned: bool | None
    benefits_mentioned: bool | None
    enrichment_version: str | None
    enriched_at: datetime | None


class BrandMentionDetail(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID | None
    brand_name: str | None
    entity_name: str
    entity_type: str
    confidence_score: float | None


class PostingDetailResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    external_job_id: str | None
    title: str | None
    location: str | None
    url: str | None
    first_seen_at: datetime
    last_seen_at: datetime | None
    is_active: bool
    times_reposted: int
    enrichment: EnrichmentDetail | None
    brand_mentions: list[BrandMentionDetail]


def _build_filters(
    company_id: uuid.UUID | None,
    is_active: bool | None,
    role_archetype: str | None,
) -> list:
    filters = []
    if company_id is not None:
        filters.append(Posting.company_id == company_id)  # already a uuid.UUID
    if is_active is not None:
        filters.append(Posting.is_active == is_active)
    if role_archetype is not None:
        filters.append(PostingEnrichment.role_archetype == role_archetype)
    return filters


@router.get("", response_model=PostingListResponse)
async def list_postings(
    limit: int = 50,
    offset: int = 0,
    company_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    role_archetype: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PostingListResponse:
    filters = _build_filters(company_id, is_active, role_archetype)

    count_subq = (
        select(Posting)
        .outerjoin(PostingEnrichment, PostingEnrichment.posting_id == Posting.id)
        .where(*filters)
        .subquery()
    )
    count_result = await db.execute(select(func.count()).select_from(count_subq))
    total = count_result.scalar_one()

    rows_result = await db.execute(
        select(
            Posting,
            PostingEnrichment.role_archetype,
            PostingEnrichment.pay_min,
            PostingEnrichment.pay_max,
            PostingEnrichment.employment_type,
            PostingSnapshot.title_raw,
            PostingSnapshot.location_raw,
        )
        .outerjoin(PostingEnrichment, PostingEnrichment.posting_id == Posting.id)
        .outerjoin(
            PostingSnapshot,
            (PostingSnapshot.posting_id == Posting.id)
            & (
                PostingSnapshot.snapshot_date
                == select(func.max(PostingSnapshot.snapshot_date))
                .where(PostingSnapshot.posting_id == Posting.id)
                .correlate(Posting)
                .scalar_subquery()
            ),
        )
        .where(*filters)
        .order_by(Posting.first_seen_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = rows_result.all()

    items: list[PostingListItem] = [
        PostingListItem(
            id=row[0].id,
            company_id=row[0].company_id,
            title=row[5],
            location=row[6],
            first_seen_at=row[0].first_seen_at,
            last_seen_at=row[0].last_seen_at,
            is_active=row[0].is_active,
            role_archetype=row[1],
            pay_min=row[2],
            pay_max=row[3],
            employment_type=row[4],
        )
        for row in rows
    ]

    return PostingListResponse(items=items, total=total)


@router.get("/{posting_id}", response_model=PostingDetailResponse)
async def get_posting(
    posting_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PostingDetailResponse:
    try:
        pid = uuid.UUID(posting_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Posting not found") from exc

    posting_result = await db.execute(select(Posting).where(Posting.id == pid))
    posting = posting_result.scalar_one_or_none()

    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    enrichment_result = await db.execute(
        select(PostingEnrichment)
        .where(PostingEnrichment.posting_id == pid)
        .order_by(PostingEnrichment.enriched_at.desc())
        .limit(1)
    )
    enrichment = enrichment_result.scalar_one_or_none()

    snapshot_result = await db.execute(
        select(PostingSnapshot)
        .where(PostingSnapshot.posting_id == pid)
        .order_by(PostingSnapshot.snapshot_date.desc())
        .limit(1)
    )
    latest_snapshot = snapshot_result.scalar_one_or_none()

    mentions_result = await db.execute(
        select(PostingBrandMention, Brand.id, Brand.name)
        .outerjoin(Brand, Brand.id == PostingBrandMention.resolved_brand_id)
        .where(PostingBrandMention.posting_id == pid)
        .order_by(PostingBrandMention.entity_name)
    )
    mention_rows = mentions_result.all()

    enrichment_detail: EnrichmentDetail | None = None
    if enrichment is not None:
        enrichment_detail = EnrichmentDetail(
            id=enrichment.id,
            title_normalized=enrichment.title_normalized,
            role_archetype=enrichment.role_archetype,
            role_level=enrichment.role_level,
            pay_type=enrichment.pay_type,
            pay_min=enrichment.pay_min,
            pay_max=enrichment.pay_max,
            pay_currency=enrichment.pay_currency,
            pay_frequency=enrichment.pay_frequency,
            employment_type=enrichment.employment_type,
            commission_mentioned=enrichment.commission_mentioned,
            benefits_mentioned=enrichment.benefits_mentioned,
            enrichment_version=enrichment.enrichment_version,
            enriched_at=enrichment.enriched_at,
        )

    brand_mentions: list[BrandMentionDetail] = [
        BrandMentionDetail(
            id=mention.id,
            brand_id=brand_id,
            brand_name=brand_name,
            entity_name=mention.entity_name,
            entity_type=mention.entity_type,
            confidence_score=mention.confidence_score,
        )
        for mention, brand_id, brand_name in mention_rows
    ]

    return PostingDetailResponse(
        id=posting.id,
        company_id=posting.company_id,
        external_job_id=posting.external_job_id,
        title=latest_snapshot.title_raw if latest_snapshot else None,
        location=latest_snapshot.location_raw if latest_snapshot else None,
        url=latest_snapshot.url if latest_snapshot else None,
        first_seen_at=posting.first_seen_at,
        last_seen_at=posting.last_seen_at,
        is_active=posting.is_active,
        times_reposted=posting.times_reposted,
        enrichment=enrichment_detail,
        brand_mentions=brand_mentions,
    )
