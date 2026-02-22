#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
import sys
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill_title_normalization")

BATCH_SIZE = 500


async def backfill() -> int:
    from sqlalchemy import func, select, update

    from compgraph.db.models import PostingEnrichment, PostingSnapshot
    from compgraph.db.session import async_session_factory, engine
    from compgraph.enrichment.normalizers import normalize_title_for_grouping

    try:
        async with async_session_factory() as session:
            total_stmt = (
                select(func.count())
                .select_from(PostingEnrichment)
                .where(PostingEnrichment.title_normalized.is_(None))
            )
            result = await session.execute(total_stmt)
            total_pending = result.scalar_one()

        logger.info("Found %d enrichments with title_normalized IS NULL", total_pending)
        if total_pending == 0:
            logger.info("Nothing to backfill.")
            return 0

        processed = 0
        updated = 0

        while True:
            async with async_session_factory() as session:
                latest_snapshot = (
                    select(
                        PostingSnapshot.posting_id,
                        PostingSnapshot.title_raw,
                        func.row_number()
                        .over(
                            partition_by=PostingSnapshot.posting_id,
                            order_by=PostingSnapshot.snapshot_date.desc(),
                        )
                        .label("rn"),
                    )
                ).subquery()

                stmt = (
                    select(
                        PostingEnrichment.id,
                        latest_snapshot.c.title_raw,
                    )
                    .join(
                        latest_snapshot,
                        (latest_snapshot.c.posting_id == PostingEnrichment.posting_id)
                        & (latest_snapshot.c.rn == 1),
                    )
                    .where(PostingEnrichment.title_normalized.is_(None))
                    .limit(BATCH_SIZE)
                )

                rows: list[tuple[uuid.UUID, str | None]] = list((await session.execute(stmt)).all())

                if not rows:
                    break

                batch_count = 0
                for enrichment_id, title_raw in rows:
                    normalized = normalize_title_for_grouping(title_raw)
                    # Use empty string for un-normalizable titles so they
                    # won't be re-queried (title_normalized IS NULL) forever.
                    await session.execute(
                        update(PostingEnrichment)
                        .where(PostingEnrichment.id == enrichment_id)
                        .values(title_normalized=normalized or "")
                    )
                    batch_count += 1

                await session.commit()
                updated += batch_count
                processed += len(rows)
                logger.info(
                    "Progress: %d/%d processed, %d updated",
                    processed,
                    total_pending,
                    updated,
                )

        logger.info("Backfill complete: %d processed, %d updated", processed, updated)
        return 0

    finally:
        await engine.dispose()


def main() -> int:
    try:
        return asyncio.run(backfill())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
