from __future__ import annotations

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from compgraph.config import settings

logger = logging.getLogger(__name__)

CRON_WEEKDAYS = {0, 2, 4}  # Mon, Wed, Fri
CRON_HOUR = 2
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
    from compgraph.scheduler.jobs import pipeline_job

    await pipeline_job()


class WorkerSettings:
    functions = [run_pipeline]
    cron_jobs = [
        cron(
            run_pipeline,
            hour={CRON_HOUR},
            minute={CRON_MINUTE},
            weekday=CRON_WEEKDAYS,
            unique=True,
            timeout=CRON_TIMEOUT_SECONDS,
            run_at_startup=False,
        ),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = get_redis_settings()
    max_jobs = 1
    job_timeout = CRON_TIMEOUT_SECONDS
    health_check_interval = 60
    allow_abort_jobs = True
