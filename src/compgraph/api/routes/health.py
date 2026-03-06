import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from compgraph.api.deps import get_db
from compgraph.config import settings

router = APIRouter()

logger = logging.getLogger(__name__)

DB_CHECK_TIMEOUT = 2.0
SCHEDULER_CHECK_TIMEOUT = 2.0


@router.get("/health")
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    checks: dict[str, str] = {}

    # Database check
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=DB_CHECK_TIMEOUT)
        checks["database"] = "connected"
    except (TimeoutError, OSError, SQLAlchemyError) as exc:
        logger.warning("Database health check failed: %s", exc, exc_info=exc)
        checks["database"] = "error: unavailable"

    # Scheduler check
    if settings.SCHEDULER_ENABLED:
        scheduler = getattr(request.app.state, "scheduler", None)
        if scheduler is None:
            checks["scheduler"] = "error: not initialized"
        else:
            try:
                schedules = await asyncio.wait_for(
                    scheduler.get_schedules(), timeout=SCHEDULER_CHECK_TIMEOUT
                )
                checks["scheduler"] = f"ok ({len(schedules)} schedule(s))"
            except Exception as exc:
                logger.warning("Scheduler health check failed: %s", exc, exc_info=exc)
                checks["scheduler"] = "error: unavailable"
    else:
        checks["scheduler"] = "disabled"

    # Pipeline status (for deploy safety checks)
    from compgraph.scrapers.orchestrator import PipelineStatus, _pipeline_runs

    active_pipelines = [
        r
        for r in _pipeline_runs.values()
        if r.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED, PipelineStatus.STOPPING)
    ]
    if active_pipelines:
        checks["pipeline"] = f"active ({len(active_pipelines)} run(s))"
    else:
        checks["pipeline"] = "idle"

    # Shutdown status (access via app.state to avoid circular import with main)
    shutdown_evt = getattr(request.app.state, "shutdown_event", None)
    shutting_down = shutdown_evt is not None and shutdown_evt.is_set()
    if shutting_down:
        checks["shutdown"] = "in_progress"

    has_errors = any(v.startswith("error") for v in checks.values())
    status_code = 503 if has_errors or shutting_down else 200
    overall = "shutting_down" if shutting_down else ("degraded" if has_errors else "ok")

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "version": "0.1.0", "checks": checks},
    )
