"""Enrichment pipeline orchestrator — batch processing with concurrency control."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.config import settings
from compgraph.db.session import async_session_factory
from compgraph.enrichment.client import get_anthropic_client
from compgraph.enrichment.pass1 import enrich_posting_pass1
from compgraph.enrichment.pass2 import enrich_posting_pass2
from compgraph.enrichment.queries import (
    fetch_pass1_complete_postings,
    fetch_unenriched_postings,
    save_enrichment,
)
from compgraph.enrichment.resolver import resolve_entity, save_brand_mentions

logger = logging.getLogger(__name__)


class EnrichmentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class EnrichResult:
    """Result summary from an enrichment batch run."""

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


@dataclass
class EnrichmentRun:
    """Tracks the state of an enrichment pipeline run."""

    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    pass1_result: EnrichResult | None = None
    pass2_result: EnrichResult | None = None

    def finish(self, result: EnrichResult) -> None:
        self.pass1_result = result
        self.finished_at = datetime.now(UTC)
        self._update_status(result)

    def finish_pass2(self, result: EnrichResult) -> None:
        self.pass2_result = result
        self.finished_at = datetime.now(UTC)
        self._compute_final_status()

    def _update_status(self, result: EnrichResult) -> None:
        if result.failed == 0 and result.succeeded > 0:
            self.status = EnrichmentStatus.SUCCESS
        elif result.succeeded > 0:
            self.status = EnrichmentStatus.PARTIAL
        elif result.succeeded == 0 and result.failed == 0:
            self.status = EnrichmentStatus.SUCCESS  # nothing to process
        else:
            self.status = EnrichmentStatus.FAILED

    def _compute_final_status(self) -> None:
        """Aggregate pass1 + pass2 results into a single status."""
        total_failed = 0
        total_succeeded = 0
        for r in (self.pass1_result, self.pass2_result):
            if r:
                total_failed += r.failed
                total_succeeded += r.succeeded

        if total_failed == 0 and total_succeeded > 0:
            self.status = EnrichmentStatus.SUCCESS
        elif total_succeeded > 0 and total_failed > 0:
            self.status = EnrichmentStatus.PARTIAL
        elif total_succeeded == 0 and total_failed == 0:
            self.status = EnrichmentStatus.SUCCESS
        else:
            self.status = EnrichmentStatus.FAILED


# In-memory run storage (mirrors scrape orchestrator pattern)
_runs: dict[uuid.UUID, EnrichmentRun] = {}


def _store_run(run: EnrichmentRun) -> None:
    _runs[run.run_id] = run


def get_enrichment_run(run_id: uuid.UUID) -> EnrichmentRun | None:
    return _runs.get(run_id)


def get_latest_enrichment_run() -> EnrichmentRun | None:
    if not _runs:
        return None
    return max(_runs.values(), key=lambda r: r.started_at)


async def _mark_pass2_complete(
    session: AsyncSession,
    enrichment_id: uuid.UUID,
) -> None:
    """Mark an enrichment record as having completed Pass 2.

    Appends '+pass2' to enrichment_version so fetch_pass1_complete_postings
    skips it. Prevents infinite re-processing of postings with no entities.
    """
    from sqlalchemy import select

    from compgraph.db.models import PostingEnrichment

    stmt = select(PostingEnrichment).where(PostingEnrichment.id == enrichment_id)
    result = await session.execute(stmt)
    enrichment = result.scalar_one_or_none()
    if enrichment:
        current = enrichment.enrichment_version or ""
        if "pass2" not in current:
            enrichment.enrichment_version = f"{current}+pass2" if current else "pass2"


class EnrichmentOrchestrator:
    """Orchestrates batch enrichment with concurrency control."""

    def __init__(
        self,
        batch_size: int | None = None,
        concurrency: int | None = None,
    ):
        self.batch_size = batch_size or settings.ENRICHMENT_BATCH_SIZE
        self.concurrency = concurrency or settings.ENRICHMENT_CONCURRENCY
        self.client = get_anthropic_client()

    async def run_pass1(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> EnrichResult:
        """Run Pass 1 enrichment on all unenriched postings.

        Processes in batches, with a semaphore limiting concurrent API calls.
        Each posting is isolated — one failure doesn't stop the batch.
        """
        run.status = EnrichmentStatus.RUNNING
        result = EnrichResult()
        semaphore = asyncio.Semaphore(self.concurrency)
        total_processed = 0
        failed_ids: set[uuid.UUID] = set()

        while True:
            async with async_session_factory() as session:
                batch = await fetch_unenriched_postings(
                    session,
                    company_id=company_id,
                    batch_size=self.batch_size,
                    exclude_ids=failed_ids,
                )

                if not batch:
                    break

                async def _process_posting(
                    posting_id: uuid.UUID,
                    snapshot_id: uuid.UUID,
                    title: str,
                    location: str,
                    full_text: str,
                ) -> tuple[bool, uuid.UUID]:
                    async with semaphore:
                        try:
                            pass1_result = await enrich_posting_pass1(
                                self.client,
                                posting_id,
                                title or "",
                                location or "",
                                full_text or "",
                            )
                            async with async_session_factory() as save_session:
                                await save_enrichment(
                                    save_session,
                                    posting_id,
                                    snapshot_id,
                                    pass1_result,
                                    model=settings.ENRICHMENT_MODEL_PASS1,
                                    version="pass1-v1",
                                )
                                await save_session.commit()
                            return True, posting_id
                        except Exception:
                            logger.exception("Pass 1 failed for posting %s", posting_id)
                            return False, posting_id

                tasks = [
                    _process_posting(
                        posting.id,
                        snapshot.id,
                        snapshot.title_raw or "",
                        snapshot.location_raw or "",
                        snapshot.full_text_raw or "",
                    )
                    for posting, snapshot in batch
                ]

                outcomes = await asyncio.gather(*tasks)
                for success, pid in outcomes:
                    if success:
                        result.succeeded += 1
                    else:
                        result.failed += 1
                        failed_ids.add(pid)

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 1 progress: %d processed (%d succeeded, %d failed)",
                        total_processed,
                        result.succeeded,
                        result.failed,
                    )

                # If batch was smaller than batch_size, we've exhausted all postings
                if len(batch) < self.batch_size:
                    break

        run.finish(result)
        return result

    async def run_pass2(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> EnrichResult:
        """Run Pass 2 entity extraction on all postings with Pass 1 but no Pass 2.

        For each posting: extract entities via Sonnet, resolve against Brand/Retailer
        tables, and create PostingBrandMention records.
        """
        run.status = EnrichmentStatus.RUNNING
        result = EnrichResult()
        semaphore = asyncio.Semaphore(self.concurrency)
        total_processed = 0

        while True:
            async with async_session_factory() as session:
                batch = await fetch_pass1_complete_postings(
                    session, company_id=company_id, batch_size=self.batch_size
                )

                if not batch:
                    break

                async def _process_posting_pass2(
                    posting_id: uuid.UUID,
                    enrichment_id: uuid.UUID,
                    title: str,
                    location: str,
                    content_role_specific: str | None,
                    full_text: str,
                ) -> bool:
                    async with semaphore:
                        try:
                            pass2_result = await enrich_posting_pass2(
                                self.client,
                                posting_id,
                                title,
                                location,
                                content_role_specific,
                                full_text,
                            )

                            async with async_session_factory() as save_session:
                                if pass2_result.entities:
                                    # Resolve each entity against dimension tables
                                    resolved = []
                                    for entity in pass2_result.entities:
                                        resolution = await resolve_entity(
                                            save_session,
                                            entity.entity_name,
                                            entity.entity_type,
                                        )
                                        resolved.append(resolution)

                                    # Save brand mentions and update enrichment
                                    await save_brand_mentions(
                                        save_session,
                                        posting_id,
                                        enrichment_id,
                                        pass2_result.entities,
                                        resolved,
                                    )

                                # Always mark Pass 2 complete on enrichment
                                # to prevent infinite re-processing of postings
                                # with no extractable entities
                                await _mark_pass2_complete(save_session, enrichment_id)
                                await save_session.commit()

                            return True
                        except Exception:
                            logger.exception("Pass 2 failed for posting %s", posting_id)
                            return False

                tasks = [
                    _process_posting_pass2(
                        posting.id,
                        enrichment.id,
                        snapshot.title_raw or "",
                        snapshot.location_raw or "",
                        enrichment.content_role_specific,
                        snapshot.full_text_raw or "",
                    )
                    for posting, snapshot, enrichment in batch
                ]

                outcomes = await asyncio.gather(*tasks)
                for success in outcomes:
                    if success:
                        result.succeeded += 1
                    else:
                        result.failed += 1

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 2 progress: %d processed (%d succeeded, %d failed)",
                        total_processed,
                        result.succeeded,
                        result.failed,
                    )

                if len(batch) < self.batch_size:
                    break

        run.finish_pass2(result)
        return result

    async def run_full(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> tuple[EnrichResult, EnrichResult]:
        """Run the full enrichment pipeline: Pass 1 → Pass 2 → Fingerprinting.

        Returns tuple of (pass1_result, pass2_result).
        """
        from compgraph.enrichment.fingerprint import detect_reposts

        pass1_result = await self.run_pass1(run, company_id=company_id)
        pass2_result = await self.run_pass2(run, company_id=company_id)

        # Run fingerprinting after entity resolution provides brand_slug
        try:
            async with async_session_factory() as session:
                reposts = await detect_reposts(session, company_id=company_id)
                await session.commit()
                logger.info("Fingerprinting complete: %d reposts detected", reposts)
        except Exception:
            logger.exception("Fingerprinting failed")
            # Downgrade status since pipeline didn't fully complete
            if run.status == EnrichmentStatus.SUCCESS:
                run.status = EnrichmentStatus.PARTIAL

        return pass1_result, pass2_result
