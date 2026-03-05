"""Scrape pipeline API endpoints: trigger runs, check status, and control execution."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.auth.dependencies import AuthUser, require_admin, require_viewer
from compgraph.db.models import ScrapeRun
from compgraph.scrapers.orchestrator import (
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _pipeline_orchestrators,
    _store_run,
    get_all_runs,
    get_latest_run,
    get_orchestrator,
    get_run,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])


# --- Response Models ---


class CompanyResultResponse(BaseModel):
    company_slug: str
    postings_found: int
    snapshots_created: int
    errors: list[str]
    warnings: list[str]
    success: bool
    started_at: datetime
    finished_at: datetime | None


class PipelineRunResponse(BaseModel):
    run_id: uuid.UUID
    status: PipelineStatus
    started_at: datetime
    finished_at: datetime | None
    total_postings_found: int
    total_snapshots_created: int
    total_errors: int
    companies_succeeded: int
    companies_failed: int
    company_results: dict[str, CompanyResultResponse]
    company_states: dict[str, str]


class TriggerResponse(BaseModel):
    run_id: uuid.UUID
    message: str


class ControlResponse(BaseModel):
    run_id: uuid.UUID
    status: PipelineStatus
    message: str


# --- Helpers ---


def _run_to_response(run: PipelineRun) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=run.run_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        total_postings_found=run.total_postings_found,
        total_snapshots_created=run.total_snapshots_created,
        total_errors=run.total_errors,
        companies_succeeded=run.companies_succeeded,
        companies_failed=run.companies_failed,
        company_results={
            slug: CompanyResultResponse(
                company_slug=slug,
                postings_found=r.postings_found,
                snapshots_created=r.snapshots_created,
                errors=r.errors,
                warnings=r.warnings,
                success=r.success,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for slug, r in run.company_results.items()
        },
        company_states={k: v.value for k, v in run.company_states.items()},
    )


def _get_active_run_and_orchestrator(
    run_id: uuid.UUID | None = None,
    allowed_statuses: tuple[PipelineStatus, ...] = (
        PipelineStatus.RUNNING,
        PipelineStatus.PAUSED,
    ),
) -> tuple[PipelineRun, PipelineOrchestrator]:
    """Find an active run and its orchestrator, or raise HTTP errors.

    If run_id is provided, targets that specific run. Otherwise falls back
    to the latest run.
    """
    if run_id is not None:
        run = get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    else:
        run = get_latest_run()
        if run is None:
            raise HTTPException(status_code=404, detail="No pipeline runs found")
    if run.status not in allowed_statuses:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline is not active (status={run.status})",
        )
    orch = get_orchestrator(run.run_id)
    if orch is None:
        raise HTTPException(
            status_code=409,
            detail="Orchestrator not found for this run",
        )
    return run, orch


# --- Endpoints ---


_ACTIVE_STATUSES = frozenset(
    {
        PipelineStatus.PENDING,
        PipelineStatus.RUNNING,
        PipelineStatus.PAUSED,
        PipelineStatus.STOPPING,
    }
)

_DB_ACTIVE_STATUSES = [s.value for s in _ACTIVE_STATUSES]


async def _check_active_scrape_run(db: AsyncSession) -> ScrapeRun | None:
    stmt = (
        select(ScrapeRun)
        .where(ScrapeRun.status.in_(_DB_ACTIVE_STATUSES))
        .order_by(ScrapeRun.started_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TriggerResponse:
    msg = "A pipeline is already running. Wait for completion or force-stop first."

    active_run = await _check_active_scrape_run(db)
    if active_run is not None:
        logger.info(
            "Trigger blocked by DB concurrency guard: active scrape_run %s (status=%s)",
            active_run.id,
            active_run.status,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": msg,
                "active_run_id": str(active_run.id),
                "active_status": active_run.status,
            },
        )

    latest = get_latest_run()
    if latest is not None and latest.status in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "message": msg,
                "active_run_id": str(latest.run_id),
                "active_status": latest.status.value,
            },
        )

    pipeline_run = PipelineRun()
    _store_run(pipeline_run)

    orchestrator = PipelineOrchestrator()
    _pipeline_orchestrators[pipeline_run.run_id] = orchestrator

    async def _run_pipeline() -> None:
        try:
            await orchestrator.run(pipeline_run)
        finally:
            _pipeline_orchestrators.pop(pipeline_run.run_id, None)

    background_tasks.add_task(_run_pipeline)

    return TriggerResponse(
        run_id=pipeline_run.run_id,
        message="Pipeline run triggered. Check /api/v1/scrape/status for progress.",
    )


@router.get("/status", response_model=PipelineRunResponse)
async def scrape_status(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> PipelineRunResponse:
    """Get the status of the most recent pipeline run."""
    run = get_latest_run()
    if run is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return _run_to_response(run)


@router.get("/status/{run_id}", response_model=PipelineRunResponse)
async def scrape_status_by_id(
    run_id: uuid.UUID,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> PipelineRunResponse:
    """Get the status of a specific pipeline run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    return _run_to_response(run)


