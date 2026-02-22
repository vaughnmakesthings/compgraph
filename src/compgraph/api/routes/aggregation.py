from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import (
    AggBrandAgencyOverlap,
    AggBrandChurnSignals,
    AggBrandTimeline,
    AggDailyVelocity,
    AggMarketCoverageGaps,
    AggPayBenchmarks,
    AggPostingLifecycle,
)

router = APIRouter(prefix="/api/aggregation", tags=["aggregation"])


class TriggerResponse(BaseModel):
    message: str


@router.get("/velocity")
async def get_velocity(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(
        select(AggDailyVelocity).order_by(AggDailyVelocity.date.desc()).limit(500)
    )
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/brand-timeline")
async def get_brand_timeline(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(select(AggBrandTimeline).limit(500))
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/pay-benchmarks")
async def get_pay_benchmarks(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(select(AggPayBenchmarks).limit(500))
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/lifecycle")
async def get_lifecycle(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(select(AggPostingLifecycle).limit(500))
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/churn-signals")
async def get_churn_signals(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(
        select(AggBrandChurnSignals)
        .order_by(AggBrandChurnSignals.churn_signal_score.desc())
        .limit(100)
    )
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/coverage-gaps")
async def get_coverage_gaps(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(select(AggMarketCoverageGaps).limit(500))
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


@router.get("/agency-overlap")
async def get_agency_overlap(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(
        select(AggBrandAgencyOverlap).order_by(AggBrandAgencyOverlap.agency_count.desc()).limit(100)
    )
    rows = result.scalars().all()
    return [{c.key: getattr(r, c.key) for c in r.__table__.columns} for r in rows]


async def _run_aggregation() -> None:
    from compgraph.aggregation.orchestrator import AggregationOrchestrator

    orchestrator = AggregationOrchestrator()
    await orchestrator.run()


@router.post("/trigger")
async def trigger_aggregation(background_tasks: BackgroundTasks) -> TriggerResponse:
    background_tasks.add_task(_run_aggregation)
    return TriggerResponse(message="Aggregation rebuild started")
