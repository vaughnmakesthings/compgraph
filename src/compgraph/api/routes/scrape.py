"""Scrape pipeline API endpoints: trigger runs and check status."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from compgraph.scrapers.orchestrator import (
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _store_run,
    get_latest_run,
    get_run,
)

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


# --- Response Models ---


class CompanyResultResponse(BaseModel):
    company_slug: str
    postings_found: int
    snapshots_created: int
    errors: list[str]
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


class TriggerResponse(BaseModel):
    run_id: uuid.UUID
    message: str


# --- Helper ---


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
                success=r.success,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for slug, r in run.company_results.items()
        },
    )


# --- Endpoints ---


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_scrape(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Trigger a manual scrape pipeline run.

    The scrape runs in the background. Use GET /api/scrape/status to check progress.
    """
    pipeline_run = PipelineRun()
    _store_run(pipeline_run)

    orchestrator = PipelineOrchestrator()

    async def _run_pipeline() -> None:
        await orchestrator.run(pipeline_run)

    background_tasks.add_task(_run_pipeline)

    return TriggerResponse(
        run_id=pipeline_run.run_id,
        message="Pipeline run triggered. Check /api/scrape/status for progress.",
    )


@router.get("/status", response_model=PipelineRunResponse)
async def scrape_status() -> PipelineRunResponse:
    """Get the status of the most recent pipeline run."""
    run = get_latest_run()
    if run is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return _run_to_response(run)


@router.get("/status/{run_id}", response_model=PipelineRunResponse)
async def scrape_status_by_id(run_id: uuid.UUID) -> PipelineRunResponse:
    """Get the status of a specific pipeline run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    return _run_to_response(run)
