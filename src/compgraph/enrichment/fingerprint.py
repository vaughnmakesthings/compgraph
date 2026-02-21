"""Fingerprinting — detect reposted jobs via composite hash."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Brand, Posting, PostingEnrichment, PostingSnapshot

logger = logging.getLogger(__name__)

# Common title prefixes to strip for normalization
_TITLE_PREFIXES = [
    r"field\s+rep(?:resentative)?\s*[-\u2013\u2014:]\s*",
    r"brand\s+ambassador\s*[-\u2013\u2014:]\s*",
    r"merchandiser\s*[-\u2013\u2014:]\s*",
    r"retail\s+sales\s*[-\u2013\u2014:]\s*",
    r"demo\s+specialist\s*[-\u2013\u2014:]\s*",
]
_PREFIX_PATTERN = re.compile(
    r"^(" + "|".join(_TITLE_PREFIXES) + r")",
    re.IGNORECASE,
)


def normalize_title(title: str) -> str:
    """Normalize a title for fingerprinting.

    Lowercase, strip whitespace, remove common prefixes.
    """
    normalized = title.strip().lower()
    normalized = _PREFIX_PATTERN.sub("", normalized).strip()
    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_location(location: str) -> str:
    """Normalize a location for fingerprinting.

    Lowercase, strip whitespace, collapse spaces.
    """
    normalized = location.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def compute_content_hash(title: str, full_text: str) -> str:
    """Hash title + body for enrichment deduplication. Excludes location.

    Two postings with the same title and body but different locations
    (e.g., same job posted to Dallas and Houston) will produce the same
    hash, allowing the orchestrator to call the LLM only once per
    unique content.

    Unlike ``normalize_title`` (used for fingerprinting), this does NOT
    strip role prefixes — "Field Rep: Samsung" and "Merchandiser: Samsung"
    are distinct roles and must not collide.  Uses a null-byte separator
    to prevent delimiter collisions.
    """
    norm_title = re.sub(r"\s+", " ", title.strip().lower())
    norm_body = re.sub(r"\s+", " ", full_text.strip().lower())
    return hashlib.sha256(f"{norm_title}\0{norm_body}".encode()).hexdigest()


def generate_fingerprint(title: str, location: str, brand_slug: str | None) -> str:
    """Generate a composite fingerprint hash.

    Combines normalized title, location, and brand_slug into a SHA-256 hash.
    Deterministic: same inputs always produce the same hash.
    """
    norm_title = normalize_title(title)
    norm_location = normalize_location(location)
    brand = brand_slug or ""

    composite = f"{norm_title}\0{norm_location}\0{brand}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


async def detect_reposts(session: AsyncSession, company_id: uuid.UUID | None = None) -> int:
    """Detect and link reposted jobs via fingerprint matching.

    For each posting with enrichment but no fingerprint:
    1. Generate fingerprint from enrichment data
    2. Check for existing postings with same fingerprint + company_id
    3. If match found: increment times_reposted on canonical (oldest) posting
    4. Update fingerprint_hash on current posting

    Returns count of reposts detected.
    """
    # Fetch postings that have Pass 2-complete enrichment but no fingerprint.
    # Requires Pass 2 so brand_slug is available for accurate fingerprints.
    stmt = (
        select(Posting, PostingEnrichment)
        .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
        .where(Posting.fingerprint_hash.is_(None))
        .where(Posting.is_active.is_(True))
        .where(PostingEnrichment.enrichment_version.like("%pass2%"))
    )
    if company_id is not None:
        stmt = stmt.where(Posting.company_id == company_id)

    # Order by first_seen_at so oldest posting is fingerprinted first
    # and becomes the canonical for any repost cluster
    stmt = stmt.order_by(Posting.first_seen_at.asc())

    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        logger.info("Fingerprinting complete: 0 reposts detected")
        return 0

    posting_ids = [posting.id for posting, _ in rows]

    # Batch-load latest snapshots (1 query instead of N)
    latest_snapshot = (
        select(
            PostingSnapshot.posting_id,
            func.max(PostingSnapshot.created_at).label("max_created"),
        )
        .where(PostingSnapshot.posting_id.in_(posting_ids))
        .group_by(PostingSnapshot.posting_id)
        .subquery()
    )
    snapshot_stmt = select(PostingSnapshot).join(
        latest_snapshot,
        (PostingSnapshot.posting_id == latest_snapshot.c.posting_id)
        & (PostingSnapshot.created_at == latest_snapshot.c.max_created),
    )
    snapshot_result = await session.execute(snapshot_stmt)
    snapshot_map: dict[uuid.UUID, PostingSnapshot] = {
        s.posting_id: s for s in snapshot_result.scalars().all()
    }

    # Batch-load brand slugs (1 query instead of up to N)
    brand_ids = {e.brand_id for _, e in rows if e.brand_id is not None}
    brand_slug_map: dict[uuid.UUID, str] = {}
    if brand_ids:
        brand_stmt = select(Brand.id, Brand.slug).where(Brand.id.in_(brand_ids))
        brand_result = await session.execute(brand_stmt)
        brand_slug_map = dict(brand_result.all())  # type: ignore[arg-type]

    reposts_detected = 0

    for posting, enrichment in rows:
        snapshot = snapshot_map.get(posting.id)
        if not snapshot:
            continue

        brand_slug = brand_slug_map.get(enrichment.brand_id) if enrichment.brand_id else None

        fingerprint = generate_fingerprint(
            snapshot.title_raw or "",
            snapshot.location_raw or "",
            brand_slug,
        )

        # Update this posting's fingerprint
        posting.fingerprint_hash = fingerprint

        # Check for existing postings with same fingerprint and company
        # (still per-posting — fingerprint is computed above so can't be batch-checked)
        existing_stmt = (
            select(Posting)
            .where(Posting.fingerprint_hash == fingerprint)
            .where(Posting.company_id == posting.company_id)
            .where(Posting.id != posting.id)
            .order_by(Posting.first_seen_at.asc())
            .limit(1)
        )
        existing_result = await session.execute(existing_stmt)
        canonical = existing_result.scalar_one_or_none()

        if canonical:
            # This is a repost — increment counter on the canonical posting
            canonical.times_reposted += 1
            reposts_detected += 1
            logger.info(
                "Repost detected: posting %s matches canonical %s (fingerprint=%s...)",
                posting.id,
                canonical.id,
                fingerprint[:12],
            )

    await session.flush()
    logger.info("Fingerprinting complete: %d reposts detected", reposts_detected)
    return reposts_detected
