"""Enrichment pipeline API endpoints: trigger runs and check status."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from compgraph.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentRun,
    EnrichmentStatus,
    _store_run,
    get_enrichment_run,
    get_latest_enrichment_run,
)

router = APIRouter(prefix="/api/enrich", tags=["enrich"])


# --- Response Models ---


class EnrichResultResponse(BaseModel):
    succeeded: int
    failed: int
    skipped: int


class EnrichmentRunResponse(BaseModel):
    run_id: uuid.UUID
    status: EnrichmentStatus
    started_at: datetime
    finished_at: datetime | None
    pass1_result: EnrichResultResponse | None
    pass2_result: EnrichResultResponse | None


class TriggerResponse(BaseModel):
    run_id: uuid.UUID
    message: str


# --- Helper ---


def _run_to_response(run: EnrichmentRun) -> EnrichmentRunResponse:
    pass1 = None
    if run.pass1_result:
        pass1 = EnrichResultResponse(
            succeeded=run.pass1_result.succeeded,
            failed=run.pass1_result.failed,
            skipped=run.pass1_result.skipped,
        )
    pass2 = None
    if run.pass2_result:
        pass2 = EnrichResultResponse(
            succeeded=run.pass2_result.succeeded,
            failed=run.pass2_result.failed,
            skipped=run.pass2_result.skipped,
        )
    return EnrichmentRunResponse(
        run_id=run.run_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        pass1_result=pass1,
        pass2_result=pass2,
    )


# --- Endpoints ---


_TRIGGER_METHODS = {"run_pass1", "run_pass2", "run_full"}


def _trigger_enrichment(
    background_tasks: BackgroundTasks,
    method_name: str,
    message: str,
) -> TriggerResponse:
    """Shared setup for all enrichment trigger endpoints."""
    if method_name not in _TRIGGER_METHODS:
        raise ValueError(f"Unknown enrichment method: {method_name}")

    enrichment_run = EnrichmentRun()
    _store_run(enrichment_run)

    orchestrator = EnrichmentOrchestrator()
    method = getattr(orchestrator, method_name)

    async def _run() -> None:
        await method(enrichment_run)

    background_tasks.add_task(_run)

    return TriggerResponse(run_id=enrichment_run.run_id, message=message)


@router.post("/pass1/trigger", response_model=TriggerResponse)
async def trigger_pass1(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Trigger Pass 1 enrichment (Haiku classification)."""
    return _trigger_enrichment(
        background_tasks,
        "run_pass1",
        "Pass 1 enrichment triggered. Check /api/enrich/status for progress.",
    )


@router.post("/pass2/trigger", response_model=TriggerResponse)
async def trigger_pass2(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Trigger Pass 2 enrichment (Sonnet entity extraction)."""
    return _trigger_enrichment(
        background_tasks,
        "run_pass2",
        "Pass 2 enrichment triggered. Check /api/enrich/status for progress.",
    )


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_full(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Trigger full enrichment pipeline (Pass 1 + Pass 2)."""
    return _trigger_enrichment(
        background_tasks,
        "run_full",
        "Full enrichment pipeline triggered. Check /api/enrich/status for progress.",
    )


@router.get("/status", response_model=EnrichmentRunResponse)
async def enrich_status() -> EnrichmentRunResponse:
    """Get the status of the most recent enrichment run."""
    run = get_latest_enrichment_run()
    if run is None:
        raise HTTPException(status_code=404, detail="No enrichment runs found")
    return _run_to_response(run)


@router.get("/status/{run_id}", response_model=EnrichmentRunResponse)
async def enrich_status_by_id(run_id: uuid.UUID) -> EnrichmentRunResponse:
    """Get the status of a specific enrichment run."""
    run = get_enrichment_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Enrichment run {run_id} not found")
    return _run_to_response(run)
