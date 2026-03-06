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
logger = logging.getLogger("backfill_geocoding")

NOMINATIM_DELAY = 1.1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill geocoding for existing postings")
    parser.add_argument("--dry-run", action="store_true", help="Count without processing")
    parser.add_argument("--limit", type=int, default=None, help="Max unique locations to process")
    return parser.parse_args()


async def count_missing() -> dict[str, int]:
    from sqlalchemy import func, select

    from compgraph.db.models import Posting, PostingSnapshot
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        total_stmt = (
            select(func.count())
            .select_from(Posting)
            .where(Posting.latitude.is_(None))
            .where(Posting.is_active.is_(True))
        )
        total_result = await session.execute(total_stmt)
        total = total_result.scalar_one()

        unique_stmt = (
            select(func.count(func.distinct(PostingSnapshot.location_raw)))
            .select_from(Posting)
            .join(PostingSnapshot, Posting.id == PostingSnapshot.posting_id)
            .where(Posting.latitude.is_(None))
            .where(Posting.is_active.is_(True))
            .where(PostingSnapshot.location_raw.isnot(None))
        )
        unique_result = await session.execute(unique_stmt)
        unique_locations = unique_result.scalar_one()

    return {"total_postings": total, "unique_locations": unique_locations}


async def run_backfill(args: argparse.Namespace) -> int:
    from sqlalchemy import func, select, update

    from compgraph.db.models import Posting, PostingSnapshot
    from compgraph.db.session import async_session_factory
    from compgraph.geocoding import compute_h3_index, geocode_location

    counts = await count_missing()
    logger.info("Postings needing geocoding: %d", counts["total_postings"])
    logger.info("Unique location strings: %d", counts["unique_locations"])

    if args.dry_run:
        logger.info("Dry run complete.")
        return 0

    if counts["unique_locations"] == 0:
        logger.info("Nothing to backfill.")
        return 0

    async with async_session_factory() as session:
        loc_stmt = (
            select(func.distinct(PostingSnapshot.location_raw))
            .select_from(Posting)
            .join(PostingSnapshot, Posting.id == PostingSnapshot.posting_id)
            .where(Posting.latitude.is_(None))
            .where(Posting.is_active.is_(True))
            .where(PostingSnapshot.location_raw.isnot(None))
        )
        result = await session.execute(loc_stmt)
        unique_locations = [row[0] for row in result.all()]

    limit = args.limit or len(unique_locations)
    locations_to_process = unique_locations[:limit]

    geocoded = 0
    failed = 0
    postings_updated = 0

    for i, location_str in enumerate(locations_to_process):
        coords = await geocode_location(location_str)

        if coords:
            lat, lng = coords
            h3_idx = compute_h3_index(lat, lng)
            geocoded += 1

            async with async_session_factory() as session:
                posting_ids_stmt = (
                    select(Posting.id)
                    .join(PostingSnapshot, Posting.id == PostingSnapshot.posting_id)
                    .where(PostingSnapshot.location_raw == location_str)
                    .where(Posting.latitude.is_(None))
                )
                id_result = await session.execute(posting_ids_stmt)
                ids = [row[0] for row in id_result.all()]

                if ids:
                    await session.execute(
                        update(Posting)
                        .where(Posting.id.in_(ids))
                        .values(latitude=lat, longitude=lng, h3_index=h3_idx)
                    )
                    await session.commit()
                    postings_updated += len(ids)
        else:
            failed += 1

        if (i + 1) % 50 == 0:
            logger.info(
                "Progress: %d / %d locations (geocoded=%d, failed=%d, postings=%d)",
                i + 1,
                len(locations_to_process),
                geocoded,
                failed,
                postings_updated,
            )

        await asyncio.sleep(NOMINATIM_DELAY)

    logger.info(
        "Backfill complete: %d locations geocoded, %d failed, %d postings updated",
        geocoded,
        failed,
        postings_updated,
    )
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
