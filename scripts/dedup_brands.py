#!/usr/bin/env python3
"""One-time brand deduplication: merge duplicate brand pairs into canonical names.

Merges: Reliant→Reliant Energy, LG→LG Electronics, Virgin Mobile→Virgin Plus.
Updates posting_brand_mentions.resolved_brand_id and posting_enrichments.brand_id,
then deletes the duplicate brand rows.

Usage:
    op run --env-file=.env -- uv run python scripts/dedup_brands.py
    op run --env-file=.env -- uv run python scripts/dedup_brands.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dedup_brands")

# (duplicate_name, canonical_name) — duplicate will be merged into canonical
MERGE_PAIRS: list[tuple[str, str]] = [
    ("Reliant", "Reliant Energy"),
    ("LG", "LG Electronics"),
    ("Virgin Mobile", "Virgin Plus"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge duplicate brands into canonical names")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without applying")
    return parser.parse_args()


async def run_dedup(args: argparse.Namespace) -> int:
    from sqlalchemy import func, select, update
    from sqlalchemy.exc import IntegrityError

    from compgraph.db.models import Brand, PostingBrandMention, PostingEnrichment
    from compgraph.db.session import async_session_factory, engine

    try:
        async with async_session_factory() as session:
            for dup_name, canon_name in MERGE_PAIRS:
                dup_stmt = select(Brand).where(Brand.name == dup_name)
                canon_stmt = select(Brand).where(Brand.name == canon_name)

                dup_brand = (await session.execute(dup_stmt)).scalar_one_or_none()
                canon_brand = (await session.execute(canon_stmt)).scalar_one_or_none()

                if not dup_brand:
                    logger.info("Duplicate '%s' not found — skipping", dup_name)
                    continue
                if not canon_brand:
                    logger.warning(
                        "Canonical '%s' not found — cannot merge '%s' (run seed first?)",
                        canon_name,
                        dup_name,
                    )
                    continue
                if dup_brand.id == canon_brand.id:
                    logger.info("'%s' and '%s' are same brand — skipping", dup_name, canon_name)
                    continue

                # Count affected rows (use count query, do not load rows)
                pbm_stmt = (
                    select(func.count())
                    .select_from(PostingBrandMention)
                    .where(PostingBrandMention.resolved_brand_id == dup_brand.id)
                )
                pe_stmt = (
                    select(func.count())
                    .select_from(PostingEnrichment)
                    .where(PostingEnrichment.brand_id == dup_brand.id)
                )
                pbm_count = (await session.execute(pbm_stmt)).scalar() or 0
                pe_count = (await session.execute(pe_stmt)).scalar() or 0

                logger.info(
                    "Would merge '%s' (id=%s) → '%s' (id=%s): "
                    "%d posting_brand_mentions, %d posting_enrichments",
                    dup_name,
                    dup_brand.id,
                    canon_name,
                    canon_brand.id,
                    pbm_count,
                    pe_count,
                )

                if args.dry_run:
                    continue

                await session.execute(
                    update(PostingBrandMention)
                    .where(PostingBrandMention.resolved_brand_id == dup_brand.id)
                    .values(resolved_brand_id=canon_brand.id)
                )
                await session.execute(
                    update(PostingEnrichment)
                    .where(PostingEnrichment.brand_id == dup_brand.id)
                    .values(brand_id=canon_brand.id)
                )
                await session.delete(dup_brand)

                try:
                    await session.commit()
                    logger.info("Merged '%s' → '%s'", dup_name, canon_name)
                except IntegrityError:
                    await session.rollback()
                    logger.exception("Failed to merge '%s' — rollback", dup_name)
                    return 1

        logger.info("Dedup complete.")
        return 0

    finally:
        await engine.dispose()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_dedup(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
