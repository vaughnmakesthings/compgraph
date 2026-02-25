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
        detail = str(exc) if str(exc) else type(exc).__name__
        checks["database"] = f"error: {detail}"

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
                logger.warning("Scheduler health check failed: %s", exc)
                checks["scheduler"] = f"error: {type(exc).__name__}"
    else:
        checks["scheduler"] = "disabled"

    has_errors = any(v.startswith("error") for v in checks.values())
    status_code = 503 if has_errors else 200
    overall = "degraded" if has_errors else "ok"

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "version": "0.1.0", "checks": checks},
    )
