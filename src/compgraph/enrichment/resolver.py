"""Entity resolution — match extracted entities against Brand/Retailer dimension tables."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Protocol, cast, runtime_checkable

from rapidfuzz import fuzz
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Brand, PostingBrandMention, PostingEnrichment, Retailer
from compgraph.enrichment.schemas import EntityMention

logger = logging.getLogger(__name__)


@runtime_checkable
class DimensionEntity(Protocol):
    id: uuid.UUID
    name: str
    slug: str


DimensionModel = type[Brand] | type[Retailer]


def normalize_entity_name(name: str) -> str:
    """Normalize an entity name for matching.

    Strips whitespace, removes possessives, normalizes case.
    """
    name = name.strip()
    # Remove possessives: "Walmart's" → "Walmart"
    name = re.sub(r"'s$", "", name)
    return name


async def _find_entity(
    session: AsyncSession, entity_name: str, model: DimensionModel
) -> tuple[uuid.UUID | None, float]:
    """Find a matching entity by name, slug, or fuzzy match.

    Works for both Brand and Retailer models (identical schema structure).
    Returns (entity_id, match_score) or (None, 0.0) if no match.
    """
    normalized = normalize_entity_name(entity_name)
    label = model.__name__  # "Brand" or "Retailer"

    # Tier 1: Exact name match (case-insensitive)
    stmt = select(model).where(func.lower(model.name) == normalized.lower())
    result = await session.execute(stmt)
    entity = result.scalar_one_or_none()
    if entity:
        matched = cast(DimensionEntity, entity)
        return matched.id, 100.0

    # Tier 2: Slug match
    entity_slug = slugify(normalized)
    stmt = select(model).where(model.slug == entity_slug)
    result = await session.execute(stmt)
    entity = result.scalar_one_or_none()
    if entity:
        matched = cast(DimensionEntity, entity)
        return matched.id, 95.0

    # Tier 3: Fuzzy match against all entities
    stmt = select(model)
    result = await session.execute(stmt)
    all_entities = result.scalars().all()

    best_score = 0.0
    best_id: uuid.UUID | None = None
    for row in all_entities:
        candidate = cast(DimensionEntity, row)
        score = fuzz.token_sort_ratio(normalized.lower(), candidate.name.lower())
        if score > best_score:
            best_score = score
            best_id = candidate.id

    from compgraph.config import settings

    if best_score >= settings.ENTITY_AUTO_ACCEPT_THRESHOLD:
        return best_id, best_score
    if best_score >= settings.ENTITY_REVIEW_THRESHOLD:
        logger.info(
            "Fuzzy %s match for '%s' (score=%.1f) — accepted but flagged for review",
            label,
            entity_name,
            best_score,
        )
        return best_id, best_score

    return None, 0.0


async def _create_entity(
    session: AsyncSession, entity_name: str, model: DimensionModel
) -> uuid.UUID:
    """Create a new dimension record. Uses savepoint for concurrent duplicate handling.

    Works for both Brand and Retailer models (identical schema structure).
    """
    from sqlalchemy.exc import IntegrityError

    normalized = normalize_entity_name(entity_name)
    entity_slug = slugify(normalized)
    label = model.__name__  # "Brand" or "Retailer"
    entity = model(name=normalized, slug=entity_slug)
    try:
        async with session.begin_nested():
            session.add(entity)
            await session.flush()
    except IntegrityError:
        # Savepoint rolled back, session state preserved — re-query
        stmt = select(model).where(model.slug == entity_slug)
        result = await session.execute(stmt)
        existing = cast(DimensionEntity, result.scalar_one())
        logger.info(
            "%s already exists (concurrent create): %s (id=%s)",
            label,
            normalized,
            existing.id,
        )
        return existing.id
    matched = cast(DimensionEntity, entity)
    logger.info("Created new %s: %s (id=%s)", label, normalized, matched.id)
    return matched.id


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
        brand_id, _score = await _find_entity(session, entity_name, Brand)
        if brand_id:
            return brand_id, None, False
        new_id = await _create_entity(session, entity_name, Brand)
        return new_id, None, True

    if entity_type == "retailer":
        retailer_id, _score = await _find_entity(session, entity_name, Retailer)
        if retailer_id:
            return None, retailer_id, False
        new_id = await _create_entity(session, entity_name, Retailer)
        return None, new_id, True

    # Ambiguous: try both, prefer higher confidence match
    brand_id, brand_score = await _find_entity(session, entity_name, Brand)
    retailer_id, retailer_score = await _find_entity(session, entity_name, Retailer)

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
    new_id = await _create_entity(session, entity_name, Brand)
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
