"""Entity resolution — match extracted entities against Brand/Retailer dimension tables."""

from __future__ import annotations

import logging
import re
import uuid

from rapidfuzz import fuzz
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Brand, PostingBrandMention, PostingEnrichment, Retailer
from compgraph.enrichment.schemas import EntityMention

logger = logging.getLogger(__name__)

# Fuzzy matching thresholds
EXACT_THRESHOLD = 100
AUTO_ACCEPT_THRESHOLD = 85
REVIEW_THRESHOLD = 70


def normalize_entity_name(name: str) -> str:
    """Normalize an entity name for matching.

    Strips whitespace, removes possessives, normalizes case.
    """
    name = name.strip()
    # Remove possessives: "Walmart's" → "Walmart"
    name = re.sub(r"'s$", "", name)
    return name


async def _find_brand(session: AsyncSession, entity_name: str) -> tuple[uuid.UUID | None, float]:
    """Find a matching brand by name, slug, or fuzzy match.

    Returns (brand_id, match_score) or (None, 0.0) if no match.
    """
    normalized = normalize_entity_name(entity_name)

    # Tier 1: Exact name match (case-insensitive)
    stmt = select(Brand).where(func.lower(Brand.name) == normalized.lower())
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand:
        return brand.id, 100.0

    # Tier 2: Slug match
    entity_slug = slugify(normalized)
    stmt = select(Brand).where(Brand.slug == entity_slug)
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand:
        return brand.id, 95.0

    # Tier 3: Fuzzy match against all brands
    stmt = select(Brand)
    result = await session.execute(stmt)
    all_brands = result.scalars().all()

    best_score = 0.0
    best_brand_id: uuid.UUID | None = None
    for brand in all_brands:
        score = fuzz.token_sort_ratio(normalized.lower(), brand.name.lower())
        if score > best_score:
            best_score = score
            best_brand_id = brand.id

    if best_score >= AUTO_ACCEPT_THRESHOLD:
        return best_brand_id, best_score
    if best_score >= REVIEW_THRESHOLD:
        logger.info(
            "Fuzzy brand match for '%s' (score=%.1f) — accepted but flagged for review",
            entity_name,
            best_score,
        )
        return best_brand_id, best_score

    return None, 0.0


async def _find_retailer(session: AsyncSession, entity_name: str) -> tuple[uuid.UUID | None, float]:
    """Find a matching retailer by name, slug, or fuzzy match.

    Returns (retailer_id, match_score) or (None, 0.0) if no match.
    """
    normalized = normalize_entity_name(entity_name)

    # Tier 1: Exact name match (case-insensitive)
    stmt = select(Retailer).where(func.lower(Retailer.name) == normalized.lower())
    result = await session.execute(stmt)
    retailer = result.scalar_one_or_none()
    if retailer:
        return retailer.id, 100.0

    # Tier 2: Slug match
    entity_slug = slugify(normalized)
    stmt = select(Retailer).where(Retailer.slug == entity_slug)
    result = await session.execute(stmt)
    retailer = result.scalar_one_or_none()
    if retailer:
        return retailer.id, 95.0

    # Tier 3: Fuzzy match against all retailers
    stmt = select(Retailer)
    result = await session.execute(stmt)
    all_retailers = result.scalars().all()

    best_score = 0.0
    best_retailer_id: uuid.UUID | None = None
    for retailer in all_retailers:
        score = fuzz.token_sort_ratio(normalized.lower(), retailer.name.lower())
        if score > best_score:
            best_score = score
            best_retailer_id = retailer.id

    if best_score >= AUTO_ACCEPT_THRESHOLD:
        return best_retailer_id, best_score
    if best_score >= REVIEW_THRESHOLD:
        logger.info(
            "Fuzzy retailer match for '%s' (score=%.1f) — accepted but flagged for review",
            entity_name,
            best_score,
        )
        return best_retailer_id, best_score

    return None, 0.0


async def _create_brand(session: AsyncSession, entity_name: str) -> uuid.UUID:
    """Create a new Brand record."""
    normalized = normalize_entity_name(entity_name)
    brand = Brand(
        name=normalized,
        slug=slugify(normalized),
    )
    session.add(brand)
    await session.flush()
    logger.info("Created new brand: %s (id=%s)", normalized, brand.id)
    return brand.id


