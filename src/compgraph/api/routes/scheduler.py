from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from compgraph.scheduler.jobs import get_last_pipeline_finished_at, get_last_pipeline_success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

MISSED_RUN_THRESHOLD_HOURS = 56


class ScheduleInfo(BaseModel):
    schedule_id: str
    next_fire_time: datetime | None
    last_fire_time: datetime | None
    paused: bool


class SchedulerStatusResponse(BaseModel):
    enabled: bool
    schedules: list[ScheduleInfo]
    last_pipeline_finished_at: datetime | None
    last_pipeline_success: bool
    missed_run: bool


class TriggerResponse(BaseModel):
    job_id: str
    message: str


class ControlResponse(BaseModel):
    schedule_id: str
    paused: bool
    message: str


_VALID_SCHEDULE_IDS = {"daily_pipeline"}


def _get_scheduler(request: Request):
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler is not enabled. Set SCHEDULER_ENABLED=true.",
        )
    return scheduler


def _validate_schedule_id(job_id: str) -> None:
    if job_id not in _VALID_SCHEDULE_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown schedule '{job_id}'. Valid: {', '.join(sorted(_VALID_SCHEDULE_IDS))}",
        )


@router.get("/status", response_model=SchedulerStatusResponse)
async def scheduler_status(request: Request) -> SchedulerStatusResponse:
    scheduler = getattr(request.app.state, "scheduler", None)
    enabled = scheduler is not None

    schedules: list[ScheduleInfo] = []
    if enabled and scheduler is not None:
        try:
            raw_schedules = await scheduler.get_schedules()
            for s in raw_schedules:
                schedules.append(
                    ScheduleInfo(
                        schedule_id=s.id,
                        next_fire_time=s.next_fire_time,
                        last_fire_time=s.last_fire_time,
                        paused=s.paused,
                    )
                )
        except Exception:
            logger.exception("Failed to fetch schedules from scheduler")

    last_finished = get_last_pipeline_finished_at()
    missed = False
    if last_finished is not None:
        hours_since = (datetime.now(UTC) - last_finished).total_seconds() / 3600
        missed = hours_since > MISSED_RUN_THRESHOLD_HOURS
    elif enabled:
        missed = False

    return SchedulerStatusResponse(
        enabled=enabled,
        schedules=schedules,
        last_pipeline_finished_at=last_finished,
        last_pipeline_success=get_last_pipeline_success(),
        missed_run=missed,
    )


@router.post("/jobs/{job_id}/trigger", response_model=TriggerResponse)
async def trigger_job(request: Request, job_id: str) -> TriggerResponse:
    _validate_schedule_id(job_id)
    scheduler = _get_scheduler(request)

    from compgraph.scheduler.jobs import pipeline_job

    try:
        result_id = await scheduler.add_job(pipeline_job)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to trigger job: {exc}") from exc

    return TriggerResponse(
        job_id=str(result_id),
        message=f"Pipeline job triggered manually (schedule: {job_id}). "
        "Check /api/scrape/status and /api/enrich/status for progress.",
    )


@router.post("/jobs/{job_id}/pause", response_model=ControlResponse)
async def pause_job(request: Request, job_id: str) -> ControlResponse:
    _validate_schedule_id(job_id)
    scheduler = _get_scheduler(request)

    try:
        await scheduler.pause_schedule(job_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Schedule {job_id} not found: {exc}") from exc

    return ControlResponse(
        schedule_id=job_id,
        paused=True,
        message=f"Schedule {job_id} paused. Use /resume to re-enable.",
    )


@router.post("/jobs/{job_id}/resume", response_model=ControlResponse)
async def resume_job(request: Request, job_id: str) -> ControlResponse:
    _validate_schedule_id(job_id)
    scheduler = _get_scheduler(request)

    try:
        await scheduler.unpause_schedule(job_id, resume_from="now")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Schedule {job_id} not found: {exc}") from exc

    return ControlResponse(
        schedule_id=job_id,
        paused=False,
        message=f"Schedule {job_id} resumed.",
    )
