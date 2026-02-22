#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seed_locations")

BATCH_SIZE = 50
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a geography expert. Given a list of (city, state, country) tuples,
map each to its US Census Metropolitan Statistical Area (MSA) name or Canadian Census
Metropolitan Area (CMA) name.

Respond with a JSON array where each element has:
- city: the input city name (exactly as provided)
- state: the input state/province code (exactly as provided)
- country: "US" or "CA" (exactly as provided)
- metro_name: the MSA/CMA name (e.g., "Dallas-Fort Worth-Arlington")
- metro_state: primary state of the metro (e.g., "TX")
- metro_country: "US" or "CA"

For cities not in any MSA/CMA, use the city name itself as metro_name.
Return ONLY the JSON array, no other text."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed location_mappings table using LLM metro area classification"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count locations without making API calls",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Locations per LLM batch (default: {BATCH_SIZE})",
    )
    return parser.parse_args()


async def extract_distinct_locations() -> list[tuple[str, str, str]]:
    from compgraph.enrichment.normalizers import normalize_location_raw
    from sqlalchemy import text

    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT DISTINCT location_raw FROM posting_snapshots "
                    "WHERE location_raw IS NOT NULL"
                )
            )
        ).all()

    locations: set[tuple[str, str, str]] = set()
    for (raw,) in rows:
        result = normalize_location_raw(raw)
        if result:
            locations.add(result)

    return sorted(locations)


async def get_existing_mappings() -> set[tuple[str, str, str]]:
    from sqlalchemy import select

    from compgraph.db.models import LocationMapping
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(
                    LocationMapping.city_normalized,
                    LocationMapping.state,
                    LocationMapping.country,
                )
            )
        ).all()
    return {(r[0], r[1], r[2]) for r in rows}


async def classify_batch(
    client: anthropic.AsyncAnthropic,
    batch: list[tuple[str, str, str]],
) -> list[dict[str, str]]:

    from compgraph.enrichment.client import strip_markdown_fences

    input_text = json.dumps(
        [{"city": city, "state": state, "country": country} for city, state, country in batch]
    )

    response: anthropic.types.Message = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": input_text}],
    )

    raw_text = response.content[0].text
    cleaned = strip_markdown_fences(raw_text)
    return json.loads(cleaned)


async def run_seed(args: argparse.Namespace) -> int:
    import anthropic

    from compgraph.db.models import LocationMapping
    from compgraph.db.session import async_session_factory, engine

    try:
        all_locations = await extract_distinct_locations()
        existing = await get_existing_mappings()
        new_locations = [loc for loc in all_locations if loc not in existing]

        logger.info(
            "Total distinct locations: %d, already seeded: %d, new: %d",
            len(all_locations),
            len(existing),
            len(new_locations),
        )

        if args.dry_run:
            batch_count = (len(new_locations) + args.batch_size - 1) // args.batch_size
            logger.info(
                "Dry run -- would seed %d locations in %d batches",
                len(new_locations),
                batch_count,
            )
            return 0

        if not new_locations:
            logger.info("Nothing to seed.")
            return 0

        client = anthropic.AsyncAnthropic()
        total_inserted = 0

        for i in range(0, len(new_locations), args.batch_size):
            batch = new_locations[i : i + args.batch_size]
            batch_num = i // args.batch_size + 1
            logger.info("Batch %d: classifying %d locations...", batch_num, len(batch))

            try:
                results = await classify_batch(client, batch)
            except Exception:
                logger.exception("Batch %d failed -- skipping", batch_num)
                continue

            async with async_session_factory() as session:
                batch_inserted = 0
                for item in results:
                    mapping = LocationMapping(
                        city_normalized=item["city"],
                        state=item["state"],
                        country=item["country"],
                        metro_name=item["metro_name"],
                        metro_state=item["metro_state"],
                        metro_country=item["metro_country"],
                    )
                    session.add(mapping)
                    batch_inserted += 1
                await session.commit()
                total_inserted += batch_inserted
                logger.info(
                    "Batch %d: inserted %d mappings (total: %d)",
                    batch_num,
                    batch_inserted,
                    total_inserted,
                )

        logger.info("Seeding complete: %d mappings inserted", total_inserted)
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_seed(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
