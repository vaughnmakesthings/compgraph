from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from compgraph.aggregation.agency_overlap import BrandAgencyOverlapJob
from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.brand_churn import BrandChurnSignalsJob
from compgraph.aggregation.brand_timeline import BrandTimelineJob
from compgraph.aggregation.coverage_gaps import MarketCoverageGapsJob
from compgraph.aggregation.daily_velocity import DailyVelocityJob
from compgraph.aggregation.pay_benchmarks import PayBenchmarksJob
from compgraph.aggregation.posting_lifecycle import PostingLifecycleJob
from compgraph.db.session import async_session_factory

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    succeeded: dict[str, int] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


class AggregationOrchestrator:
    def __init__(self) -> None:
        self.jobs: list[AggregationJob] = [
            DailyVelocityJob(),
            BrandTimelineJob(),
            PostingLifecycleJob(),
            BrandChurnSignalsJob(),
            BrandAgencyOverlapJob(),
            PayBenchmarksJob(),
            MarketCoverageGapsJob(),
        ]

    async def run(self) -> AggregationResult:
        result = AggregationResult()
        logger.info("[AGG] Starting aggregation run (%d jobs)", len(self.jobs))

        for job in self.jobs:
            try:
                async with async_session_factory() as session:
                    count = await job.run(session)
                result.succeeded[job.table_name] = count
                logger.info("[AGG] %s: OK (%d rows)", job.table_name, count)
            except Exception as exc:
                result.failed[job.table_name] = str(exc)
                logger.exception("[AGG] %s: FAILED", job.table_name)

        result.finished_at = datetime.now(UTC)
        logger.info(
            "[AGG] Run complete: %d succeeded, %d failed",
            len(result.succeeded),
            len(result.failed),
        )
        return result
