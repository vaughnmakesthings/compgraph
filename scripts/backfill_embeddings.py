#!/usr/bin/env python3
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
logger = logging.getLogger("backfill_embeddings")

BATCH_SIZE = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill embeddings for enriched postings")
    parser.add_argument("--dry-run", action="store_true", help="Count without processing")
    parser.add_argument("--limit", type=int, default=None, help="Max postings to process")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size")
    return parser.parse_args()


async def count_missing() -> int:
    from sqlalchemy import func, select

    from compgraph.db.models import PostingEnrichment
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = (
            select(func.count())
            .select_from(PostingEnrichment)
            .where(PostingEnrichment.embedding.is_(None))
            .where(PostingEnrichment.enrichment_version.like("%pass2%"))
        )
        result = await session.execute(stmt)
        return result.scalar_one()


async def run_backfill(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from compgraph.db.models import PostingEnrichment
    from compgraph.db.session import async_session_factory
    from compgraph.enrichment.embeddings import generate_embeddings_batch

    total_missing = await count_missing()
    logger.info("Enrichments needing embeddings: %d", total_missing)

    if args.dry_run:
        logger.info("Dry run complete.")
        return 0

    if total_missing == 0:
        logger.info("Nothing to backfill.")
        return 0

    processed = 0
    remaining = args.limit or total_missing

    while remaining > 0:
        batch_size = min(args.batch_size, remaining)

        async with async_session_factory() as session:
            stmt = (
                select(PostingEnrichment)
                .where(PostingEnrichment.embedding.is_(None))
                .where(PostingEnrichment.enrichment_version.like("%pass2%"))
                .limit(batch_size)
            )
            result = await session.execute(stmt)
            enrichments = list(result.scalars().all())

            if not enrichments:
                break

            texts = []
            for e in enrichments:
                title = e.title_normalized or ""
                content = e.content_role_specific or ""
                texts.append(f"{title} {content}".strip() or "empty")

            embeddings = await generate_embeddings_batch(texts)

            for enrichment, embedding in zip(enrichments, embeddings, strict=True):
                enrichment.embedding = embedding

            await session.commit()

        processed += len(enrichments)
        remaining -= len(enrichments)
        logger.info("Progress: %d / %d processed", processed, total_missing)

        if len(enrichments) < batch_size:
            break

    logger.info("Backfill complete: %d embeddings generated", processed)
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_backfill(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
