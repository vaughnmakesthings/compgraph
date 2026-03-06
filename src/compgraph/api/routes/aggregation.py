from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.api.schemas.aggregation import (
    AgencyOverlapItem,
    BrandTimelineItem,
    ChurnSignalItem,
    CoverageGapItem,
    LifecycleItem,
    PayBenchmarkItem,
    VelocityItem,
)
from compgraph.auth.dependencies import AuthUser, require_admin, require_viewer
from compgraph.services.aggregation_service import AggregationService

router = APIRouter(prefix="/aggregation", tags=["aggregation"])

CACHE_CONTROL_5MIN = "public, max-age=300"


class TriggerResponse(BaseModel):
    message: str


@router.get("/velocity", response_model=list[VelocityItem])
async def get_velocity(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_velocity(db)


@router.get("/brand-timeline", response_model=list[BrandTimelineItem])
async def get_brand_timeline(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_brand_timeline(db)


@router.get("/pay-benchmarks", response_model=list[PayBenchmarkItem])
async def get_pay_benchmarks(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_pay_benchmarks(db)


@router.get("/lifecycle", response_model=list[LifecycleItem])
async def get_lifecycle(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_lifecycle(db)


@router.get("/churn-signals", response_model=list[ChurnSignalItem])
async def get_churn_signals(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_churn_signals(db)


@router.get("/coverage-gaps", response_model=list[CoverageGapItem])
async def get_coverage_gaps(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_coverage_gaps(db)


@router.get("/agency-overlap", response_model=list[AgencyOverlapItem])
async def get_agency_overlap(
    response: Response,
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    response.headers["Cache-Control"] = CACHE_CONTROL_5MIN
    return await AggregationService.get_agency_overlap(db)


async def _run_aggregation() -> None:
    from compgraph.aggregation.orchestrator import AggregationOrchestrator

    orchestrator = AggregationOrchestrator()
    await orchestrator.run()


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_aggregation(
    background_tasks: BackgroundTasks,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> TriggerResponse:
    background_tasks.add_task(_run_aggregation)
    return TriggerResponse(message="Aggregation rebuild started")
