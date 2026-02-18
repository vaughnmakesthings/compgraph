"""Enrichment pipeline orchestrator — batch processing with concurrency control."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.config import settings
from compgraph.db.session import async_session_factory
from compgraph.enrichment.client import get_anthropic_client
from compgraph.enrichment.fingerprint import compute_content_hash
from compgraph.enrichment.pass1 import enrich_posting_pass1
from compgraph.enrichment.pass2 import enrich_posting_pass2
from compgraph.enrichment.queries import (
    fetch_pass1_complete_postings,
    fetch_unenriched_postings,
    save_enrichment,
)
from compgraph.enrichment.resolver import resolve_entity, save_brand_mentions
from compgraph.enrichment.schemas import Pass1Result, Pass2Result

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


# ---------------------------------------------------------------------------
# DB persistence (enrichment_runs table) — supplements in-memory state
# ---------------------------------------------------------------------------


async def create_enrichment_run_record(run_id: uuid.UUID) -> None:
    from compgraph.db.models import EnrichmentRunDB
    from compgraph.db.models import EnrichmentRunStatus as DBStatus

    async with async_session_factory() as session:
        db_run = EnrichmentRunDB(
            id=run_id,
            status=DBStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        session.add(db_run)
        await session.commit()


async def increment_enrichment_counter(
    run_id: uuid.UUID,
    **counters: int,
) -> None:
    from sqlalchemy import func, update

    from compgraph.db.models import EnrichmentRunDB

    values = {k: getattr(EnrichmentRunDB, k) + v for k, v in counters.items() if v != 0}
    if not values:
        return
    values["updated_at"] = func.now()
    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**values)
        )
        await session.commit()


async def update_enrichment_run_record(
    run_id: uuid.UUID,
    **fields: object,
) -> None:
    from sqlalchemy import update

    from compgraph.db.models import EnrichmentRunDB

    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**fields)
        )
        await session.commit()


async def get_latest_enrichment_run_from_db() -> dict | None:
    from sqlalchemy import select as sa_select

    from compgraph.db.models import EnrichmentRunDB

    async with async_session_factory() as session:
        stmt = sa_select(EnrichmentRunDB).order_by(EnrichmentRunDB.started_at.desc()).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "run_id": row.id,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "pass1_total": row.pass1_total,
            "pass1_succeeded": row.pass1_succeeded,
            "pass1_failed": row.pass1_failed,
            "pass1_skipped": row.pass1_skipped,
            "pass2_total": row.pass2_total,
            "pass2_succeeded": row.pass2_succeeded,
            "pass2_failed": row.pass2_failed,
            "pass2_skipped": row.pass2_skipped,
            "error_summary": row.error_summary,
        }


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
    """Orchestrates batch enrichment with concurrency control.

    Uses run-scoped content caching to deduplicate LLM calls for postings
    with identical content (e.g., same job posted to multiple cities).
    """

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
        *,
        finalize: bool = True,
    ) -> EnrichResult:
        """Run Pass 1 enrichment on all unenriched postings.

        Processes in batches, with a semaphore limiting concurrent API calls.
        Each posting is isolated — one failure doesn't stop the batch.
        Uses content-based deduplication to avoid redundant LLM calls for
        postings with identical title+body (e.g., same job in multiple cities).
        """
        run.status = EnrichmentStatus.RUNNING
        await create_enrichment_run_record(run.run_id)
        result = EnrichResult()
        semaphore = asyncio.Semaphore(self.concurrency)
        total_processed = 0
        failed_ids: set[uuid.UUID] = set()
        content_cache: dict[str, Pass1Result] = {}
        api_calls = 0

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

                # Group batch by content hash for deduplication
                groups: dict[str, list[tuple[uuid.UUID, uuid.UUID, str, str, str]]] = defaultdict(
                    list
                )
                for posting, snapshot in batch:
                    title = snapshot.title_raw or ""
                    full_text = snapshot.full_text_raw or ""
                    content_hash = compute_content_hash(title, full_text)
                    logger.debug(
                        "Content hash posting_id=%s hash=%s title=%.60s len=%d",
                        posting.id,
                        content_hash[:12],
                        title,
                        len(full_text),
                    )
                    groups[content_hash].append(
                        (posting.id, snapshot.id, title, snapshot.location_raw or "", full_text)
                    )

                unique_groups = len(groups)
                total_in_batch = len(batch)
                api_calls_before = api_calls
                logger.info(
                    "Pass 1 batch dedup: %d postings -> %d unique groups",
                    total_in_batch,
                    unique_groups,
                )

                async def _process_group(
                    content_hash: str,
                    group: list[tuple[uuid.UUID, uuid.UUID, str, str, str]],
                ) -> list[tuple[bool, uuid.UUID]]:
                    """Process a group of postings with identical content.

                    Calls the LLM once for the leader, then copies the result
                    to all followers in the group.
                    """
                    nonlocal api_calls

                    # Check run-scoped cache first
                    if content_hash in content_cache:
                        cached = content_cache[content_hash]
                        outcomes: list[tuple[bool, uuid.UUID]] = []
                        for posting_id, snapshot_id, *_ in group:
                            try:
                                logger.info(
                                    "Pass 1 cache hit: posting %s reusing result (hash=%s...)",
                                    posting_id,
                                    content_hash[:12],
                                )
                                async with async_session_factory() as save_session:
                                    await save_enrichment(
                                        save_session,
                                        posting_id,
                                        snapshot_id,
                                        cached,
                                        model=settings.ENRICHMENT_MODEL_PASS1,
                                        version="pass1-v1",
                                    )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                logger.exception(
                                    "Pass 1 failed saving cached result for posting %s",
                                    posting_id,
                                )
                                outcomes.append((False, posting_id))
                        return outcomes

                    # Cache miss — call LLM for the leader posting
                    leader_id, _leader_snap, leader_title, leader_location, leader_text = group[0]
                    logger.debug(
                        "Pass 1 cache miss: %s leader for hash=%s... (size=%d)",
                        leader_id,
                        content_hash[:12],
                        len(group),
                    )

                    async with semaphore:
                        try:
                            pass1_result = await enrich_posting_pass1(
                                self.client,
                                leader_id,
                                leader_title,
                                leader_location,
                                leader_text,
                            )
                            api_calls += 1
                        except Exception:
                            api_calls += 1  # Count the failed attempt
                            logger.warning(
                                "Pass 1 leader %s failed, fallback for %d followers (hash=%s...)",
                                leader_id,
                                len(group) - 1,
                                content_hash[:12],
                            )
                            # Release semaphore before fallback to avoid deadlock
                            leader_failed = True
                        else:
                            leader_failed = False

                    if leader_failed:
                        # Skip leader (already failed), process followers only
                        followers = group[1:]
                        follower_outcomes = await _fallback_individual(
                            followers,
                            content_hash,
                        )
                        return [(False, leader_id), *follower_outcomes]

                    # Cache the result for future batches within this run
                    content_cache[content_hash] = pass1_result

                    # Save for leader + all followers
                    outcomes = []
                    for i, (posting_id, snapshot_id, *_) in enumerate(group):
                        try:
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
                            if i > 0:
                                logger.debug(
                                    "Pass 1 follower: copied enrichment %s from leader %s",
                                    posting_id,
                                    leader_id,
                                )
                            outcomes.append((True, posting_id))
                        except Exception:
                            logger.exception(
                                "Pass 1 failed saving enrichment for posting %s", posting_id
                            )
                            outcomes.append((False, posting_id))
                    return outcomes

                async def _fallback_individual(
                    group: list[tuple[uuid.UUID, uuid.UUID, str, str, str]],
                    content_hash: str,
                ) -> list[tuple[bool, uuid.UUID]]:
                    """Process each posting individually when leader fails."""
                    nonlocal api_calls
                    cached_on_fallback = False
                    outcomes: list[tuple[bool, uuid.UUID]] = []
                    for posting_id, snapshot_id, title, location, full_text in group:
                        # Reuse cached result from first successful follower
                        if cached_on_fallback:
                            try:
                                logger.info(
                                    "Pass 1 fallback cache hit: reused for posting %s (hash=%s...)",
                                    posting_id,
                                    content_hash[:12],
                                )
                                async with async_session_factory() as save_session:
                                    await save_enrichment(
                                        save_session,
                                        posting_id,
                                        snapshot_id,
                                        content_cache[content_hash],
                                        model=settings.ENRICHMENT_MODEL_PASS1,
                                        version="pass1-v1",
                                    )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                logger.exception(
                                    "Pass 1 failed saving cached fallback for posting %s",
                                    posting_id,
                                )
                                outcomes.append((False, posting_id))
                            continue

                        async with semaphore:
                            try:
                                p1 = await enrich_posting_pass1(
                                    self.client,
                                    posting_id,
                                    title,
                                    location,
                                    full_text,
                                )
                                api_calls += 1
                                content_cache[content_hash] = p1
                                cached_on_fallback = True
                                async with async_session_factory() as save_session:
                                    await save_enrichment(
                                        save_session,
                                        posting_id,
                                        snapshot_id,
                                        p1,
                                        model=settings.ENRICHMENT_MODEL_PASS1,
                                        version="pass1-v1",
                                    )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                api_calls += 1  # Count failed follower attempt
                                logger.exception("Pass 1 failed for posting %s", posting_id)
                                outcomes.append((False, posting_id))
                    return outcomes

                # Process all groups concurrently
                group_tasks = [_process_group(ch, grp) for ch, grp in groups.items()]
                group_outcomes = await asyncio.gather(*group_tasks)

                for outcomes in group_outcomes:
                    for success, pid in outcomes:
                        if success:
                            result.succeeded += 1
                            await increment_enrichment_counter(run.run_id, pass1_succeeded=1)
                        else:
                            result.failed += 1
                            await increment_enrichment_counter(run.run_id, pass1_failed=1)
                            failed_ids.add(pid)

                # Track actual dedup savings (accounts for fallback paths)
                api_calls_this_batch = api_calls - api_calls_before
                actual_saved = total_in_batch - api_calls_this_batch
                result.skipped += max(0, actual_saved)

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 1 progress: %d processed (%d succeeded, %d failed, %d dedup saved)",
                        total_processed,
                        result.succeeded,
                        result.failed,
                        actual_saved,
                    )

                # If batch was smaller than batch_size, we've exhausted all postings
                if len(batch) < self.batch_size:
                    break

        logger.info(
            "Pass 1 done: %d total, %d API, %d dedup, %d failed. Cache: %d",
            result.succeeded + result.failed,
            api_calls,
            result.skipped,
            result.failed,
            len(content_cache),
        )
        run.finish(result)
        from compgraph.db.models import EnrichmentRunStatus as DBStatus

        update_fields: dict[str, object] = {
            "pass1_total": result.succeeded + result.failed + result.skipped,
            "pass1_skipped": result.skipped,
        }
        if finalize:
            update_fields["status"] = (
                DBStatus.COMPLETED
                if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)
                else DBStatus.FAILED
            )
            update_fields["finished_at"] = run.finished_at
        else:
            update_fields["status"] = DBStatus.RUNNING
        await update_enrichment_run_record(run.run_id, **update_fields)
        return result

    @staticmethod
    async def _resolve_and_save_pass2(
        save_session: AsyncSession,
        posting_id: uuid.UUID,
        enrichment_id: uuid.UUID,
        pass2_result: Pass2Result,
    ) -> None:
        """Resolve entities and save brand mentions for a single posting.

        Extracted to avoid duplicating entity resolution logic across
        cache-hit, leader+follower, and fallback code paths.
        """
        if pass2_result.entities:
            resolved = []
            for entity in pass2_result.entities:
                resolution = await resolve_entity(
                    save_session,
                    entity.entity_name,
                    entity.entity_type,
                )
                resolved.append(resolution)
            await save_brand_mentions(
                save_session,
                posting_id,
                enrichment_id,
                pass2_result.entities,
                resolved,
            )
        await _mark_pass2_complete(save_session, enrichment_id)

    async def run_pass2(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> EnrichResult:
        """Run Pass 2 entity extraction on all postings with Pass 1 but no Pass 2.

        For each posting: extract entities via Sonnet, resolve against Brand/Retailer
        tables, and create PostingBrandMention records.
        Uses content-based deduplication to avoid redundant LLM calls.
        """
        run.status = EnrichmentStatus.RUNNING
        from sqlalchemy import select as sa_select

        from compgraph.db.models import EnrichmentRunDB

        async with async_session_factory() as _check_session:
            _exists = await _check_session.execute(
                sa_select(EnrichmentRunDB.id).where(EnrichmentRunDB.id == run.run_id)
            )
            if _exists.scalar_one_or_none() is None:
                await create_enrichment_run_record(run.run_id)
        result = EnrichResult()
        semaphore = asyncio.Semaphore(self.concurrency)
        total_processed = 0
        failed_ids: set[uuid.UUID] = set()
        content_cache_p2: dict[str, Pass2Result] = {}
        api_calls = 0

        while True:
            async with async_session_factory() as session:
                batch = await fetch_pass1_complete_postings(
                    session,
                    company_id=company_id,
                    batch_size=self.batch_size,
                    exclude_ids=failed_ids,
                )

                if not batch:
                    break

                # Group batch by content hash for deduplication
                # Pass 2 uses content_role_specific (from Pass 1) if available
                groups: dict[
                    str,
                    list[tuple[uuid.UUID, uuid.UUID, str, str, str | None, str]],
                ] = defaultdict(list)
                for posting, snapshot, enrichment in batch:
                    title = snapshot.title_raw or ""
                    # Use the same text Pass 2 sends to the LLM
                    p2_text = enrichment.content_role_specific or snapshot.full_text_raw or ""
                    content_hash = compute_content_hash(title, p2_text)
                    logger.debug(
                        "Pass 2 content hash computed posting_id=%s hash=%s",
                        posting.id,
                        content_hash[:12],
                    )
                    groups[content_hash].append(
                        (
                            posting.id,
                            enrichment.id,
                            title,
                            snapshot.location_raw or "",
                            enrichment.content_role_specific,
                            snapshot.full_text_raw or "",
                        )
                    )

                unique_groups = len(groups)
                total_in_batch = len(batch)
                api_calls_before = api_calls
                logger.info(
                    "Pass 2 batch dedup: %d postings -> %d unique groups",
                    total_in_batch,
                    unique_groups,
                )

                async def _process_group_pass2(
                    content_hash: str,
                    group: list[tuple[uuid.UUID, uuid.UUID, str, str, str | None, str]],
                ) -> list[tuple[bool, uuid.UUID]]:
                    """Process a group of postings with identical content for Pass 2."""
                    nonlocal api_calls

                    # Check run-scoped cache first
                    if content_hash in content_cache_p2:
                        cached = content_cache_p2[content_hash]
                        outcomes: list[tuple[bool, uuid.UUID]] = []
                        for posting_id, enrichment_id, *_ in group:
                            try:
                                logger.info(
                                    "Pass 2 cache hit: posting %s reusing result (hash=%s...)",
                                    posting_id,
                                    content_hash[:12],
                                )
                                async with async_session_factory() as save_session:
                                    await self._resolve_and_save_pass2(
                                        save_session,
                                        posting_id,
                                        enrichment_id,
                                        cached,
                                    )
                                    if cached.entities:
                                        logger.debug(
                                            "Pass 2 copying %d entities to follower %s",
                                            len(cached.entities),
                                            posting_id,
                                        )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                logger.exception(
                                    "Pass 2 failed saving cached result for posting %s",
                                    posting_id,
                                )
                                outcomes.append((False, posting_id))
                        return outcomes

                    # Cache miss — call LLM for the leader
                    leader_id, _leader_eid, leader_title, leader_loc, leader_crs, leader_ft = group[
                        0
                    ]
                    logger.debug(
                        "Pass 2 cache miss: %s leader for hash=%s... (size=%d)",
                        leader_id,
                        content_hash[:12],
                        len(group),
                    )

                    async with semaphore:
                        try:
                            pass2_result = await enrich_posting_pass2(
                                self.client,
                                leader_id,
                                leader_title,
                                leader_loc,
                                leader_crs,
                                leader_ft,
                            )
                            api_calls += 1
                        except Exception:
                            api_calls += 1  # Count the failed attempt
                            logger.warning(
                                "Pass 2 leader %s failed, fallback for %d followers (hash=%s...)",
                                leader_id,
                                len(group) - 1,
                                content_hash[:12],
                            )
                            leader_failed = True
                        else:
                            leader_failed = False

                    if leader_failed:
                        followers = group[1:]
                        follower_outcomes = await _fallback_individual_pass2(
                            followers,
                            content_hash,
                        )
                        return [(False, leader_id), *follower_outcomes]

                    content_cache_p2[content_hash] = pass2_result

                    # Save for leader + all followers
                    outcomes = []
                    for i, (posting_id, enrichment_id, *_rest) in enumerate(group):
                        try:
                            async with async_session_factory() as save_session:
                                await self._resolve_and_save_pass2(
                                    save_session,
                                    posting_id,
                                    enrichment_id,
                                    pass2_result,
                                )
                                if i > 0 and pass2_result.entities:
                                    logger.debug(
                                        "Pass 2 copying %d entities from leader %s to %s",
                                        len(pass2_result.entities),
                                        leader_id,
                                        posting_id,
                                    )
                                await save_session.commit()
                            outcomes.append((True, posting_id))
                        except Exception:
                            logger.exception(
                                "Pass 2 failed saving enrichment for posting %s", posting_id
                            )
                            outcomes.append((False, posting_id))
                    return outcomes

                async def _fallback_individual_pass2(
                    group: list[tuple[uuid.UUID, uuid.UUID, str, str, str | None, str]],
                    content_hash: str,
                ) -> list[tuple[bool, uuid.UUID]]:
                    """Process each posting individually when leader fails."""
                    nonlocal api_calls
                    cached_on_fallback = False
                    outcomes: list[tuple[bool, uuid.UUID]] = []
                    for posting_id, enrichment_id, title, location, crs, full_text in group:
                        # Reuse cached result from first successful follower
                        if cached_on_fallback:
                            try:
                                logger.info(
                                    "Pass 2 fallback cache hit: reused for posting %s (hash=%s...)",
                                    posting_id,
                                    content_hash[:12],
                                )
                                async with async_session_factory() as save_session:
                                    await self._resolve_and_save_pass2(
                                        save_session,
                                        posting_id,
                                        enrichment_id,
                                        content_cache_p2[content_hash],
                                    )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                logger.exception(
                                    "Pass 2 failed saving cached fallback for posting %s",
                                    posting_id,
                                )
                                outcomes.append((False, posting_id))
                            continue

                        async with semaphore:
                            try:
                                p2 = await enrich_posting_pass2(
                                    self.client,
                                    posting_id,
                                    title,
                                    location,
                                    crs,
                                    full_text,
                                )
                                api_calls += 1
                                content_cache_p2[content_hash] = p2
                                cached_on_fallback = True
                                async with async_session_factory() as save_session:
                                    await self._resolve_and_save_pass2(
                                        save_session,
                                        posting_id,
                                        enrichment_id,
                                        p2,
                                    )
                                    await save_session.commit()
                                outcomes.append((True, posting_id))
                            except Exception:
                                api_calls += 1  # Count failed follower attempt
                                logger.exception("Pass 2 failed for posting %s", posting_id)
                                outcomes.append((False, posting_id))
                    return outcomes

                # Process all groups concurrently
                group_tasks = [_process_group_pass2(ch, grp) for ch, grp in groups.items()]
                group_outcomes = await asyncio.gather(*group_tasks)

                for outcomes in group_outcomes:
                    for success, pid in outcomes:
                        if success:
                            result.succeeded += 1
                            await increment_enrichment_counter(run.run_id, pass2_succeeded=1)
                        else:
                            result.failed += 1
                            await increment_enrichment_counter(run.run_id, pass2_failed=1)
                            failed_ids.add(pid)

                # Track actual dedup savings (accounts for fallback paths)
                api_calls_this_batch = api_calls - api_calls_before
                actual_saved = total_in_batch - api_calls_this_batch
                result.skipped += max(0, actual_saved)

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 2 progress: %d processed (%d succeeded, %d failed, %d dedup saved)",
                        total_processed,
                        result.succeeded,
                        result.failed,
                        actual_saved,
                    )

                if len(batch) < self.batch_size:
                    break

        logger.info(
            "Pass 2 done: %d total, %d API, %d dedup, %d failed. Cache: %d",
            result.succeeded + result.failed,
            api_calls,
            result.skipped,
            result.failed,
            len(content_cache_p2),
        )
        run.finish_pass2(result)
        from compgraph.db.models import EnrichmentRunStatus as DBStatus

        final_status = (
            DBStatus.COMPLETED
            if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)
            else DBStatus.FAILED
        )
        error_msg = None
        if run.status == EnrichmentStatus.FAILED:
            p1_failed = run.pass1_result.failed if run.pass1_result else 0
            error_msg = f"pass1: {p1_failed}fail, pass2: {result.failed}fail"
        await update_enrichment_run_record(
            run.run_id,
            pass2_total=result.succeeded + result.failed + result.skipped,
            pass2_skipped=result.skipped,
            status=final_status,
            finished_at=run.finished_at,
            error_summary=error_msg,
        )
        return result

    async def run_full(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> tuple[EnrichResult, EnrichResult]:
        """Run the full enrichment pipeline: Pass 1 -> Pass 2 -> Fingerprinting.

        Returns tuple of (pass1_result, pass2_result).
        """
        from compgraph.enrichment.fingerprint import detect_reposts

        pass1_result = await self.run_pass1(run, company_id=company_id, finalize=False)
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
