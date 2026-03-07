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

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


from compgraph.config import settings
from compgraph.db.session import async_session_factory
from compgraph.enrichment.client import get_anthropic_client
from compgraph.enrichment.constants import ENRICHMENT_VERSION_PASS2
from compgraph.enrichment.fingerprint import compute_content_hash
from compgraph.enrichment.pass1 import enrich_posting_pass1
from compgraph.enrichment.pass2 import enrich_posting_pass2
from compgraph.enrichment.queries import (
    fetch_pass1_complete_postings,
    fetch_unenriched_postings,
    save_enrichment,
)
from compgraph.enrichment.resolver import resolve_entity, save_brand_mentions
from compgraph.enrichment.retry import (
    API_FAILURE_CATEGORIES,
    EnrichmentAPIError,
    ErrorCategory,
)
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
    total_api_calls: int = 0
    total_dedup_saved: int = 0


@dataclass
class EnrichmentRun:
    """Tracks the state of an enrichment pipeline run."""

    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    pass1_result: EnrichResult | None = None
    pass2_result: EnrichResult | None = None
    circuit_breaker_tripped: bool = False
    error_summary: str | None = None

    def finish(self, result: EnrichResult, *, finalize: bool = True) -> None:
        self.pass1_result = result
        if finalize:
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
MAX_STORED_ENRICHMENT_RUNS = 10

# Advisory lock key for enrichment mutual exclusion.
# md5(b"compgraph-enrichment").digest()[:8] as signed bigint.
ENRICHMENT_ADVISORY_LOCK_KEY = -6_705_433_518_358_464_913


def _store_run(run: EnrichmentRun) -> None:
    _runs[run.run_id] = run
    if len(_runs) > MAX_STORED_ENRICHMENT_RUNS:
        oldest_id = min(_runs, key=lambda k: _runs[k].started_at)
        del _runs[oldest_id]


def get_enrichment_run(run_id: uuid.UUID) -> EnrichmentRun | None:
    return _runs.get(run_id)


def get_latest_enrichment_run() -> EnrichmentRun | None:
    if not _runs:
        return None
    return max(_runs.values(), key=lambda r: r.started_at)


