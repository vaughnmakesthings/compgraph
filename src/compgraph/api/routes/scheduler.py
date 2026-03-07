from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from compgraph.auth.dependencies import AuthUser, require_admin, require_viewer
from compgraph.scheduler.app import (
    _DAY_NAMES,
    _DAY_NUMBERS,
    DEFAULT_SCHEDULE_CONFIG,
    PAUSE_REDIS_KEY,
    SCHEDULE_ID,
    enqueue_pipeline_job,
    get_schedule_config,
    set_schedule_config,
)
from compgraph.scheduler.jobs import (
    get_last_pipeline_finished_at,
    get_last_pipeline_success,
)

if TYPE_CHECKING:
    from arq import ArqRedis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

MISSED_RUN_THRESHOLD_HOURS = 80  # 72h max gap (Fri->Mon) + 8h grace


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
    last_pipeline_error: str | None = None


class TriggerResponse(BaseModel):
    job_id: str
    message: str


class ControlResponse(BaseModel):
    schedule_id: str
    paused: bool
    message: str


class ScheduleConfigResponse(BaseModel):
    schedule_id: str
    weekdays: list[str]  # ["mon", "wed", "fri"]
    hour: int
    minute: int
    timezone: str  # always "UTC" — informational


class ScheduleConfigUpdate(BaseModel):
    weekdays: list[str] | None = None  # ["mon", "wed", "fri"]
    hour: int | None = None  # 0-23
    minute: int | None = None  # 0-59


_VALID_SCHEDULE_IDS = {SCHEDULE_ID}


def _get_arq_pool(request: Request) -> ArqRedis:
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler is not enabled. Set SCHEDULER_ENABLED=true and configure REDIS_URL.",
        )
    return pool  # type: ignore[no-any-return]


def _validate_schedule_id(job_id: str) -> None:
    if job_id not in _VALID_SCHEDULE_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown schedule '{job_id}'. Valid: {', '.join(sorted(_VALID_SCHEDULE_IDS))}",
        )


@router.get("/status", response_model=SchedulerStatusResponse)
async def scheduler_status(
    request: Request,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> SchedulerStatusResponse:
    pool: ArqRedis | None = getattr(request.app.state, "arq_pool", None)
    enabled = pool is not None

    schedules: list[ScheduleInfo] = []
    if enabled and pool is not None:
        is_paused = bool(await pool.get(f"{PAUSE_REDIS_KEY}{SCHEDULE_ID}"))
        schedules.append(
            ScheduleInfo(
                schedule_id=SCHEDULE_ID,
                next_fire_time=None,
                last_fire_time=None,
                paused=is_paused,
            )
        )

    last_finished = get_last_pipeline_finished_at()
    last_success = get_last_pipeline_success()

    if last_finished is None:
        from compgraph.scheduler.jobs import get_last_pipeline_run_from_db

        try:
            db_result = await get_last_pipeline_run_from_db()
            db_finished = db_result["finished_at"]
            if isinstance(db_finished, datetime):
                last_finished = db_finished
                last_success = bool(db_result["success"])
        except Exception:
            logger.debug("DB fallback for last pipeline run failed", exc_info=True)

    missed = False
    if last_finished is not None:
        hours_since = (datetime.now(UTC) - last_finished).total_seconds() / 3600
        missed = hours_since > MISSED_RUN_THRESHOLD_HOURS

    from compgraph.scheduler.jobs import get_last_pipeline_error

    return SchedulerStatusResponse(
        enabled=enabled,
        schedules=schedules,
        last_pipeline_finished_at=last_finished,
        last_pipeline_success=last_success,
        missed_run=missed,
        last_pipeline_error=get_last_pipeline_error(),
    )


@router.post("/jobs/{job_id}/trigger", response_model=TriggerResponse)
async def trigger_job(
    request: Request,
    job_id: str,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> TriggerResponse:
    _validate_schedule_id(job_id)
    pool = _get_arq_pool(request)

    try:
        result_id = await enqueue_pipeline_job(pool)  # type: ignore[arg-type]
    except Exception:
        logger.exception("Failed to trigger job")
        raise HTTPException(status_code=500, detail="Failed to trigger job") from None

    if result_id is None:
        raise HTTPException(status_code=409, detail="Pipeline job already queued")

    return TriggerResponse(
        job_id=result_id,
        message=f"Pipeline job triggered manually (schedule: {job_id}). "
        "Check /api/v1/scrape/status and /api/v1/enrich/status for progress.",
    )


@router.post("/jobs/{job_id}/pause", response_model=ControlResponse)
async def pause_job(
    request: Request,
    job_id: str,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    _validate_schedule_id(job_id)
    pool = _get_arq_pool(request)

    await pool.set(f"{PAUSE_REDIS_KEY}{job_id}", b"1")
    logger.info("Schedule %s paused (stored in Redis)", job_id)

    return ControlResponse(
        schedule_id=job_id,
        paused=True,
        message=f"Schedule {job_id} paused. Use /resume to re-enable.",
    )


@router.post("/jobs/{job_id}/resume", response_model=ControlResponse)
async def resume_job(
    request: Request,
    job_id: str,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ControlResponse:
    _validate_schedule_id(job_id)
    pool = _get_arq_pool(request)

    await pool.delete(f"{PAUSE_REDIS_KEY}{job_id}")
    logger.info("Schedule %s resumed (cleared from Redis)", job_id)

    return ControlResponse(
        schedule_id=job_id,
        paused=False,
        message=f"Schedule {job_id} resumed.",
    )


def _config_to_response(config: dict[str, Any]) -> ScheduleConfigResponse:
    weekday_names = [_DAY_NAMES[d] for d in config["weekdays"]]
    return ScheduleConfigResponse(
        schedule_id=SCHEDULE_ID,
        weekdays=weekday_names,
        hour=config["hour"],
        minute=config["minute"],
        timezone="UTC",
    )


@router.get("/config", response_model=ScheduleConfigResponse)
async def get_config(
    request: Request,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
) -> ScheduleConfigResponse:
    pool: ArqRedis | None = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        return _config_to_response(DEFAULT_SCHEDULE_CONFIG)
    config = await get_schedule_config(pool)
    return _config_to_response(config)


@router.put("/config", response_model=ScheduleConfigResponse)
async def update_config(
    request: Request,
    body: ScheduleConfigUpdate,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> ScheduleConfigResponse:
    pool = _get_arq_pool(request)
    config = await get_schedule_config(pool)

    if body.weekdays is not None:
        day_numbers = []
        for name in body.weekdays:
            lower = name.lower()
            if lower not in _DAY_NUMBERS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid weekday '{name}'. Valid: {', '.join(sorted(_DAY_NUMBERS))}",
                )
            day_numbers.append(_DAY_NUMBERS[lower])
        config["weekdays"] = sorted(day_numbers)

    if body.hour is not None:
        if not 0 <= body.hour <= 23:
            raise HTTPException(status_code=422, detail="hour must be 0-23")
        config["hour"] = body.hour

    if body.minute is not None:
        if not 0 <= body.minute <= 59:
            raise HTTPException(status_code=422, detail="minute must be 0-59")
        config["minute"] = body.minute

    await set_schedule_config(pool, config)
    logger.info("Schedule config updated: %s", config)

    return _config_to_response(config)
