"""Enrichment pipeline API endpoints: trigger runs and check status."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from compgraph.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentRun,
    EnrichmentStatus,
    _store_run,
    get_enrichment_run,
    get_latest_enrichment_run,
    get_latest_enrichment_run_from_db,
)

_STATUS_MAP: dict[str, EnrichmentStatus] = {
    "pending": EnrichmentStatus.PENDING,
    "running": EnrichmentStatus.RUNNING,
    "completed": EnrichmentStatus.SUCCESS,
    "failed": EnrichmentStatus.FAILED,
}

logger = logging.getLogger(__name__)

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
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_api_calls: int = 0
    total_dedup_saved: int = 0
    circuit_breaker_tripped: bool = False
    error_summary: str | None = None


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
    total_in = 0
    total_out = 0
    total_api = 0
    total_dedup = 0
    for r in (run.pass1_result, run.pass2_result):
        if r:
            total_in += r.total_input_tokens
            total_out += r.total_output_tokens
            total_api += r.total_api_calls
            total_dedup += r.total_dedup_saved
    return EnrichmentRunResponse(
        run_id=run.run_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        pass1_result=pass1,
        pass2_result=pass2,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_api_calls=total_api,
        total_dedup_saved=total_dedup,
        circuit_breaker_tripped=run.circuit_breaker_tripped,
        error_summary=run.error_summary,
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
        try:
            await method(enrichment_run)
        except Exception:
            logger.exception("Enrichment run %s failed", enrichment_run.run_id)
            if enrichment_run.status == EnrichmentStatus.RUNNING:
                enrichment_run.status = EnrichmentStatus.FAILED
                enrichment_run.finished_at = datetime.now(tz=UTC)
                # Best-effort DB update — only if run was still RUNNING
                try:
                    from compgraph.db.models import EnrichmentRunStatus as DBStatus
                    from compgraph.enrichment.orchestrator import (
                        update_enrichment_run_record,
                    )

                    await update_enrichment_run_record(
                        enrichment_run.run_id,
                        status=DBStatus.FAILED,
                        finished_at=enrichment_run.finished_at,
                        error_summary=f"Unhandled exception in {method_name}",
                    )
                except Exception:
                    logger.exception(
                        "Failed to update DB for crashed run %s",
                        enrichment_run.run_id,
                    )

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


def _db_dict_to_response(d: dict) -> EnrichmentRunResponse:
    """Convert a DB-backed enrichment run dict to a response model."""
    pass1 = None
    if d.get("pass1_succeeded") is not None or d.get("pass1_failed") is not None:
        pass1 = EnrichResultResponse(
            succeeded=d.get("pass1_succeeded") or 0,
            failed=d.get("pass1_failed") or 0,
            skipped=d.get("pass1_skipped") or 0,
        )
    pass2 = None
    if d.get("pass2_succeeded") is not None or d.get("pass2_failed") is not None:
        pass2 = EnrichResultResponse(
            succeeded=d.get("pass2_succeeded") or 0,
            failed=d.get("pass2_failed") or 0,
            skipped=d.get("pass2_skipped") or 0,
        )
    return EnrichmentRunResponse(
        run_id=d["run_id"],
        status=_STATUS_MAP.get(d["status"], EnrichmentStatus.FAILED),
        started_at=d["started_at"],
        finished_at=d.get("finished_at"),
        pass1_result=pass1,
        pass2_result=pass2,
        total_input_tokens=d.get("total_input_tokens") or 0,
        total_output_tokens=d.get("total_output_tokens") or 0,
        total_api_calls=d.get("total_api_calls") or 0,
        total_dedup_saved=d.get("total_dedup_saved") or 0,
        circuit_breaker_tripped=d.get("circuit_breaker_tripped") or False,
        error_summary=d.get("error_summary"),
    )


@router.get("/status", response_model=EnrichmentRunResponse)
async def enrich_status() -> EnrichmentRunResponse:
    """Get the status of the most recent enrichment run.

    Falls back to DB when in-memory store is empty (e.g. after server restart).
    """
    run = get_latest_enrichment_run()
    if run is not None:
        return _run_to_response(run)

    db_run = await get_latest_enrichment_run_from_db()
    if db_run is not None:
        return _db_dict_to_response(db_run)

    raise HTTPException(status_code=404, detail="No enrichment runs found")


@router.get("/status/{run_id}", response_model=EnrichmentRunResponse)
async def enrich_status_by_id(run_id: uuid.UUID) -> EnrichmentRunResponse:
    """Get the status of a specific enrichment run."""
    run = get_enrichment_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Enrichment run {run_id} not found")
    return _run_to_response(run)
