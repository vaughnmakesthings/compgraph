from __future__ import annotations

import logging

from apscheduler import AsyncScheduler, CoalescePolicy, ConflictPolicy
from apscheduler.triggers.cron import CronTrigger

from compgraph.config import settings
from compgraph.scheduler.jobs import pipeline_job

logger = logging.getLogger(__name__)

SCHEDULE_ID = "daily_pipeline"


async def setup_scheduler() -> AsyncScheduler:
    scheduler = AsyncScheduler()

    trigger = CronTrigger(
        day_of_week="mon,wed,fri",
        hour=2,
        minute=0,
        timezone=settings.SCHEDULER_TIMEZONE,
    )

    await scheduler.__aenter__()

    await scheduler.add_schedule(
        pipeline_job,
        trigger,
        id=SCHEDULE_ID,
        coalesce=CoalescePolicy.latest,
        misfire_grace_time=3600,
        conflict_policy=ConflictPolicy.replace,
    )

    logger.info(
        "Scheduler configured: schedule=%s, cron=%s, timezone=%s",
        SCHEDULE_ID,
        settings.SCHEDULER_PIPELINE_CRON,
        settings.SCHEDULER_TIMEZONE,
    )

    return scheduler
