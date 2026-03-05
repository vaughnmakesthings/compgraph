from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.auth.dependencies import AuthUser, require_admin, require_viewer
from compgraph.services.aggregation_service import AggregationService

router = APIRouter(prefix="/aggregation", tags=["aggregation"])


class TriggerResponse(BaseModel):
    message: str


@router.get("/velocity")
async def get_velocity(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_velocity(db)


@router.get("/brand-timeline")
async def get_brand_timeline(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_brand_timeline(db)


@router.get("/pay-benchmarks")
async def get_pay_benchmarks(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_pay_benchmarks(db)


@router.get("/lifecycle")
async def get_lifecycle(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_lifecycle(db)


@router.get("/churn-signals")
async def get_churn_signals(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_churn_signals(db)


@router.get("/coverage-gaps")
async def get_coverage_gaps(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_coverage_gaps(db)


@router.get("/agency-overlap")
async def get_agency_overlap(
    _user: AuthUser = Depends(require_viewer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    return await AggregationService.get_agency_overlap(db)


async def _run_aggregation() -> None:
    from compgraph.aggregation.orchestrator import AggregationOrchestrator

    orchestrator = AggregationOrchestrator()
    await orchestrator.run()


@router.post("/trigger")
async def trigger_aggregation(
    background_tasks: BackgroundTasks,
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
) -> TriggerResponse:
    background_tasks.add_task(_run_aggregation)
    return TriggerResponse(message="Aggregation rebuild started")
