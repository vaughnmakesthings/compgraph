from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from compgraph.auth.dependencies import AuthUser, require_viewer
from compgraph.enrichment.orchestrator import (
    EnrichmentRun,
    EnrichmentStatus,
    get_latest_enrichment_run,
    get_latest_enrichment_run_from_db,
)
from compgraph.scrapers.orchestrator import (
    PipelineRun,
    PipelineStatus,
    get_latest_run,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class ScrapeCurrentRun(BaseModel):
    run_id: uuid.UUID
    status: str
    started_at: datetime
    total_postings_found: int
    total_snapshots_created: int
    companies_succeeded: int
    companies_failed: int
    total_companies: int


class EnrichCurrentRun(BaseModel):
    run_id: uuid.UUID
    status: str
    started_at: datetime
    pass1_total: int
    pass1_succeeded: int
    pass1_skipped: int = 0
    pass2_total: int
    pass2_succeeded: int
    pass2_skipped: int = 0


class StageStatus(BaseModel):
    status: str
    last_completed_at: datetime | None
    current_run: ScrapeCurrentRun | EnrichCurrentRun | None


class SchedulerSummary(BaseModel):
    enabled: bool
    next_run_at: datetime | None


class PipelineStatusResponse(BaseModel):
    system_state: str
    scrape: StageStatus
    enrich: StageStatus
    scheduler: SchedulerSummary


def _scrape_stage_status(run: PipelineRun | None) -> StageStatus:
    if run is None:
        return StageStatus(status="idle", last_completed_at=None, current_run=None)

    if run.status == PipelineStatus.RUNNING:
        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=ScrapeCurrentRun(
                run_id=run.run_id,
                status=run.status.value,
                started_at=run.started_at,
                total_postings_found=run.total_postings_found,
                total_snapshots_created=run.total_snapshots_created,
                companies_succeeded=run.companies_succeeded,
                companies_failed=run.companies_failed,
                total_companies=len(run.company_states),
            ),
        )

    return StageStatus(
        status=run.status.value,
        last_completed_at=run.finished_at,
        current_run=None,
    )


_ENRICH_STATUS_MAP = {
    EnrichmentStatus.SUCCESS: "completed",
    EnrichmentStatus.PARTIAL: "completed",
}


async def _enrich_stage_from_memory(run: EnrichmentRun) -> StageStatus:
    if run.status == EnrichmentStatus.RUNNING:
        p1 = run.pass1_result
        p2 = run.pass2_result
        pass1_succeeded = p1.succeeded if p1 else 0
        pass1_skipped = p1.skipped if p1 else 0
        pass2_succeeded = p2.succeeded if p2 else 0
        pass2_skipped = p2.skipped if p2 else 0

        pass1_total = 0
        pass2_total = 0

        if pass1_succeeded == 0 and pass2_succeeded == 0:
            db_run = await get_latest_enrichment_run_from_db()
            if db_run is not None and db_run["status"] == "running":
                return _enrich_stage_from_db(db_run)

        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=EnrichCurrentRun(
                run_id=run.run_id,
                status="running",
                started_at=run.started_at,
                pass1_total=pass1_total,
                pass1_succeeded=pass1_succeeded,
                pass1_skipped=pass1_skipped,
                pass2_total=pass2_total,
                pass2_succeeded=pass2_succeeded,
                pass2_skipped=pass2_skipped,
            ),
        )

    normalized = _ENRICH_STATUS_MAP.get(run.status, run.status.value)
    return StageStatus(
        status=normalized,
        last_completed_at=run.finished_at,
        current_run=None,
    )


def _enrich_stage_from_db(db_run: dict) -> StageStatus:
    if db_run["status"] == "running":
        return StageStatus(
            status="running",
            last_completed_at=None,
            current_run=EnrichCurrentRun(
                run_id=db_run["run_id"],
                status=db_run["status"],
                started_at=db_run["started_at"],
                pass1_total=db_run["pass1_total"],
                pass1_succeeded=db_run["pass1_succeeded"],
                pass1_skipped=db_run["pass1_skipped"],
                pass2_total=db_run["pass2_total"],
                pass2_succeeded=db_run["pass2_succeeded"],
                pass2_skipped=db_run["pass2_skipped"],
            ),
        )

    return StageStatus(
        status=db_run["status"],
        last_completed_at=db_run["finished_at"],
        current_run=None,
    )


