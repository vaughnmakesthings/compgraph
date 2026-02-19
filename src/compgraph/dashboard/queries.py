"""Dashboard query functions (sync, read-only).

All functions take a sync Session and return lists of dicts for easy DataFrame conversion.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from compgraph.db.models import (
    Brand,
    Company,
    Posting,
    PostingBrandMention,
    PostingEnrichment,
    PostingSnapshot,
    Retailer,
    ScrapeRun,
)

logger = logging.getLogger(__name__)


def _timed_query(func_: Any) -> Any:
    """Log query name, duration, and row count at INFO level."""

    @wraps(func_)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func_(*args, **kwargs)
        elapsed = time.perf_counter() - start
        row_count = len(result) if isinstance(result, list) else (0 if result is None else 1)
        logger.info("query.%s duration=%.3fs rows=%s", func_.__name__, elapsed, row_count)
        return result

    return wrapper


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


def _format_completed_at(run: Any) -> Any:
    if run.completed_at:
        return run.completed_at
    if run.status == "pending":
        elapsed = datetime.now(UTC) - run.started_at
        minutes = int(elapsed.total_seconds() / 60)
        return f"Running ({minutes}m elapsed)"
    return "In Progress"


@_timed_query
def get_recent_scrape_runs(session: Session, limit: int = 20) -> list[dict]:
    """Recent scrape runs with company name."""
    stmt = (
        select(ScrapeRun, Company.name.label("company_name"))
        .join(Company, ScrapeRun.company_id == Company.id)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    results = []
    for row in rows:
        errors_json = row.ScrapeRun.errors
        has_errors = False
        has_warnings = False
        if isinstance(errors_json, dict):
            has_errors = bool(errors_json.get("errors"))
            has_warnings = bool(errors_json.get("warnings"))
        results.append(
            {
                "company": row.company_name,
                "started_at": row.ScrapeRun.started_at,
                "completed_at": _format_completed_at(row.ScrapeRun),
                "scrape_status": row.ScrapeRun.status,
                "pages_scraped": row.ScrapeRun.pages_scraped,
                "jobs_found": row.ScrapeRun.jobs_found,
                "snapshots_created": row.ScrapeRun.snapshots_created,
                "postings_closed": row.ScrapeRun.postings_closed,
                "has_errors": has_errors,
                "warnings": has_warnings,
            }
        )
    return results


@_timed_query
def get_latest_pipeline_status(session: Session) -> dict | None:
    latest_started = session.execute(select(func.max(ScrapeRun.started_at))).scalars().first()

    if latest_started is None:
        return None

    stmt = (
        select(
            ScrapeRun.status,
            ScrapeRun.started_at,
            ScrapeRun.completed_at,
            ScrapeRun.jobs_found,
            ScrapeRun.snapshots_created,
            ScrapeRun.errors,
            Company.name.label("company_name"),
            Company.slug,
        )
        .join(Company, ScrapeRun.company_id == Company.id)
        .where(ScrapeRun.started_at >= latest_started - timedelta(minutes=2))
    )
    rows = session.execute(stmt).all()

    if not rows:
        return None

    total_postings = 0
    total_snapshots = 0
    total_errors = 0
    succeeded = 0
    failed = 0
    company_states: dict[str, str] = {}
    company_results: dict[str, dict] = {}

    for row in rows:
        total_postings += row.jobs_found or 0
        total_snapshots += row.snapshots_created or 0
        company_states[row.slug] = row.status
        company_results[row.slug] = {
            "postings_found": row.jobs_found or 0,
            "snapshots_created": row.snapshots_created or 0,
        }
        if row.status == "completed":
            succeeded += 1
        elif row.status == "failed":
            failed += 1
            total_errors += 1

    has_incomplete = any(r.completed_at is None for r in rows)
    if has_incomplete:
        for slug, status in company_states.items():
            if status == "pending":
                company_states[slug] = "running"

    statuses = set(company_states.values())
    if "pending" in statuses or "running" in statuses:
        overall = "running"
    elif failed == len(rows):
        overall = "failed"
    elif failed > 0:
        overall = "partial"
    else:
        overall = "success"

    return {
        "status": overall,
        "started_at": latest_started,
        "total_postings_found": total_postings,
        "total_snapshots_created": total_snapshots,
        "companies_succeeded": succeeded,
        "companies_failed": failed,
        "total_errors": total_errors,
        "company_states": company_states,
        "company_results": company_results,
    }


@_timed_query
def get_enrichment_coverage(session: Session) -> dict:
    """Enrichment coverage stats for active postings.

    Combines coverage and pass breakdown into a single query using a CTE
    to share the active_ids filter across all counts.
    """
    active_ids = select(Posting.id).where(Posting.is_active.is_(True)).cte("active_ids")

    total_active = session.execute(select(func.count()).select_from(active_ids)).scalar_one()

    enriched = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(select(active_ids.c.id))
        )
    ).scalar_one()

    with_brands = session.execute(
        select(func.count(func.distinct(PostingBrandMention.posting_id))).where(
            PostingBrandMention.posting_id.in_(select(active_ids.c.id))
        )
    ).scalar_one()

    fully_enriched = session.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id))).where(
            PostingEnrichment.posting_id.in_(select(active_ids.c.id)),
            PostingEnrichment.enrichment_version.isnot(None),
            PostingEnrichment.enrichment_version.contains("pass2"),
        )
    ).scalar_one()

    return {
        "total_active": total_active,
        "enriched": enriched,
        "with_brands": with_brands,
        "unenriched": total_active - enriched,
        # Pass breakdown fields (used by Pipeline Health)
        "pass1_only": enriched - fully_enriched,
        "fully_enriched": fully_enriched,
    }


def get_enrichment_pass_breakdown(session: Session) -> dict:
    """Pass-level enrichment breakdown — delegates to get_enrichment_coverage().

    Kept for backward compatibility with Pipeline Health page.
    """
    return get_enrichment_coverage(session)


@_timed_query
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


@_timed_query
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


@_timed_query
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

    sep: Any = aggregate_order_by(literal_column("', '"), PostingBrandMention.entity_name)
    brands_sub = (
        select(func.string_agg(PostingBrandMention.entity_name, sep))
        .where(
            PostingBrandMention.posting_id == Posting.id,
            PostingBrandMention.entity_type == "client_brand",
        )
        .correlate(Posting)
        .scalar_subquery()
        .label("brands")
    )
    retailers_sub = (
        select(func.string_agg(PostingBrandMention.entity_name, sep))
        .where(
            PostingBrandMention.posting_id == Posting.id,
            PostingBrandMention.entity_type == "retailer",
        )
        .correlate(Posting)
        .scalar_subquery()
        .label("retailers")
    )

    stmt = (
        select(
            Posting.id,
            PostingSnapshot.title_raw,
            PostingSnapshot.location_raw,
            Company.name.label("company"),
            PostingEnrichment.role_archetype,
            PostingEnrichment.pay_min,
            PostingEnrichment.pay_max,
            brands_sub,
            retailers_sub,
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
            "title": row.title_raw,
            "company": row.company,
            "location": row.location_raw,
            "role_archetype": row.role_archetype,
            "brands": row.brands or "",
            "retailers": row.retailers or "",
            "pay_min": row.pay_min,
            "pay_max": row.pay_max,
            "is_active": row.is_active,
            "first_seen_at": row.first_seen_at,
            "posting_id": str(row.id),
        }
        for row in rows
    ]


@_timed_query
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


@_timed_query
def get_companies(session: Session) -> list[dict]:
    """All companies (for filter dropdowns)."""
    stmt = select(Company.id, Company.name).order_by(Company.name)
    rows = session.execute(stmt).all()
    return [{"id": str(row.id), "name": row.name} for row in rows]


@_timed_query
def get_last_scrape_timestamps(session: Session) -> list[dict]:
    company_stmt = select(
        Company.name,
        Company.slug,
        Company.last_scraped_at,
    ).order_by(Company.name)
    company_rows = session.execute(company_stmt).all()

    global_latest_stmt = select(func.max(ScrapeRun.completed_at)).where(
        ScrapeRun.status == "completed"
    )
    global_latest: datetime | None = session.execute(global_latest_stmt).scalar_one_or_none()

    results: list[dict] = [
        {
            "name": row.name,
            "slug": row.slug,
            "last_scraped_at": row.last_scraped_at,
        }
        for row in company_rows
    ]
    results.append(
        {
            "name": "__global__",
            "slug": "__global__",
            "last_scraped_at": global_latest,
        }
    )
    return results


FRESHNESS_ICONS: dict[str, str] = {
    "green": "\U0001f7e2",
    "yellow": "\U0001f7e1",
    "red": "\U0001f534",
    "gray": "\u26aa",
}


def freshness_color(last_scraped_at: datetime | None) -> str:
    """Return color based on age: green <24h, yellow 24-72h, red >72h, gray never."""
    if last_scraped_at is None:
        return "gray"
    age = datetime.now(UTC) - last_scraped_at
    if age < timedelta(hours=24):
        return "green"
    if age < timedelta(hours=72):
        return "yellow"
    return "red"


@_timed_query
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


# ---------------------------------------------------------------------------
# Brand Intel
# ---------------------------------------------------------------------------


@_timed_query
def get_brand_intel(session: Session, company_id: uuid.UUID) -> list[dict]:
    """Client brands mentioned in active postings for a company."""
    from sqlalchemy import case as case

    active_count = func.count(func.distinct(case((Posting.is_active.is_(True), Posting.id))))
    stmt = (
        select(
            func.coalesce(Brand.name, PostingBrandMention.entity_name).label("name"),
            active_count.label("active_postings"),
            func.min(Posting.first_seen_at).label("first_seen"),
        )
        .select_from(PostingBrandMention)
        .join(Posting, Posting.id == PostingBrandMention.posting_id)
        .outerjoin(Brand, Brand.id == PostingBrandMention.resolved_brand_id)
        .where(
            Posting.company_id == company_id,
            PostingBrandMention.entity_type == "client_brand",
        )
        .group_by(func.coalesce(Brand.name, PostingBrandMention.entity_name))
        .having(active_count > 0)
        .order_by(active_count.desc())
    )
    rows = session.execute(stmt).all()
    return [
        {
            "name": row.name,
            "active_postings": row.active_postings,
            "first_seen": row.first_seen,
        }
        for row in rows
    ]


@_timed_query
def get_retailer_intel(session: Session, company_id: uuid.UUID) -> list[dict]:
    """Retailers mentioned in active postings for a company."""
    from sqlalchemy import case as case

    active_count = func.count(func.distinct(case((Posting.is_active.is_(True), Posting.id))))
    stmt = (
        select(
            func.coalesce(Retailer.name, PostingBrandMention.entity_name).label("name"),
            active_count.label("active_postings"),
            func.min(Posting.first_seen_at).label("first_seen"),
        )
        .select_from(PostingBrandMention)
        .join(Posting, Posting.id == PostingBrandMention.posting_id)
        .outerjoin(Retailer, Retailer.id == PostingBrandMention.resolved_retailer_id)
        .where(
            Posting.company_id == company_id,
            PostingBrandMention.entity_type == "retailer",
        )
        .group_by(func.coalesce(Retailer.name, PostingBrandMention.entity_name))
        .having(active_count > 0)
        .order_by(active_count.desc())
    )
    rows = session.execute(stmt).all()
    return [
        {
            "name": row.name,
            "active_postings": row.active_postings,
            "first_seen": row.first_seen,
        }
        for row in rows
    ]