# ---------------------------------------------------------------------------
# Circuit breaker — aborts batch loop on systemic API failures
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Tracks consecutive API failures to abort batch processing early.

    Only counts failures in API_FAILURE_CATEGORIES (rate limit, quota, transient).
    Parse errors and permanent errors do NOT trip the breaker since they indicate
    per-posting issues, not systemic API problems.
    """

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold
        self.consecutive_failures = 0
        self.tripped = False
        self.trip_reason: str | None = None

    def record_api_failure(self, category: ErrorCategory) -> None:
        """Record an API failure. Trips the breaker if threshold is reached."""
        if category in API_FAILURE_CATEGORIES:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.threshold:
                self.tripped = True
                self.trip_reason = (
                    f"{self.consecutive_failures} consecutive API failures (last: {category})"
                )

    def record_success(self) -> None:
        """Reset the failure counter on a successful API call."""
        self.consecutive_failures = 0


# Type aliases for group tuples
Pass1Group = list[tuple[uuid.UUID, uuid.UUID, str, str, str]]
Pass2Group = list[tuple[uuid.UUID, uuid.UUID, str, str, str | None, str]]


@dataclass
class _BatchState:
    result: EnrichResult
    breaker: CircuitBreaker
    semaphore: asyncio.Semaphore
    run: EnrichmentRun
    failed_ids: set[uuid.UUID]
    api_calls: int = 0


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
            "total_input_tokens": row.total_input_tokens,
            "total_output_tokens": row.total_output_tokens,
            "total_api_calls": row.total_api_calls,
            "total_dedup_saved": row.total_dedup_saved,
            "error_summary": row.error_summary,
            "circuit_breaker_tripped": (
                cb_val
                if (cb_val := getattr(row, "circuit_breaker_tripped", None)) is not None
                else bool(row.error_summary and "circuit breaker" in row.error_summary.lower())
            ),
        }


async def _mark_pass2_complete(
    session: AsyncSession,
    enrichment_id: uuid.UUID,
    entity_count: int = 0,
) -> None:
    """Mark an enrichment record as having completed Pass 2.

    Appends '+pass2' to enrichment_version so fetch_pass1_complete_postings
    skips it. Prevents infinite re-processing of postings with no entities.
    Records entity_count to distinguish empty extraction from not-yet-extracted.
    """
    from sqlalchemy import select

    from compgraph.db.models import PostingEnrichment

    stmt = select(PostingEnrichment).where(PostingEnrichment.id == enrichment_id)
    result = await session.execute(stmt)
    enrichment = result.scalar_one_or_none()
    if enrichment:
        current = enrichment.enrichment_version or ""
        if ENRICHMENT_VERSION_PASS2 not in current:
            enrichment.enrichment_version = (
                f"{current}+{ENRICHMENT_VERSION_PASS2}" if current else ENRICHMENT_VERSION_PASS2
            )
        enrichment.entity_count = entity_count

        try:
            from compgraph.enrichment.embeddings import generate_embedding

            title = enrichment.title_normalized or ""
            content = enrichment.content_role_specific or ""
            embed_text = f"{title} {content}".strip()
            if embed_text:
                embedding = await generate_embedding(embed_text)
                enrichment.embedding = embedding
        except Exception:
            logger.warning(
                "Failed to generate embedding for enrichment %s",
                enrichment_id,
                exc_info=True,
            )


class EnrichmentOrchestrator:
    """Orchestrates batch enrichment with concurrency control.

    Uses run-scoped content caching to deduplicate LLM calls for postings
    with identical content (e.g., same job posted to multiple cities).
    Includes a circuit breaker that aborts the batch loop when consecutive
    API failures indicate a systemic issue (quota exhaustion, rate limits).
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
        Includes a circuit breaker that aborts when consecutive API failures
        indicate systemic issues (e.g., quota exhaustion).
        """
        run.status = EnrichmentStatus.RUNNING
        await create_enrichment_run_record(run.run_id)
        state = _BatchState(
            result=EnrichResult(),
            breaker=CircuitBreaker(settings.ENRICHMENT_CIRCUIT_BREAKER_THRESHOLD),
            semaphore=asyncio.Semaphore(self.concurrency),
            run=run,
            failed_ids=set(),
        )
        total_processed = 0
        content_cache: dict[str, Pass1Result] = {}
        shutdown_interrupted = False

        # Import once outside the loop (deferred to avoid circular import at module level)
        from compgraph.main import shutdown_event

        while True:
            # Check for graceful shutdown signal
            if shutdown_event.is_set():
                logger.info("Pass 1 stopping early — shutdown signal received")
                shutdown_interrupted = True
                break

            async with async_session_factory() as session:
                batch = await fetch_unenriched_postings(
                    session,
                    company_id=company_id,
                    batch_size=self.batch_size,
                    exclude_ids=state.failed_ids,
                )

                if not batch:
                    break

                groups: dict[str, Pass1Group] = defaultdict(list)
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
                api_calls_before = state.api_calls
                logger.info(
                    "Pass 1 batch dedup: %d postings -> %d unique groups",
                    total_in_batch,
                    unique_groups,
                )

                group_tasks = [
                    self._process_group_pass1(state, content_cache, ch, grp)
                    for ch, grp in groups.items()
                ]
                await asyncio.gather(*group_tasks)

                if state.breaker.tripped:
                    logger.error(
                        "Pass 1 aborting: circuit breaker tripped — %s",
                        state.breaker.trip_reason,
                    )
                    break

                api_calls_this_batch = state.api_calls - api_calls_before
                actual_saved = total_in_batch - api_calls_this_batch
                state.result.skipped += max(0, actual_saved)

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 1 progress: %d processed (%d succeeded, %d failed, %d dedup saved)",
                        total_processed,
                        state.result.succeeded,
                        state.result.failed,
                        actual_saved,
                    )

                if len(batch) < self.batch_size:
                    break

        result = state.result
        result.total_api_calls = state.api_calls
        result.total_dedup_saved = result.skipped
        logger.info(
            "Pass 1 done: %d total, %d API, %d dedup, %d failed, %d in_tok, %d out_tok",
            result.succeeded + result.failed,
            state.api_calls,
            result.skipped,
            result.failed,
            result.total_input_tokens,
            result.total_output_tokens,
        )
        if shutdown_interrupted:
            run.error_summary = "interrupted by graceful shutdown"
        if state.breaker.tripped:
            run.circuit_breaker_tripped = True
            run.error_summary = f"circuit breaker triggered: {state.breaker.trip_reason}"
        run.finish(result, finalize=finalize)
        if shutdown_interrupted and run.status == EnrichmentStatus.SUCCESS:
            run.status = EnrichmentStatus.PARTIAL
        from compgraph.db.models import EnrichmentRunStatus as DBStatus

        update_fields: dict[str, object] = {
            "pass1_total": result.succeeded + result.failed + result.skipped,
            "pass1_skipped": result.skipped,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "total_api_calls": result.total_api_calls,
            "total_dedup_saved": result.total_dedup_saved,
        }
        if state.breaker.tripped:
            update_fields["circuit_breaker_tripped"] = True
        if finalize:
            update_fields["status"] = (
                DBStatus.COMPLETED
                if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)
                else DBStatus.FAILED
            )
            update_fields["finished_at"] = run.finished_at
            if shutdown_interrupted:
                update_fields["error_summary"] = "interrupted by graceful shutdown"
            if state.breaker.tripped:
                update_fields["error_summary"] = (
                    f"circuit breaker triggered: {state.breaker.trip_reason}"
                )
        else:
            update_fields["status"] = DBStatus.RUNNING
        await update_enrichment_run_record(run.run_id, **update_fields)
        return result

    async def _process_group_pass1(
        self,
        state: _BatchState,
        content_cache: dict[str, Pass1Result],
        content_hash: str,
        group: Pass1Group,
    ) -> None:
        """Process a dedup group for Pass 1.

        Call LLM once, apply result to all postings in the group.
        """
        if state.breaker.tripped:
            return

        if content_hash in content_cache:
            cached = content_cache[content_hash]
            for posting_id, snapshot_id, title, *_ in group:
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
                            title_raw=title,
                        )
                        await save_session.commit()
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass1_succeeded=1)
                except Exception:
                    logger.exception(
                        "Pass 1 failed saving cached result for posting %s",
                        posting_id,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass1_failed=1)
            return

        leader_id, _leader_snap, leader_title, leader_location, leader_text = group[0]
        logger.debug(
            "Pass 1 cache miss: %s leader for hash=%s... (size=%d)",
            leader_id,
            content_hash[:12],
            len(group),
        )

        async with state.semaphore:
            if state.breaker.tripped:
                return

            try:
                llm_result = await enrich_posting_pass1(
                    self.client,
                    leader_id,
                    leader_title,
                    leader_location,
                    leader_text,
                )
                state.api_calls += 1
                pass1_result = llm_result.result
                state.result.total_input_tokens += llm_result.input_tokens
                state.result.total_output_tokens += llm_result.output_tokens
                state.breaker.record_success()
            except EnrichmentAPIError as e:
                state.api_calls += 1
                state.breaker.record_api_failure(e.category)
                if state.breaker.tripped:
                    logger.error(
                        "Circuit breaker tripped during Pass 1: %s",
                        state.breaker.trip_reason,
                    )
                logger.warning(
                    "Pass 1 leader %s failed (%s), fallback for %d followers (hash=%s...)",
                    leader_id,
                    e.category,
                    len(group) - 1,
                    content_hash[:12],
                )
                leader_failed = True
            except Exception:
                state.api_calls += 1
                logger.warning(
                    "Pass 1 leader %s failed, fallback for %d followers (hash=%s...)",
                    leader_id,
                    len(group) - 1,
                    content_hash[:12],
                )
                leader_failed = True
            else:
                leader_failed = False

        if leader_failed:
            state.result.failed += 1
            state.failed_ids.add(leader_id)
            await increment_enrichment_counter(state.run.run_id, pass1_failed=1)
            if state.breaker.tripped:
                return
            followers = group[1:]
            await self._fallback_individual_pass1(
                state,
                content_cache,
                content_hash,
                followers,
            )
            return

        content_cache[content_hash] = pass1_result

        for i, (posting_id, snapshot_id, title, *_) in enumerate(group):
            try:
                async with async_session_factory() as save_session:
                    await save_enrichment(
                        save_session,
                        posting_id,
                        snapshot_id,
                        pass1_result,
                        model=settings.ENRICHMENT_MODEL_PASS1,
                        version="pass1-v1",
                        title_raw=title,
                    )
                    await save_session.commit()
                if i > 0:
                    logger.debug(
                        "Pass 1 follower: copied enrichment %s from leader %s",
                        posting_id,
                        leader_id,
                    )
                state.result.succeeded += 1
                await increment_enrichment_counter(state.run.run_id, pass1_succeeded=1)
            except Exception:
                logger.exception("Pass 1 failed saving enrichment for posting %s", posting_id)
                state.result.failed += 1
                state.failed_ids.add(posting_id)
                await increment_enrichment_counter(state.run.run_id, pass1_failed=1)

    async def _fallback_individual_pass1(
        self,
        state: _BatchState,
        content_cache: dict[str, Pass1Result],
        content_hash: str,
        group: Pass1Group,
    ) -> None:
        """Fallback for Pass 1.

        Process each posting individually after group call fails.
        """
        cached_on_fallback = False
        for posting_id, snapshot_id, title, location, full_text in group:
            if state.breaker.tripped:
                break

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
                            title_raw=title,
                        )
                        await save_session.commit()
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass1_succeeded=1)
                except Exception:
                    logger.exception(
                        "Pass 1 failed saving cached fallback for posting %s",
                        posting_id,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass1_failed=1)
                continue

            async with state.semaphore:
                if state.breaker.tripped:
                    break
                try:
                    llm_result = await enrich_posting_pass1(
                        self.client,
                        posting_id,
                        title,
                        location,
                        full_text,
                    )
                    state.api_calls += 1
                    p1 = llm_result.result
                    state.result.total_input_tokens += llm_result.input_tokens
                    state.result.total_output_tokens += llm_result.output_tokens
                    state.breaker.record_success()
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
                            title_raw=title,
                        )
                        await save_session.commit()
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass1_succeeded=1)
                except EnrichmentAPIError as e:
                    state.api_calls += 1
                    state.breaker.record_api_failure(e.category)
                    if state.breaker.tripped:
                        logger.error(
                            "Circuit breaker tripped during Pass 1 fallback: %s",
                            state.breaker.trip_reason,
                        )
                    logger.exception(
                        "Pass 1 failed for posting %s (%s)",
                        posting_id,
                        e.category,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass1_failed=1)
                except Exception:
                    state.api_calls += 1
                    logger.exception("Pass 1 failed for posting %s", posting_id)
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass1_failed=1)

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
        entity_count = len(pass2_result.entities)
        await _mark_pass2_complete(save_session, enrichment_id, entity_count=entity_count)

    async def run_pass2(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> EnrichResult:
        """Run Pass 2 entity extraction on all postings with Pass 1 but no Pass 2.

        For each posting: extract entities via Sonnet, resolve against Brand/Retailer
        tables, and create PostingBrandMention records.
        Uses content-based deduplication to avoid redundant LLM calls.
        Includes a circuit breaker that aborts when consecutive API failures
        indicate systemic issues.
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
        state = _BatchState(
            result=EnrichResult(),
            breaker=CircuitBreaker(settings.ENRICHMENT_CIRCUIT_BREAKER_THRESHOLD),
            semaphore=asyncio.Semaphore(self.concurrency),
            run=run,
            failed_ids=set(),
        )
        total_processed = 0
        content_cache_p2: dict[str, Pass2Result] = {}
        shutdown_interrupted = False

        # Import once outside the loop (deferred to avoid circular import at module level)
        from compgraph.main import shutdown_event

        while True:
            # Check for graceful shutdown signal
            if shutdown_event.is_set():
                logger.info("Pass 2 stopping early — shutdown signal received")
                shutdown_interrupted = True
                break

            async with async_session_factory() as session:
                batch = await fetch_pass1_complete_postings(
                    session,
                    company_id=company_id,
                    batch_size=self.batch_size,
                    exclude_ids=state.failed_ids,
                )

                if not batch:
                    break

                groups: dict[str, Pass2Group] = defaultdict(list)
                for posting, snapshot, enrichment in batch:
                    title = snapshot.title_raw or ""
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
                api_calls_before = state.api_calls
                logger.info(
                    "Pass 2 batch dedup: %d postings -> %d unique groups",
                    total_in_batch,
                    unique_groups,
                )

                group_tasks = [
                    self._process_group_pass2(state, content_cache_p2, ch, grp)
                    for ch, grp in groups.items()
                ]
                await asyncio.gather(*group_tasks)

                if state.breaker.tripped:
                    logger.error(
                        "Pass 2 aborting: circuit breaker tripped — %s",
                        state.breaker.trip_reason,
                    )
                    break

                api_calls_this_batch = state.api_calls - api_calls_before
                actual_saved = total_in_batch - api_calls_this_batch
                state.result.skipped += max(0, actual_saved)

                total_processed += len(batch)
                if total_processed % 10 == 0 or len(batch) < self.batch_size:
                    logger.info(
                        "Pass 2 progress: %d processed (%d succeeded, %d failed, %d dedup saved)",
                        total_processed,
                        state.result.succeeded,
                        state.result.failed,
                        actual_saved,
                    )

                if len(batch) < self.batch_size:
                    break

        result = state.result
        result.total_api_calls = state.api_calls
        result.total_dedup_saved = result.skipped
        logger.info(
            "Pass 2 done: %d total, %d API, %d dedup, %d failed, %d in_tok, %d out_tok",
            result.succeeded + result.failed,
            state.api_calls,
            result.skipped,
            result.failed,
            result.total_input_tokens,
            result.total_output_tokens,
        )
        if shutdown_interrupted:
            run.error_summary = "interrupted by graceful shutdown"
        if state.breaker.tripped:
            run.circuit_breaker_tripped = True
            run.error_summary = f"circuit breaker triggered: {state.breaker.trip_reason}"
        run.finish_pass2(result)
        if shutdown_interrupted and run.status == EnrichmentStatus.SUCCESS:
            run.status = EnrichmentStatus.PARTIAL
        from compgraph.db.models import EnrichmentRunStatus as DBStatus

        final_status = (
            DBStatus.COMPLETED
            if run.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)
            else DBStatus.FAILED
        )
        error_msg = run.error_summary
        if not error_msg and run.status == EnrichmentStatus.FAILED:
            p1_failed = run.pass1_result.failed if run.pass1_result else 0
            error_msg = f"pass1: {p1_failed}fail, pass2: {result.failed}fail"

        p1 = run.pass1_result
        total_in = result.total_input_tokens + (p1.total_input_tokens if p1 else 0)
        total_out = result.total_output_tokens + (p1.total_output_tokens if p1 else 0)
        total_api = result.total_api_calls + (p1.total_api_calls if p1 else 0)
        total_dedup = result.total_dedup_saved + (p1.total_dedup_saved if p1 else 0)

        await update_enrichment_run_record(
            run.run_id,
            pass2_total=result.succeeded + result.failed + result.skipped,
            pass2_skipped=result.skipped,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_api_calls=total_api,
            total_dedup_saved=total_dedup,
            status=final_status,
            finished_at=run.finished_at,
            error_summary=error_msg,
            circuit_breaker_tripped=run.circuit_breaker_tripped,
        )
        return result

    async def _process_group_pass2(
        self,
        state: _BatchState,
        content_cache: dict[str, Pass2Result],
        content_hash: str,
        group: Pass2Group,
    ) -> None:
        """Process a dedup group for Pass 2.

        Call LLM once, resolve entities and save mentions for all postings.
        """
        if state.breaker.tripped:
            return

        if content_hash in content_cache:
            cached = content_cache[content_hash]
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
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass2_succeeded=1)
                except Exception:
                    logger.exception(
                        "Pass 2 failed saving cached result for posting %s",
                        posting_id,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass2_failed=1)
            return

        leader_id, _leader_eid, leader_title, leader_loc, leader_crs, leader_ft = group[0]
        logger.debug(
            "Pass 2 cache miss: %s leader for hash=%s... (size=%d)",
            leader_id,
            content_hash[:12],
            len(group),
        )

        async with state.semaphore:
            if state.breaker.tripped:
                return

            try:
                llm_result = await enrich_posting_pass2(
                    self.client,
                    leader_id,
                    leader_title,
                    leader_loc,
                    leader_crs,
                    leader_ft,
                )
                state.api_calls += 1
                pass2_result = llm_result.result
                state.result.total_input_tokens += llm_result.input_tokens
                state.result.total_output_tokens += llm_result.output_tokens
                state.breaker.record_success()
            except EnrichmentAPIError as e:
                state.api_calls += 1
                state.breaker.record_api_failure(e.category)
                if state.breaker.tripped:
                    logger.error(
                        "Circuit breaker tripped during Pass 2: %s",
                        state.breaker.trip_reason,
                    )
                logger.warning(
                    "Pass 2 leader %s failed (%s), fallback for %d followers (hash=%s...)",
                    leader_id,
                    e.category,
                    len(group) - 1,
                    content_hash[:12],
                )
                leader_failed = True
            except Exception:
                state.api_calls += 1
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
            state.result.failed += 1
            state.failed_ids.add(leader_id)
            await increment_enrichment_counter(state.run.run_id, pass2_failed=1)
            if state.breaker.tripped:
                return
            followers = group[1:]
            await self._fallback_individual_pass2(
                state,
                content_cache,
                content_hash,
                followers,
            )
            return

        content_cache[content_hash] = pass2_result

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
                state.result.succeeded += 1
                await increment_enrichment_counter(state.run.run_id, pass2_succeeded=1)
            except Exception:
                logger.exception("Pass 2 failed saving enrichment for posting %s", posting_id)
                state.result.failed += 1
                state.failed_ids.add(posting_id)
                await increment_enrichment_counter(state.run.run_id, pass2_failed=1)

    async def _fallback_individual_pass2(
        self,
        state: _BatchState,
        content_cache: dict[str, Pass2Result],
        content_hash: str,
        group: Pass2Group,
    ) -> None:
        """Fallback for Pass 2: process each posting individually after group call fails."""
        cached_on_fallback = False
        for posting_id, enrichment_id, title, location, crs, full_text in group:
            if state.breaker.tripped:
                break

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
                            content_cache[content_hash],
                        )
                        await save_session.commit()
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass2_succeeded=1)
                except Exception:
                    logger.exception(
                        "Pass 2 failed saving cached fallback for posting %s",
                        posting_id,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass2_failed=1)
                continue

            async with state.semaphore:
                if state.breaker.tripped:
                    break
                try:
                    llm_result = await enrich_posting_pass2(
                        self.client,
                        posting_id,
                        title,
                        location,
                        crs,
                        full_text,
                    )
                    state.api_calls += 1
                    p2 = llm_result.result
                    state.result.total_input_tokens += llm_result.input_tokens
                    state.result.total_output_tokens += llm_result.output_tokens
                    state.breaker.record_success()
                    content_cache[content_hash] = p2
                    cached_on_fallback = True
                    async with async_session_factory() as save_session:
                        await self._resolve_and_save_pass2(
                            save_session,
                            posting_id,
                            enrichment_id,
                            p2,
                        )
                        await save_session.commit()
                    state.result.succeeded += 1
                    await increment_enrichment_counter(state.run.run_id, pass2_succeeded=1)
                except EnrichmentAPIError as e:
                    state.api_calls += 1
                    state.breaker.record_api_failure(e.category)
                    if state.breaker.tripped:
                        logger.error(
                            "Circuit breaker tripped during Pass 2 fallback: %s",
                            state.breaker.trip_reason,
                        )
                    logger.exception(
                        "Pass 2 failed for posting %s (%s)",
                        posting_id,
                        e.category,
                    )
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass2_failed=1)
                except Exception:
                    state.api_calls += 1
                    logger.exception("Pass 2 failed for posting %s", posting_id)
                    state.result.failed += 1
                    state.failed_ids.add(posting_id)
                    await increment_enrichment_counter(state.run.run_id, pass2_failed=1)

    async def run_full(
        self,
        run: EnrichmentRun,
        company_id: uuid.UUID | None = None,
    ) -> tuple[EnrichResult, EnrichResult]:
        """Run the full enrichment pipeline: Pass 1 -> Pass 2 -> Fingerprinting.

        Returns tuple of (pass1_result, pass2_result).
        """

        from compgraph.enrichment.fingerprint import detect_reposts

        # Acquire transaction-scoped advisory lock for mutual exclusion.
        # Uses pg_try_advisory_xact_lock (non-blocking): returns false immediately
        # if another enrichment run holds the lock, instead of waiting.
        # The lock auto-releases when the transaction ends (session context exit),
        # which is safe with connection pooling (unlike session-level locks).
        async with async_session_factory() as lock_session:
            result = await lock_session.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": ENRICHMENT_ADVISORY_LOCK_KEY},
            )
            acquired = result.scalar()

            if not acquired:
                logger.warning(
                    "Enrichment run %s skipped — another run holds the advisory lock",
                    run.run_id,
                )
                run.status = EnrichmentStatus.FAILED
                run.finished_at = datetime.now(UTC)
                run.error_summary = "Skipped: concurrent enrichment run in progress"
                return EnrichResult(), EnrichResult()

            logger.info("Advisory lock acquired for enrichment run %s", run.run_id)

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
                if run.status == EnrichmentStatus.SUCCESS:
                    run.status = EnrichmentStatus.PARTIAL

            return pass1_result, pass2_result
