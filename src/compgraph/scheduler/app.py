from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from arq import create_pool

from compgraph.config import settings
from compgraph.scheduler.worker import (
    CRON_HOUR,
    CRON_MINUTE,
    CRON_WEEKDAYS,
    get_redis_settings,
)

if TYPE_CHECKING:
    from arq import ArqRedis

logger = logging.getLogger(__name__)

SCHEDULE_ID = "daily_pipeline"
PAUSE_REDIS_KEY = "schedule:paused:"
SCHEDULE_CONFIG_KEY = "schedule:config:"
LAST_FIRE_REDIS_KEY = "schedule:last_fire:"

# Day name mapping for API readability
_DAY_NAMES = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
_DAY_NUMBERS = {v: k for k, v in _DAY_NAMES.items()}

DEFAULT_SCHEDULE_CONFIG: dict[str, Any] = {
    "weekdays": sorted(CRON_WEEKDAYS),
    "hour": CRON_HOUR,
    "minute": CRON_MINUTE,
}


async def get_schedule_config(pool: ArqRedis) -> dict[str, Any]:
    """Read schedule config from Redis, falling back to defaults."""
    raw = await pool.get(f"{SCHEDULE_CONFIG_KEY}{SCHEDULE_ID}")
    if raw is None:
        return dict(DEFAULT_SCHEDULE_CONFIG)
    return json.loads(raw)  # type: ignore[no-any-return]


async def set_schedule_config(pool: ArqRedis, config: dict[str, Any]) -> None:
    """Persist schedule config to Redis."""
    await pool.set(f"{SCHEDULE_CONFIG_KEY}{SCHEDULE_ID}", json.dumps(config))


async def create_arq_pool() -> ArqRedis:
    pool = await create_pool(get_redis_settings())
    logger.info(
        "arq Redis pool created: scheduler_enabled=%s",
        settings.SCHEDULER_ENABLED,
    )
    return pool


async def enqueue_pipeline_job(pool: ArqRedis) -> str | None:
    job = await pool.enqueue_job("run_pipeline_manual", _job_id="manual_pipeline_trigger")
    if job is None:
        logger.warning("Pipeline job already queued (duplicate _job_id)")
        return None
    logger.info("Pipeline job enqueued: job_id=%s", job.job_id)
    return job.job_id
