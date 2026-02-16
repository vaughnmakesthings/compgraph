#!/usr/bin/env python3
"""Validate enrichment quality by spot-checking random postings.

Randomly samples postings across all competitors and outputs a CSV
for human review of enrichment accuracy.

Usage:
    uv run python scripts/validate_enrichment.py
    op run --env-file=.env -- uv run python scripts/validate_enrichment.py

Options:
    --sample-size INT    Number of postings to sample (default: 50)
    --output PATH        Output CSV path (default: enrichment_validation.csv)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("validate")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate enrichment quality")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of postings to sample")
    parser.add_argument(
        "--output", type=str, default="enrichment_validation.csv", help="Output CSV path"
    )
    return parser.parse_args()


async def sample_enriched_postings(sample_size: int) -> list[dict]:
    """Sample enriched postings across all competitors."""
    from sqlalchemy import func, select

    from compgraph.db.models import (
        Brand,
        Company,
        Posting,
        PostingBrandMention,
        PostingEnrichment,
        PostingSnapshot,
        Retailer,
    )
    from compgraph.db.session import async_session_factory

    rows = []

    async with async_session_factory() as session:
        # Subquery: latest snapshot per posting
        latest_snapshot = (
            select(
                PostingSnapshot.posting_id,
                PostingSnapshot.id.label("snapshot_id"),
            )
            .distinct(PostingSnapshot.posting_id)
            .order_by(PostingSnapshot.posting_id, PostingSnapshot.created_at.desc())
            .subquery()
        )

        # Subquery: latest enrichment per posting
        latest_enrichment = (
            select(
                PostingEnrichment.posting_id,
                PostingEnrichment.id.label("enrichment_id"),
            )
            .distinct(PostingEnrichment.posting_id)
            .order_by(PostingEnrichment.posting_id, PostingEnrichment.enriched_at.desc())
            .subquery()
        )

        # Random sample of enriched postings with latest snapshot + enrichment
        stmt = (
            select(
                Posting,
                PostingSnapshot,
                PostingEnrichment,
                Company.name.label("company_name"),
            )
            .join(latest_enrichment, Posting.id == latest_enrichment.c.posting_id)
            .join(PostingEnrichment, PostingEnrichment.id == latest_enrichment.c.enrichment_id)
            .join(Company, Posting.company_id == Company.id)
            .join(latest_snapshot, Posting.id == latest_snapshot.c.posting_id)
            .join(PostingSnapshot, PostingSnapshot.id == latest_snapshot.c.snapshot_id)
            .where(Posting.is_active.is_(True))
            .order_by(func.random())
            .limit(sample_size)
        )

        result = await session.execute(stmt)
        samples = result.all()

        for posting, snapshot, enrichment, company_name in samples:
            # Get brand mentions for this posting
            mention_stmt = select(PostingBrandMention).where(
                PostingBrandMention.posting_id == posting.id
            )
            mention_result = await session.execute(mention_stmt)
            mentions = mention_result.scalars().all()

            brand_names = []
            retailer_names = []
            for mention in mentions:
                if mention.brand_id:
                    brand_stmt = select(Brand.name).where(Brand.id == mention.brand_id)
                    brand_result = await session.execute(brand_stmt)
                    name = brand_result.scalar_one_or_none()
                    if name:
                        brand_names.append(name)
                if mention.retailer_id:
                    retailer_stmt = select(Retailer.name).where(Retailer.id == mention.retailer_id)
                    retailer_result = await session.execute(retailer_stmt)
                    name = retailer_result.scalar_one_or_none()
                    if name:
                        retailer_names.append(name)

            pay_range = ""
            if enrichment.pay_min or enrichment.pay_max:
                pay_min = f"${enrichment.pay_min:.2f}" if enrichment.pay_min else "?"
                pay_max = f"${enrichment.pay_max:.2f}" if enrichment.pay_max else "?"
                freq = enrichment.pay_frequency or "?"
                pay_range = f"{pay_min}-{pay_max}/{freq}"

            rows.append(
                {
                    "posting_id": str(posting.id),
                    "company": company_name,
                    "title": snapshot.title_raw or "",
                    "location": snapshot.location_raw or "",
                    "role_archetype": enrichment.role_archetype or "",
                    "role_level": enrichment.role_level or "",
                    "employment_type": enrichment.employment_type or "",
                    "pay_range": pay_range,
                    "brands": "; ".join(brand_names),
                    "retailers": "; ".join(retailer_names),
                    "has_role_specific": "yes" if enrichment.content_role_specific else "no",
                    "fingerprint": (posting.fingerprint_hash or "")[:12],
                    "accurate": "",  # Human fills this in
                    "notes": "",  # Human fills this in
                }
            )

    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write rows to CSV file (sync helper to avoid async file open)."""
    import csv

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def run_validation(args: argparse.Namespace) -> int:
    """Run validation and write CSV. Returns exit code."""
    logger.info("Sampling %d enriched postings...", args.sample_size)

    rows = await sample_enriched_postings(args.sample_size)

    if not rows:
        logger.warning("No enriched postings found. Run backfill first.")
        return 1

    output_path = Path(args.output)
    fieldnames = [
        "posting_id",
        "company",
        "title",
        "location",
        "role_archetype",
        "role_level",
        "employment_type",
        "pay_range",
        "brands",
        "retailers",
        "has_role_specific",
        "fingerprint",
        "accurate",
        "notes",
    ]

    _write_csv(output_path, fieldnames, rows)

    logger.info("Wrote %d rows to %s", len(rows), output_path)
    logger.info("Companies represented: %s", ", ".join(sorted({r["company"] for r in rows})))

    # Summary stats
    archetypes = [r["role_archetype"] for r in rows if r["role_archetype"]]
    with_pay = [r for r in rows if r["pay_range"]]
    with_brands = [r for r in rows if r["brands"]]

    logger.info("Summary:")
    logger.info("  With role archetype: %d/%d", len(archetypes), len(rows))
    logger.info("  With pay data: %d/%d", len(with_pay), len(rows))
    logger.info("  With brand mentions: %d/%d", len(with_brands), len(rows))

    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_validation(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
