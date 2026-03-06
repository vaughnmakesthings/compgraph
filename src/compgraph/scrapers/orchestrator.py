"""Pipeline orchestrator: coordinates scrape runs across all companies with error isolation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from compgraph.config import settings
from compgraph.db.models import Company, Posting, ScrapeRun, ScrapeRunStatus
from compgraph.db.session import async_session_factory
from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.deactivation import deactivate_stale_postings
from compgraph.scrapers.registry import get_adapter

logger = logging.getLogger(__name__)


class PipelineStatus(StrEnum):
    """Overall status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CompanyState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class PipelineRun:
    """Tracks the state and results of a single pipeline run."""

    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    company_results: dict[str, ScrapeResult] = field(default_factory=dict)
    company_states: dict[str, CompanyState] = field(default_factory=dict)

    @property
    def total_postings_found(self) -> int:
        return sum(r.postings_found for r in self.company_results.values())

    @property
    def total_snapshots_created(self) -> int:
        return sum(r.snapshots_created for r in self.company_results.values())

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.company_results.values())

    @property
    def companies_succeeded(self) -> int:
        return sum(1 for r in self.company_results.values() if r.success)

    @property
    def companies_failed(self) -> int:
        return sum(1 for r in self.company_results.values() if not r.success)


# In-memory store for pipeline runs. Retains last MAX_STORED_RUNS.
MAX_STORED_RUNS = 10
_pipeline_runs: dict[uuid.UUID, PipelineRun] = {}

# In-memory store for active orchestrators (keyed by run_id).
# Populated by API layer when triggering runs, cleaned up on run completion.
_pipeline_orchestrators: dict[uuid.UUID, object] = {}  # values are PipelineOrchestrator


def _store_run(run: PipelineRun) -> None:
    """Store a pipeline run, evicting oldest if over limit."""
    _pipeline_runs[run.run_id] = run
    if len(_pipeline_runs) > MAX_STORED_RUNS:
        oldest_id = min(_pipeline_runs, key=lambda k: _pipeline_runs[k].started_at)
        del _pipeline_runs[oldest_id]


def get_latest_run() -> PipelineRun | None:
    """Return the most recent pipeline run, or None."""
    if not _pipeline_runs:
        return None
    return max(_pipeline_runs.values(), key=lambda r: r.started_at)


def get_run(run_id: uuid.UUID) -> PipelineRun | None:
    """Return a specific pipeline run by ID."""
    return _pipeline_runs.get(run_id)


def get_all_runs() -> list[PipelineRun]:
    """Return all stored pipeline runs, most recent first."""
    return sorted(_pipeline_runs.values(), key=lambda r: r.started_at, reverse=True)


def get_orchestrator(run_id: uuid.UUID) -> PipelineOrchestrator | None:
    """Return the orchestrator for an active run, or None."""
    orch = _pipeline_orchestrators.get(run_id)
    if orch is not None and isinstance(orch, PipelineOrchestrator):
        return orch
    return None


BASELINE_LOOKBACK = 7
BASELINE_DROP_THRESHOLD = 0.50


async def check_baseline_anomaly(
    session: AsyncSession,
    company_id: uuid.UUID,
    current_jobs_found: int,
    exclude_run_id: uuid.UUID | None = None,
) -> list[str]:
    """Compare current scrape against historical baseline.

    Returns warning messages if current count is zero with history,
    or drops >BASELINE_DROP_THRESHOLD below the rolling average.
    """
    stmt = select(ScrapeRun.jobs_found).where(
        ScrapeRun.company_id == company_id,
        ScrapeRun.status == ScrapeRunStatus.COMPLETED,
    )
    if exclude_run_id is not None:
        stmt = stmt.where(ScrapeRun.id != exclude_run_id)
    stmt = stmt.order_by(ScrapeRun.completed_at.desc()).limit(BASELINE_LOOKBACK)
    result = await session.execute(stmt)
    historical_counts = list(result.scalars().all())

    if not historical_counts:
        return []

    baseline_avg = sum(historical_counts) / len(historical_counts)

    warnings: list[str] = []

    if current_jobs_found == 0 and baseline_avg > 0:
        msg = (
            f"Zero results detected: found 0 postings but baseline average "
            f"is {baseline_avg:.1f} (last {len(historical_counts)} runs). "
            f"The career site may have changed."
        )
        logger.warning(msg)
        warnings.append(msg)
    elif baseline_avg > 0 and current_jobs_found < baseline_avg * BASELINE_DROP_THRESHOLD:
        msg = (
            f"Significant drop detected: found {current_jobs_found} postings "
            f"but baseline average is {baseline_avg:.1f} "
            f"(>{BASELINE_DROP_THRESHOLD:.0%} below baseline). "
            f"The career site may have changed."
        )
        logger.warning(msg)
        warnings.append(msg)

    return warnings