def _derive_system_state(scrape: StageStatus, enrich: StageStatus) -> str:
    if scrape.status == "running":
        return "scraping"
    if enrich.status == "running":
        return "enriching"
    if scrape.status == "failed" or enrich.status == "failed":
        return "error"
    return "idle"


async def get_latest_scrape_run_from_db() -> dict | None:
    from sqlalchemy import select

    from compgraph.db.models import ScrapeRun
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "run_id": row.id,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.completed_at,
            "jobs_found": row.jobs_found,
            "snapshots_created": row.snapshots_created,
        }


class ScrapeRunSummary(BaseModel):
    id: uuid.UUID
    company_name: str
    company_slug: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    jobs_found: int
    snapshots_created: int
    postings_closed: int


class EnrichmentRunSummary(BaseModel):
    id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    pass1_total: int
    pass1_succeeded: int
    pass2_total: int
    pass2_succeeded: int


class PipelineRunsResponse(BaseModel):
    scrape_runs: list[ScrapeRunSummary]
    enrichment_runs: list[EnrichmentRunSummary]


@router.get("/runs", response_model=PipelineRunsResponse)
async def pipeline_runs(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> PipelineRunsResponse:
    from sqlalchemy import select

    from compgraph.db.models import Company, EnrichmentRunDB, ScrapeRun
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        scrape_stmt = (
            select(
                ScrapeRun, Company.name.label("company_name"), Company.slug.label("company_slug")
            )
            .join(Company, ScrapeRun.company_id == Company.id)
            .order_by(ScrapeRun.started_at.desc())
            .limit(50)
        )
        scrape_result = await session.execute(scrape_stmt)
        scrape_rows = scrape_result.all()

        enrich_stmt = select(EnrichmentRunDB).order_by(EnrichmentRunDB.started_at.desc()).limit(20)
        enrich_result = await session.execute(enrich_stmt)
        enrich_rows = enrich_result.scalars().all()

    return PipelineRunsResponse(
        scrape_runs=[
            ScrapeRunSummary(
                id=row.ScrapeRun.id,
                company_name=row.company_name,
                company_slug=row.company_slug,
                status=row.ScrapeRun.status,
                started_at=row.ScrapeRun.started_at,
                completed_at=row.ScrapeRun.completed_at,
                jobs_found=row.ScrapeRun.jobs_found,
                snapshots_created=row.ScrapeRun.snapshots_created,
                postings_closed=row.ScrapeRun.postings_closed,
            )
            for row in scrape_rows
        ],
        enrichment_runs=[
            EnrichmentRunSummary(
                id=r.id,
                status=r.status,
                started_at=r.started_at,
                finished_at=r.finished_at,
                pass1_total=r.pass1_total,
                pass1_succeeded=r.pass1_succeeded,
                pass2_total=r.pass2_total,
                pass2_succeeded=r.pass2_succeeded,
            )
            for r in enrich_rows
        ],
    )


@router.get("/status", response_model=PipelineStatusResponse)
async def pipeline_status(
    request: Request,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> PipelineStatusResponse:
    scrape_run = get_latest_run()
    scrape_stage = _scrape_stage_status(scrape_run)

    if scrape_run is None:
        db_scrape = await get_latest_scrape_run_from_db()
        if db_scrape is not None:
            db_status = db_scrape["status"]
            # DB uses "pending" for in-progress runs; normalize to "running"
            # so _derive_system_state correctly detects active scrapes
            if db_status == "pending":
                db_status = "running"
            scrape_stage = StageStatus(
                status=db_status,
                last_completed_at=db_scrape["finished_at"],
                current_run=None,
            )

    enrich_run = get_latest_enrichment_run()
    if enrich_run is not None:
        enrich_stage = await _enrich_stage_from_memory(enrich_run)
    else:
        db_enrich = await get_latest_enrichment_run_from_db()
        if db_enrich is not None:
            enrich_stage = _enrich_stage_from_db(db_enrich)
        else:
            enrich_stage = StageStatus(status="idle", last_completed_at=None, current_run=None)

    arq_pool = getattr(request.app.state, "arq_pool", None)
    enabled = arq_pool is not None

    return PipelineStatusResponse(
        system_state=_derive_system_state(scrape_stage, enrich_stage),
        scrape=scrape_stage,
        enrich=enrich_stage,
        scheduler=SchedulerSummary(enabled=enabled, next_run_at=None),
    )
