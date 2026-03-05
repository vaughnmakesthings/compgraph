from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.services.posting_service import SORT_BY_ALLOWED, PostingService

router = APIRouter()


class PostingListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str | None
    company_slug: str | None
    title: str | None
    location: str | None
    first_seen_at: datetime
    last_seen_at: datetime | None
    is_active: bool
    role_archetype: str | None
    pay_min: float | None
    pay_max: float | None
    pay_currency: str | None
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


@router.get("", response_model=PostingListResponse)
async def list_postings(
    limit: int = 50,
    offset: int = 0,
    company_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    role_archetype: str | None = None,
    sort_by: str = "first_seen_desc",
    search: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PostingListResponse:
    if sort_by not in SORT_BY_ALLOWED:
        raise HTTPException(
            status_code=422,
            detail=f"sort_by must be one of: {sorted(SORT_BY_ALLOWED)}",
        )

    items, total = await PostingService.list_postings(
        db,
        limit=limit,
        offset=offset,
        company_id=company_id,
        is_active=is_active,
        role_archetype=role_archetype,
        sort_by=sort_by,
        search=search,
    )

    return PostingListResponse(
        items=[PostingListItem(**item) for item in items],
        total=total,
    )


@router.get("/{posting_id}", response_model=PostingDetailResponse)
async def get_posting(
    posting_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PostingDetailResponse:
    try:
        pid = uuid.UUID(posting_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Posting not found") from exc

    data = await PostingService.get_posting(db, pid)
    if data is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    enrichment_detail: EnrichmentDetail | None = None
    if data["enrichment"] is not None:
        enrichment_detail = EnrichmentDetail(**data["enrichment"])

    brand_mentions = [BrandMentionDetail(**m) for m in data["brand_mentions"]]

    return PostingDetailResponse(
        id=data["id"],
        company_id=data["company_id"],
        external_job_id=data["external_job_id"],
        title=data["title"],
        location=data["location"],
        url=data["url"],
        first_seen_at=data["first_seen_at"],
        last_seen_at=data["last_seen_at"],
        is_active=data["is_active"],
        times_reposted=data["times_reposted"],
        enrichment=enrichment_detail,
        brand_mentions=brand_mentions,
    )
