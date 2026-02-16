"""Dashboard query functions (sync, read-only).

All functions take a sync Session and return lists of dicts for easy DataFrame conversion.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compgraph.db.models import (
    Company,
    Posting,
    PostingBrandMention,
    PostingEnrichment,
    PostingSnapshot,
    ScrapeRun,
)


def _latest_snapshot_subquery():
    """Latest snapshot per posting (most recent created_at)."""
    return (
        select(
            PostingSnapshot.posting_id,
            PostingSnapshot.id.label("snapshot_id"),
        )
        .distinct(PostingSnapshot.posting_id)
        .order_by(PostingSnapshot.posting_id, PostingSnapshot.created_at.desc())
        .subquery()
    )


# ---------------------------------------------------------------------------
# Pipeline Health
# ---------------------------------------------------------------------------


def get_recent_scrape_runs(session: Session, limit: int = 20) -> list[dict]:
    """Recent scrape runs with company name."""
    stmt = (
        select(ScrapeRun, Company.name.label("company_name"))
        .join(Company, ScrapeRun.company_id == Company.id)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    return [
        {
            "company": row.company_name,
            "started_at": row.ScrapeRun.started_at,
            "completed_at": row.ScrapeRun.completed_at or "In Progress",
            "status": row.ScrapeRun.status,
            "pages_scraped": row.ScrapeRun.pages_scraped,
            "jobs_found": row.ScrapeRun.jobs_found,
            "snapshots_created": row.ScrapeRun.snapshots_created,
            "postings_closed": row.ScrapeRun.postings_closed,
            "has_errors": row.ScrapeRun.errors is not None,
        }
        for row in rows
    ]


def get_enrichment_coverage(session: Session) -> dict:
    """Enrichment coverage stats for active postings."""
    total_active = session.execute(
        select(func.count()).select_from(Posting).where(Posting.is_active.is_(True))
    ).scalar_one()

    enriched = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(select(Posting.id).where(Posting.is_active.is_(True)))
        )
    ).scalar_one()

    with_brands = session.execute(
        select(func.count(func.distinct(PostingBrandMention.posting_id))).where(
            PostingBrandMention.posting_id.in_(
                select(Posting.id).where(Posting.is_active.is_(True))
            )
        )
    ).scalar_one()

    return {
        "total_active": total_active,
        "enriched": enriched,
        "with_brands": with_brands,
        "unenriched": total_active - enriched,
    }


def get_per_company_counts(session: Session) -> list[dict]:
    """Active posting counts per company."""
    stmt = (
        select(Company.name, func.count(Posting.id).label("count"))
        .join(Posting, Company.id == Posting.company_id)
        .where(Posting.is_active.is_(True))
        .group_by(Company.name)
        .order_by(func.count(Posting.id).desc())
    )
    rows = session.execute(stmt).all()
    return [{"company": row.name, "count": row.count} for row in rows]


def get_error_summary(session: Session, days: int = 7) -> list[dict]:
    """Scrape runs with errors in the last N days."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(ScrapeRun, Company.name.label("company_name"))
        .join(Company, ScrapeRun.company_id == Company.id)
        .where(ScrapeRun.errors.isnot(None))
        .where(ScrapeRun.started_at > cutoff)
        .order_by(ScrapeRun.started_at.desc())
    )
    rows = session.execute(stmt).all()
    return [
        {
            "company": row.company_name,
            "started_at": row.ScrapeRun.started_at,
            "status": row.ScrapeRun.status,
            "errors": json.dumps(row.ScrapeRun.errors, default=str)[:200]
            if row.ScrapeRun.errors is not None
            else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Posting Explorer
# ---------------------------------------------------------------------------


def search_postings(
    session: Session,
    company_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    role_archetype: str | None = None,
    has_enrichment: bool | None = None,
    limit: int = 100,
) -> list[dict]:
    """Search postings with filters, joined to latest snapshot and enrichment."""
    latest = _latest_snapshot_subquery()

    stmt = (
        select(
            Posting.id,
            PostingSnapshot.title_raw,
            PostingSnapshot.location_raw,
            Company.name.label("company"),
            PostingEnrichment.role_archetype,
            PostingEnrichment.pay_min,
            PostingEnrichment.pay_max,
            Posting.is_active,
            Posting.first_seen_at,
        )
        .join(latest, Posting.id == latest.c.posting_id)
        .join(PostingSnapshot, PostingSnapshot.id == latest.c.snapshot_id)
        .join(Company, Posting.company_id == Company.id)
        .outerjoin(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
    )

    if company_id is not None:
        stmt = stmt.where(Posting.company_id == company_id)
    if is_active is not None:
        stmt = stmt.where(Posting.is_active.is_(is_active))
    if role_archetype is not None:
        stmt = stmt.where(PostingEnrichment.role_archetype == role_archetype)
    if has_enrichment is True:
        stmt = stmt.where(PostingEnrichment.id.isnot(None))
    elif has_enrichment is False:
        stmt = stmt.where(PostingEnrichment.id.is_(None))

    stmt = stmt.order_by(Posting.first_seen_at.desc()).limit(limit)

    rows = session.execute(stmt).all()
    return [
        {
            "posting_id": str(row.id),
            "title": row.title_raw,
            "location": row.location_raw,
            "company": row.company,
            "role_archetype": row.role_archetype,
            "pay_min": row.pay_min,
            "pay_max": row.pay_max,
            "is_active": row.is_active,
            "first_seen_at": row.first_seen_at,
        }
        for row in rows
    ]


def get_posting_detail(session: Session, posting_id: uuid.UUID) -> dict | None:
    """Full detail for a single posting."""
    latest = _latest_snapshot_subquery()

    stmt = (
        select(Posting, PostingSnapshot, PostingEnrichment, Company.name.label("company_name"))
        .join(latest, Posting.id == latest.c.posting_id)
        .join(PostingSnapshot, PostingSnapshot.id == latest.c.snapshot_id)
        .join(Company, Posting.company_id == Company.id)
        .outerjoin(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
        .where(Posting.id == posting_id)
    )

    row = session.execute(stmt).first()
    if not row:
        return None

    posting, snapshot, enrichment, company_name = row

    # Brand mentions
    brand_stmt = select(PostingBrandMention).where(PostingBrandMention.posting_id == posting_id)
    brands = session.execute(brand_stmt).scalars().all()

    result = {
        "posting_id": str(posting.id),
        "company": company_name,
        "is_active": posting.is_active,
        "first_seen_at": posting.first_seen_at,
        "last_seen_at": posting.last_seen_at,
        "title": snapshot.title_raw,
        "location": snapshot.location_raw,
        "full_text": snapshot.full_text_raw,
        "brand_mentions": [
            {
                "entity_name": b.entity_name,
                "entity_type": b.entity_type,
                "confidence": b.confidence_score,
            }
            for b in brands
        ],
    }

    if enrichment:
        result.update(
            {
                "role_archetype": enrichment.role_archetype,
                "role_level": enrichment.role_level,
                "pay_type": enrichment.pay_type,
                "pay_min": enrichment.pay_min,
                "pay_max": enrichment.pay_max,
                "pay_frequency": enrichment.pay_frequency,
                "employment_type": enrichment.employment_type,
                "enrichment_version": enrichment.enrichment_version,
                "enriched_at": enrichment.enriched_at,
            }
        )

    return result


def get_companies(session: Session) -> list[dict]:
    """All companies (for filter dropdowns)."""
    stmt = select(Company.id, Company.name).order_by(Company.name)
    rows = session.execute(stmt).all()
    return [{"id": str(row.id), "name": row.name} for row in rows]


def get_role_archetypes(session: Session) -> list[str]:
    """Distinct role archetypes (for filter dropdowns)."""
    stmt = (
        select(PostingEnrichment.role_archetype)
        .where(PostingEnrichment.role_archetype.isnot(None))
        .distinct()
        .order_by(PostingEnrichment.role_archetype)
    )
    rows = session.execute(stmt).scalars().all()
    return [r for r in rows if r is not None]
