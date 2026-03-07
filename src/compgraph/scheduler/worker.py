from __future__ import annotations

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from compgraph.config import settings

logger = logging.getLogger(__name__)

CRON_WEEKDAYS = {0, 2, 4}  # Mon, Wed, Fri
CRON_HOUR = 7  # 7 AM UTC = 2 AM ET (EST+5) / 3 AM ET (EDT+4)
CRON_MINUTE = 0
CRON_TIMEOUT_SECONDS = 7200  # 2h max runtime per pipeline run


def get_redis_settings() -> RedisSettings:
    url = settings.REDIS_URL
    if url:
        return RedisSettings.from_dsn(url)
    return RedisSettings()


async def on_startup(ctx: dict[str, Any]) -> None:
    logger.info("[ARQ] Worker starting up")


async def on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("[ARQ] Worker shutting down")


async def run_pipeline(ctx: dict[str, Any]) -> None:
    """Check Redis schedule config and run pipeline if current time matches.

    Called every minute by arq cron. Checks:
    1. Is the schedule paused? → skip
    2. Does current UTC time match the configured weekdays/hour/minute? → run
    """
    # Deferred imports: app.py imports worker.py at module level (circular),
    # and pipeline_job pulls in heavy scraper/enrichment deps.
    from compgraph.scheduler.app import (
        PAUSE_REDIS_KEY,
        SCHEDULE_ID,
        get_schedule_config,
    )

    redis = ctx["redis"]
    if await redis.get(f"{PAUSE_REDIS_KEY}{SCHEDULE_ID}"):
        return  # paused — silent skip (fires every minute)

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    config = await get_schedule_config(redis)

    if (
        now.weekday() not in config["weekdays"]
        or now.hour != config["hour"]
        or now.minute != config["minute"]
    ):
        return  # not scheduled — silent skip

    logger.info(
        "Schedule matched: weekday=%d hour=%d minute=%d — running pipeline",
        now.weekday(),
        now.hour,
        now.minute,
    )

    from compgraph.scheduler.jobs import pipeline_job

    await pipeline_job()


class WorkerSettings:
    functions = [run_pipeline]
    cron_jobs = [
        cron(
            run_pipeline,
            minute=set(range(60)),  # every minute — schedule logic in run_pipeline
            unique=True,
            timeout=CRON_TIMEOUT_SECONDS,
            run_at_startup=False,
        ),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    # Evaluated at import time — safe because this module is only imported by
    # the arq CLI worker process where env vars are already loaded.
    redis_settings = get_redis_settings()
    max_jobs = 1
    job_timeout = CRON_TIMEOUT_SECONDS
    health_check_interval = 60
    allow_abort_jobs = True