async def _count_active_postings(session: AsyncSession, company_id: uuid.UUID) -> int:
    """Return the current count of active postings for a company."""
    result = await session.execute(
        select(func.count())
        .select_from(Posting)
        .where(
            Posting.company_id == company_id,
            Posting.is_active.is_(True),
        )
    )
    count: int = result.scalar_one()
    return count


async def cleanup_stale_pending_runs(session: AsyncSession, max_age_hours: int = 6) -> int:
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    stmt = (
        update(ScrapeRun)
        .where(
            ScrapeRun.status == ScrapeRunStatus.PENDING,
            ScrapeRun.started_at < cutoff,
        )
        .values(
            status=ScrapeRunStatus.FAILED,
            completed_at=func.now(),
            errors={"errors": ["Cleaned up stale PENDING run"], "warnings": []},
        )
    )
    result = await session.execute(stmt)
    await session.commit()
    count: int = result.rowcount  # type: ignore[attr-defined]
    return count


class PipelineOrchestrator:
    """Coordinates scrape runs across all companies with error isolation.

    Usage:
        orchestrator = PipelineOrchestrator()
        run = await orchestrator.run()
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_base_delay: float = 30.0,
        max_concurrency: int = 4,
    ):
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._resume_event = asyncio.Event()
        self._resume_event.set()  # not paused initially
        self._stop_requested = False
        self._force_stop_requested = False
        self._tasks: list[asyncio.Task] = []

    def pause(self, run: PipelineRun) -> None:
        """Pause the pipeline. Companies already scraping will finish their current page."""
        self._resume_event.clear()
        run.status = PipelineStatus.PAUSED

    def resume(self, run: PipelineRun) -> None:
        """Resume a paused pipeline."""
        self._resume_event.set()
        run.status = PipelineStatus.RUNNING

    def stop(self, run: PipelineRun) -> None:
        self._stop_requested = True
        self._resume_event.set()
        run.status = PipelineStatus.STOPPING
        for slug in run.company_states:
            if run.company_states[slug] == CompanyState.PENDING:
                run.company_states[slug] = CompanyState.SKIPPED

    def force_stop(self, run: PipelineRun) -> None:
        self._force_stop_requested = True
        self._stop_requested = True
        self._resume_event.set()
        for task in self._tasks:
            task.cancel()
        run.status = PipelineStatus.CANCELLED
        _NON_TERMINAL = {CompanyState.PENDING, CompanyState.RUNNING}
        for slug in run.company_states:
            if run.company_states[slug] in _NON_TERMINAL:
                run.company_states[slug] = CompanyState.CANCELLED

    async def run(self, pipeline_run: PipelineRun | None = None) -> PipelineRun:
        """Execute a full scrape pipeline run.

        Args:
            pipeline_run: Optional pre-created run (used by API trigger endpoint).
                If None, a new PipelineRun is created.
        """
        if pipeline_run is None:
            pipeline_run = PipelineRun()

        pipeline_run.status = PipelineStatus.RUNNING
        _store_run(pipeline_run)

        try:
            async with async_session_factory() as session:
                companies = await self._fetch_companies(session)

            if not companies:
                logger.warning("No companies found in database")
                pipeline_run.status = PipelineStatus.SUCCESS
                pipeline_run.finished_at = datetime.now(UTC)
                return pipeline_run

            # Initialize per-company states
            for company in companies:
                pipeline_run.company_states[company.slug] = CompanyState.PENDING

            self._tasks = [
                asyncio.create_task(
                    self._scrape_company_with_isolation(company, pipeline_run),
                    name=f"scrape-{company.slug}",
                )
                for company in companies
            ]
            results = await asyncio.gather(*self._tasks, return_exceptions=True)

            for company, result in zip(companies, results, strict=True):
                if isinstance(result, BaseException):
                    is_cancelled = isinstance(result, asyncio.CancelledError)
                    error_result = ScrapeResult(
                        company_id=company.id,
                        company_slug=company.slug,
                        errors=[
                            "Cancelled: pipeline force-stop"
                            if is_cancelled
                            else f"Unhandled exception: {result!r}"
                        ],
                        finished_at=datetime.now(UTC),
                    )
                    pipeline_run.company_results[company.slug] = error_result
                    pipeline_run.company_states[company.slug] = (
                        CompanyState.CANCELLED if is_cancelled else CompanyState.FAILED
                    )
                    if not is_cancelled:
                        logger.error("Unhandled exception scraping %s: %r", company.slug, result)
                else:
                    pipeline_run.company_results[company.slug] = result

            # Determine final status
            if self._stop_requested or self._force_stop_requested:
                pipeline_run.status = PipelineStatus.CANCELLED
            elif pipeline_run.companies_failed == 0:
                pipeline_run.status = PipelineStatus.SUCCESS
            elif pipeline_run.companies_succeeded == 0:
                pipeline_run.status = PipelineStatus.FAILED
            else:
                pipeline_run.status = PipelineStatus.PARTIAL

        except Exception as exc:
            logger.exception("Pipeline run failed catastrophically: %r", exc)
            pipeline_run.status = PipelineStatus.FAILED

        pipeline_run.finished_at = datetime.now(UTC)

        logger.info(
            "Pipeline run %s completed: status=%s, companies=%d/%d succeeded, "
            "postings=%d, snapshots=%d, errors=%d",
            pipeline_run.run_id,
            pipeline_run.status.value,
            pipeline_run.companies_succeeded,
            len(pipeline_run.company_results),
            pipeline_run.total_postings_found,
            pipeline_run.total_snapshots_created,
            pipeline_run.total_errors,
        )

        return pipeline_run

    async def _fetch_companies(self, session: AsyncSession) -> list[Company]:
        """Fetch all companies from the database."""
        result = await session.execute(select(Company))
        return list(result.scalars().all())

    async def _scrape_company_with_isolation(
        self, company: Company, pipeline_run: PipelineRun
    ) -> ScrapeResult:
        try:
            await self._resume_event.wait()

            if self._stop_requested:
                pipeline_run.company_states[company.slug] = CompanyState.SKIPPED
                return ScrapeResult(
                    company_id=company.id,
                    company_slug=company.slug,
                    errors=["Skipped: pipeline stop requested"],
                    finished_at=datetime.now(UTC),
                )

            pipeline_run.company_states[company.slug] = CompanyState.RUNNING

            async with self.semaphore:
                if self._stop_requested:
                    pipeline_run.company_states[company.slug] = CompanyState.SKIPPED
                    return ScrapeResult(
                        company_id=company.id,
                        company_slug=company.slug,
                        errors=["Skipped: pipeline stop requested"],
                        finished_at=datetime.now(UTC),
                    )

                scrape_run = await self._create_scrape_run(company)

                result: ScrapeResult | None = None
                try:
                    result = await self._scrape_with_retries(company)
                except BaseException as exc:
                    result = ScrapeResult(
                        company_id=company.id,
                        company_slug=company.slug,
                        errors=[f"Unexpected exception: {exc!r}"],
                        finished_at=datetime.now(UTC),
                    )
                    raise
                finally:
                    if scrape_run is not None and result is None:
                        result = ScrapeResult(
                            company_id=company.id,
                            company_slug=company.slug,
                            errors=["Scrape interrupted before completion"],
                            finished_at=datetime.now(UTC),
                        )
                    if result is not None:
                        pipeline_run.company_states[company.slug] = (
                            CompanyState.COMPLETED if result.success else CompanyState.FAILED
                        )
                        pipeline_run.company_results[company.slug] = result
                        try:
                            await asyncio.shield(self._finalize_scrape_run(scrape_run, result))
                        except asyncio.CancelledError:
                            pass

                return result
        except asyncio.CancelledError:
            if pipeline_run.company_states.get(company.slug) in (
                CompanyState.PENDING,
                CompanyState.RUNNING,
            ):
                pipeline_run.company_states[company.slug] = CompanyState.CANCELLED
            raise

    async def _create_scrape_run(self, company: Company) -> ScrapeRun | None:
        try:
            async with async_session_factory() as session:
                scrape_run = ScrapeRun(
                    company_id=company.id,
                    started_at=datetime.now(UTC),
                    status=ScrapeRunStatus.PENDING,
                )
                session.add(scrape_run)
                await session.commit()
                await session.refresh(scrape_run)
                return scrape_run
        except (IntegrityError, OperationalError) as exc:
            logger.error(
                "Database integrity/connection error creating ScrapeRun for %s: %r",
                company.slug,
                exc,
            )
            return None
        except Exception:
            logger.warning(
                "Non-critical failure creating ScrapeRun for %s, "
                "scrape will proceed without tracking",
                company.slug,
                exc_info=True,
            )
            return None

    async def _finalize_scrape_run(
        self, scrape_run: ScrapeRun | None, result: ScrapeResult
    ) -> None:
        if scrape_run is None:
            return
        try:
            async with async_session_factory() as session:
                refreshed = await session.get(ScrapeRun, scrape_run.id)
                if refreshed is None:
                    logger.error(
                        "ScrapeRun %s not found in DB during finalization for %s",
                        scrape_run.id,
                        result.company_slug,
                    )
                    return
                refreshed.completed_at = datetime.now(UTC)
                refreshed.jobs_found = result.postings_found
                refreshed.snapshots_created = result.snapshots_created
                refreshed.pages_scraped = result.pages_scraped
                if result.success:
                    refreshed.status = ScrapeRunStatus.COMPLETED
                    company = await session.get(Company, result.company_id)
                    if company:
                        company.last_scraped_at = datetime.now(UTC)

                    # Completeness gate: compare new postings against baseline to prevent
                    # false deactivation when a partial scrape returns fewer results.
                    baseline_count = await _count_active_postings(session, result.company_id)
                    threshold = settings.SCRAPE_COMPLETENESS_THRESHOLD
                    gate_triggered = (
                        baseline_count > 0 and result.postings_found < baseline_count * threshold
                    )
                    if gate_triggered:
                        pct = (
                            result.postings_found / baseline_count * 100 if baseline_count else 0.0
                        )
                        warn_msg = (
                            f"Scrape completeness gate triggered for {result.company_slug}: "
                            f"{result.postings_found}/{baseline_count} ({pct:.1f}%) "
                            f"— skipping deactivation"
                        )
                        logger.warning(warn_msg)
                        result.warnings.append(warn_msg)
                        closed = 0
                    else:
                        closed = await deactivate_stale_postings(
                            session, result.company_id, scrape_run.id
                        )
                    refreshed.postings_closed = closed
                    result.postings_closed = closed
                    baseline_warnings = await check_baseline_anomaly(
                        session,
                        result.company_id,
                        result.postings_found,
                        exclude_run_id=refreshed.id,
                    )
                    result.warnings.extend(baseline_warnings)
                    if result.warnings:
                        refreshed.errors = {
                            "errors": result.errors,
                            "warnings": result.warnings,
                        }
                else:
                    refreshed.status = ScrapeRunStatus.FAILED
                    refreshed.errors = {
                        "errors": result.errors,
                        "warnings": result.warnings,
                    }
                await session.commit()
        except (IntegrityError, OperationalError) as exc:
            logger.error(
                "Database error finalizing ScrapeRun for %s: %r",
                result.company_slug,
                exc,
            )
        except Exception:
            logger.warning(
                "Non-critical failure finalizing ScrapeRun for %s",
                result.company_slug,
                exc_info=True,
            )

    async def _scrape_with_retries(self, company: Company) -> ScrapeResult:
        for attempt in range(1, self.max_retries + 1):
            try:
                adapter = get_adapter(company.ats_platform)
            except KeyError:
                return ScrapeResult(
                    company_id=company.id,
                    company_slug=company.slug,
                    errors=[f"No adapter registered for ats_platform={company.ats_platform!r}"],
                    finished_at=datetime.now(UTC),
                )

            try:
                logger.info(
                    "Scraping %s (attempt %d/%d, adapter=%s)",
                    company.slug,
                    attempt,
                    self.max_retries,
                    company.ats_platform,
                )
                async with async_session_factory() as session:
                    result = await adapter.scrape(company, session)

                if result.success:
                    logger.info(
                        "Scrape succeeded for %s: %d postings, %d snapshots",
                        company.slug,
                        result.postings_found,
                        result.snapshots_created,
                    )
                    return result

                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Scrape for %s had errors (attempt %d/%d), retrying in %.0fs: %s",
                        company.slug,
                        attempt,
                        self.max_retries,
                        delay,
                        result.errors,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Scrape for %s failed after %d attempts: %s",
                        company.slug,
                        self.max_retries,
                        result.errors,
                    )
                    return result

            except Exception as exc:
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Scrape for %s raised exception (attempt %d/%d), retrying in %.0fs: %r",
                        company.slug,
                        attempt,
                        self.max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Scrape for %s failed after %d attempts with exception: %r",
                        company.slug,
                        self.max_retries,
                        exc,
                    )
                    return ScrapeResult(
                        company_id=company.id,
                        company_slug=company.slug,
                        errors=[f"Exception after {self.max_retries} attempts: {exc!r}"],
                        finished_at=datetime.now(UTC),
                    )

        return ScrapeResult(
            company_id=company.id,
            company_slug=company.slug,
            errors=["Unexpected: exhausted retry loop without returning"],
            finished_at=datetime.now(UTC),
        )