@router.post("/pause", response_model=ControlResponse)
async def pause_scrape(
    run_id: uuid.UUID | None = None,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    """Pause the running scrape pipeline. Companies mid-scrape will finish their current page."""
    run, orch = _get_active_run_and_orchestrator(run_id=run_id)
    if run.status != PipelineStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Pipeline is not running (cannot pause)")
    orch.pause(run)
    return ControlResponse(
        run_id=run.run_id,
        status=run.status,
        message="Pipeline paused. Use /api/v1/scrape/resume to continue.",
    )


@router.post("/resume", response_model=ControlResponse)
async def resume_scrape(
    run_id: uuid.UUID | None = None,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    """Resume a paused scrape pipeline."""
    run, orch = _get_active_run_and_orchestrator(run_id=run_id)
    if run.status != PipelineStatus.PAUSED:
        raise HTTPException(status_code=409, detail="Pipeline is not paused (cannot resume)")
    orch.resume(run)
    return ControlResponse(
        run_id=run.run_id,
        status=run.status,
        message="Pipeline resumed.",
    )


@router.post("/stop", response_model=ControlResponse)
async def stop_scrape(
    run_id: uuid.UUID | None = None,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    """Gracefully stop the scrape pipeline. Running companies finish, pending are skipped."""
    run, orch = _get_active_run_and_orchestrator(run_id=run_id)
    orch.stop(run)
    return ControlResponse(
        run_id=run.run_id,
        status=run.status,
        message="Pipeline stopping gracefully. Running companies will finish.",
    )


@router.post("/force-stop", response_model=ControlResponse)
async def force_stop_scrape(
    run_id: uuid.UUID | None = None,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    """Force stop the scrape pipeline. All tasks are cancelled immediately."""
    run, orch = _get_active_run_and_orchestrator(
        run_id=run_id,
        allowed_statuses=(
            PipelineStatus.RUNNING,
            PipelineStatus.PAUSED,
            PipelineStatus.STOPPING,
        ),
    )
    orch.force_stop(run)
    return ControlResponse(
        run_id=run.run_id,
        status=run.status,
        message="Pipeline force-stopped. All tasks cancelled.",
    )


# --- Run Listing ---


class PipelineRunSummary(BaseModel):
    run_id: uuid.UUID
    status: PipelineStatus
    started_at: datetime
    finished_at: datetime | None
    total_postings_found: int
    total_snapshots_created: int
    companies_succeeded: int
    companies_failed: int


class PipelineRunListResponse(BaseModel):
    runs: list[PipelineRunSummary]
    total: int


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_scrape_runs(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> PipelineRunListResponse:
    """List all in-memory pipeline runs, most recent first."""

    runs = get_all_runs()
    return PipelineRunListResponse(
        runs=[
            PipelineRunSummary(
                run_id=r.run_id,
                status=r.status,
                started_at=r.started_at,
                finished_at=r.finished_at,
                total_postings_found=r.total_postings_found,
                total_snapshots_created=r.total_snapshots_created,
                companies_succeeded=r.companies_succeeded,
                companies_failed=r.companies_failed,
            )
            for r in runs
        ],
        total=len(runs),
    )
