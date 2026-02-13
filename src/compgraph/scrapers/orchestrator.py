"""Pipeline orchestrator: coordinates scrape runs across all companies with error isolation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company, ScrapeRun, ScrapeRunStatus
from compgraph.db.session import async_session_factory
from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.registry import get_adapter

logger = logging.getLogger(__name__)


class PipelineStatus(StrEnum):
    """Overall status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class PipelineRun:
    """Tracks the state and results of a single pipeline run."""

    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    company_results: dict[str, ScrapeResult] = field(default_factory=dict)

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

            tasks = [self._scrape_company_with_isolation(company) for company in companies]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for company, result in zip(companies, results, strict=True):
                if isinstance(result, BaseException):
                    error_result = ScrapeResult(
                        company_id=company.id,
                        company_slug=company.slug,
                        errors=[f"Unhandled exception: {result!r}"],
                        finished_at=datetime.now(UTC),
                    )
                    pipeline_run.company_results[company.slug] = error_result
                    logger.error("Unhandled exception scraping %s: %r", company.slug, result)
                else:
                    pipeline_run.company_results[company.slug] = result

            if pipeline_run.companies_failed == 0:
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

    async def _scrape_company_with_isolation(self, company: Company) -> ScrapeResult:
        async with self.semaphore:
            scrape_run = await self._create_scrape_run(company)

            result = await self._scrape_with_retries(company)

            await self._finalize_scrape_run(scrape_run, result)
            return result

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
        except Exception:
            logger.exception("Failed to create ScrapeRun for %s", company.slug)
            return None

    async def _finalize_scrape_run(
        self, scrape_run: ScrapeRun | None, result: ScrapeResult
    ) -> None:
        if scrape_run is None:
            return
        try:
            async with async_session_factory() as session:
                merged = await session.merge(scrape_run)
                merged.completed_at = datetime.now(UTC)
                merged.jobs_found = result.postings_found
                merged.snapshots_created = result.snapshots_created
                merged.pages_scraped = result.pages_scraped
                if result.success:
                    merged.status = ScrapeRunStatus.COMPLETED
                else:
                    merged.status = ScrapeRunStatus.FAILED
                    merged.errors = {"errors": result.errors}
                await session.commit()
        except Exception:
            logger.exception("Failed to finalize ScrapeRun for %s", result.company_slug)

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
