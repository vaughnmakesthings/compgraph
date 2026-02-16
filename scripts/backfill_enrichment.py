#!/usr/bin/env python3
"""Backfill enrichment for all un-enriched postings.

Processes postings through the full enrichment pipeline:
  Pass 1 (Haiku classification) -> Pass 2 (Sonnet entity extraction) -> Fingerprinting

Usage:
    uv run python scripts/backfill_enrichment.py
    op run --env-file=.env -- uv run python scripts/backfill_enrichment.py

Options:
    --company-id UUID    Process only a specific company
    --batch-size INT     Override batch size (default: from settings)
    --concurrency INT    Override concurrency (default: from settings)
    --pass1-only         Run only Pass 1
    --pass2-only         Run only Pass 2
    --dry-run            Count un-enriched postings without processing
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill enrichment pipeline")
    parser.add_argument(
        "--company-id", type=uuid.UUID, default=None, help="Process only this company"
    )
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size override")
    parser.add_argument("--concurrency", type=int, default=None, help="Concurrency override")
    parser.add_argument("--pass1-only", action="store_true", help="Run only Pass 1")
    parser.add_argument("--pass2-only", action="store_true", help="Run only Pass 2")
    parser.add_argument("--dry-run", action="store_true", help="Count without processing")
    return parser.parse_args()


async def count_unenriched(company_id: uuid.UUID | None = None) -> dict[str, int]:
    """Count postings needing enrichment at each stage."""
    from sqlalchemy import func, select

    from compgraph.db.models import Posting, PostingEnrichment
    from compgraph.db.session import async_session_factory

    counts: dict[str, int] = {}

    async with async_session_factory() as session:
        # Total active postings
        stmt = select(func.count()).select_from(Posting).where(Posting.is_active.is_(True))
        if company_id:
            stmt = stmt.where(Posting.company_id == company_id)
        result = await session.execute(stmt)
        counts["total_active"] = result.scalar_one()

        # Postings without enrichment (need Pass 1)
        stmt = (
            select(func.count())
            .select_from(Posting)
            .outerjoin(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
            .where(PostingEnrichment.id.is_(None))
            .where(Posting.is_active.is_(True))
        )
        if company_id:
            stmt = stmt.where(Posting.company_id == company_id)
        result = await session.execute(stmt)
        counts["need_pass1"] = result.scalar_one()

        # Postings with Pass 1 enrichment but Pass 2 not yet run
        stmt = (
            select(func.count())
            .select_from(Posting)
            .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
            .where(PostingEnrichment.enrichment_version.not_like("%pass2%"))
            .where(Posting.is_active.is_(True))
        )
        if company_id:
            stmt = stmt.where(Posting.company_id == company_id)
        result = await session.execute(stmt)
        counts["need_pass2"] = result.scalar_one()

        # Postings without fingerprint
        stmt = (
            select(func.count())
            .select_from(Posting)
            .where(Posting.fingerprint_hash.is_(None))
            .where(Posting.is_active.is_(True))
        )
        if company_id:
            stmt = stmt.where(Posting.company_id == company_id)
        result = await session.execute(stmt)
        counts["need_fingerprint"] = result.scalar_one()

    return counts


async def run_backfill(args: argparse.Namespace) -> int:
    """Run the backfill pipeline. Returns exit code."""
    from compgraph.enrichment.orchestrator import (
        EnrichmentOrchestrator,
        EnrichmentRun,
    )

    # Show current state
    counts = await count_unenriched(args.company_id)
    logger.info("Current state:")
    logger.info("  Total active postings: %d", counts["total_active"])
    logger.info("  Need Pass 1: %d", counts["need_pass1"])
    logger.info("  Need Pass 2: %d", counts["need_pass2"])
    logger.info("  Need fingerprint: %d", counts["need_fingerprint"])

    if args.dry_run:
        logger.info("Dry run complete — no processing performed.")
        return 0

    if counts["total_active"] == 0:
        logger.info("No active postings found. Nothing to do.")
        return 0

    orchestrator = EnrichmentOrchestrator(
        batch_size=args.batch_size,
        concurrency=args.concurrency,
    )
    run = EnrichmentRun()

    if args.pass1_only:
        logger.info("Running Pass 1 only...")
        result = await orchestrator.run_pass1(run, company_id=args.company_id)
        logger.info("Pass 1 complete: %d succeeded, %d failed", result.succeeded, result.failed)
    elif args.pass2_only:
        logger.info("Running Pass 2 only...")
        result = await orchestrator.run_pass2(run, company_id=args.company_id)
        logger.info("Pass 2 complete: %d succeeded, %d failed", result.succeeded, result.failed)
    else:
        logger.info("Running full pipeline (Pass 1 -> Pass 2 -> Fingerprinting)...")
        pass1_result, pass2_result = await orchestrator.run_full(run, company_id=args.company_id)
        logger.info(
            "Full pipeline complete: Pass 1 (%d ok, %d fail), Pass 2 (%d ok, %d fail)",
            pass1_result.succeeded,
            pass1_result.failed,
            pass2_result.succeeded,
            pass2_result.failed,
        )

    # Show updated state
    updated_counts = await count_unenriched(args.company_id)
    logger.info("Updated state:")
    logger.info("  Need Pass 1: %d", updated_counts["need_pass1"])
    logger.info("  Need Pass 2: %d", updated_counts["need_pass2"])
    logger.info("  Need fingerprint: %d", updated_counts["need_fingerprint"])

    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_backfill(args))
    except KeyboardInterrupt:
        logger.info("Interrupted — committed work persists.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
