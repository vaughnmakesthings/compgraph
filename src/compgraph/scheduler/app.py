from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from arq import create_pool

from compgraph.config import settings
from compgraph.scheduler.worker import get_redis_settings

if TYPE_CHECKING:
    from arq import ArqRedis

logger = logging.getLogger(__name__)

SCHEDULE_ID = "daily_pipeline"


async def create_arq_pool() -> ArqRedis:
    pool = await create_pool(get_redis_settings())
    logger.info(
        "arq Redis pool created: redis_url=%s, scheduler_enabled=%s",
        settings.REDIS_URL or "redis://localhost:6379",
        settings.SCHEDULER_ENABLED,
    )
    return pool


async def enqueue_pipeline_job(pool: ArqRedis) -> str | None:
    job = await pool.enqueue_job("run_pipeline", _job_id="manual_pipeline_trigger")
    if job is None:
        logger.warning("Pipeline job already queued (duplicate _job_id)")
        return None
    logger.info("Pipeline job enqueued: job_id=%s", job.job_id)
    return job.job_id