async def _create_retailer(session: AsyncSession, entity_name: str) -> uuid.UUID:
    """Create a new Retailer record."""
    normalized = normalize_entity_name(entity_name)
    retailer = Retailer(
        name=normalized,
        slug=slugify(normalized),
    )
    session.add(retailer)
    await session.flush()
    logger.info("Created new retailer: %s (id=%s)", normalized, retailer.id)
    return retailer.id


async def resolve_entity(
    session: AsyncSession,
    entity_name: str,
    entity_type: str,
) -> tuple[uuid.UUID | None, uuid.UUID | None, bool]:
    """Resolve an entity mention to a Brand or Retailer record.

    Three-tier matching: exact → slug → fuzzy.
    Creates new records when no match is found above threshold.

    Args:
        session: Async database session.
        entity_name: Raw entity name from LLM extraction.
        entity_type: One of "client_brand", "retailer", "ambiguous".

    Returns:
        Tuple of (brand_id, retailer_id, is_new).
        Only one of brand_id/retailer_id will be non-None (unless ambiguous resolved to both).
    """
    if entity_type == "client_brand":
        brand_id, _score = await _find_brand(session, entity_name)
        if brand_id:
            return brand_id, None, False
        # No match — create new brand
        new_id = await _create_brand(session, entity_name)
        return new_id, None, True

    if entity_type == "retailer":
        retailer_id, _score = await _find_retailer(session, entity_name)
        if retailer_id:
            return None, retailer_id, False
        # No match — create new retailer
        new_id = await _create_retailer(session, entity_name)
        return None, new_id, True

    # Ambiguous: try both, prefer higher confidence match
    brand_id, brand_score = await _find_brand(session, entity_name)
    retailer_id, retailer_score = await _find_retailer(session, entity_name)

    if brand_id and retailer_id:
        # Both matched — pick the higher score
        if brand_score >= retailer_score:
            return brand_id, None, False
        return None, retailer_id, False

    if brand_id:
        return brand_id, None, False
    if retailer_id:
        return None, retailer_id, False

    # Neither matched — default to brand for ambiguous
    new_id = await _create_brand(session, entity_name)
    return new_id, None, True


async def save_brand_mentions(
    session: AsyncSession,
    posting_id: uuid.UUID,
    enrichment_id: uuid.UUID,
    entities: list[EntityMention],
    resolved: list[tuple[uuid.UUID | None, uuid.UUID | None, bool]],
) -> int:
    """Create PostingBrandMention rows for each entity.

    Also updates the PostingEnrichment with the primary brand_id/retailer_id
    (first entity of each type with highest confidence).
    """
    primary_brand_id: uuid.UUID | None = None
    primary_retailer_id: uuid.UUID | None = None
    count = 0

    # Sort by confidence descending so primary entity is highest confidence
    sorted_pairs = sorted(
        zip(entities, resolved, strict=True),
        key=lambda item: item[0].confidence,
        reverse=True,
    )

    for entity, (brand_id, retailer_id, _is_new) in sorted_pairs:
        mention = PostingBrandMention(
            posting_id=posting_id,
            entity_name=entity.entity_name,
            entity_type=entity.entity_type,
            confidence_score=entity.confidence,
            resolved_brand_id=brand_id,
            resolved_retailer_id=retailer_id,
        )
        session.add(mention)
        count += 1

        # Track primary entities (highest confidence, first occurrence)
        if brand_id and primary_brand_id is None:
            primary_brand_id = brand_id
        if retailer_id and primary_retailer_id is None:
            primary_retailer_id = retailer_id

    # Update PostingEnrichment with primary entities
    if primary_brand_id or primary_retailer_id:
        stmt = select(PostingEnrichment).where(PostingEnrichment.id == enrichment_id)
        result = await session.execute(stmt)
        enrichment = result.scalar_one_or_none()
        if enrichment:
            if primary_brand_id:
                enrichment.brand_id = primary_brand_id
            if primary_retailer_id:
                enrichment.retailer_id = primary_retailer_id

    await session.flush()
    return count
