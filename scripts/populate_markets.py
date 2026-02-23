#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("populate_markets")


async def populate() -> int:
    from sqlalchemy import select

    from compgraph.db.models import LocationMapping, Market
    from compgraph.db.session import async_session_factory, engine

    try:
        async with async_session_factory() as session:
            stmt = select(
                LocationMapping.metro_name,
                LocationMapping.metro_state,
                LocationMapping.metro_country,
            ).distinct()
            metros = (await session.execute(stmt)).all()

            existing = {
                (r[0], r[1], r[2] or "US")
                for r in (
                    await session.execute(select(Market.name, Market.state, Market.country))
                ).all()
            }

            inserted = 0
            for metro_name, metro_state, metro_country in metros:
                if (metro_name, metro_state, metro_country or "US") in existing:
                    continue
                market = Market(
                    name=metro_name,
                    state=metro_state,
                    country=metro_country,
                )
                session.add(market)
                inserted += 1

            await session.commit()

        logger.info(
            "Inserted %d new markets (skipped %d existing)",
            inserted,
            len(existing),
        )
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    try:
        return asyncio.run(populate())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
