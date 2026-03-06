"""Service layer for aggregation queries — extracted from api/routes/aggregation.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import (
    AggBrandAgencyOverlap,
    AggBrandChurnSignals,
    AggBrandTimeline,
    AggDailyVelocity,
    AggMarketCoverageGaps,
    AggPayBenchmarks,
    AggPostingLifecycle,
    Brand,
    Company,
)


def _model_to_dict(row, model) -> dict:
    """Serialize a SQLAlchemy model instance to a dict using column keys."""
    return {c.key: getattr(row, c.key) for c in model.__table__.columns}


class AggregationService:
    """Encapsulates all aggregation-table read queries."""

    @staticmethod
    async def get_velocity(db: AsyncSession, *, days: int = 30) -> list[dict]:
        cutoff = datetime.now(UTC).date() - timedelta(days=days)
        stmt = (
            select(
                AggDailyVelocity,
                Company.name.label("company_name"),
                Company.slug.label("company_slug"),
            )
            .join(Company, AggDailyVelocity.company_id == Company.id)
            .where(AggDailyVelocity.date >= cutoff)
            .order_by(AggDailyVelocity.date.desc())
        )
        result = await db.execute(stmt)
        return [
            {
                **_model_to_dict(row.AggDailyVelocity, AggDailyVelocity),
                "company_name": row.company_name,
                "company_slug": row.company_slug,
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_brand_timeline(db: AsyncSession) -> list[dict]:
        stmt = (
            select(
                AggBrandTimeline,
                Brand.name.label("brand_name"),
                Company.name.label("company_name"),
                Company.slug.label("company_slug"),
            )
            .join(Brand, AggBrandTimeline.brand_id == Brand.id)
            .join(Company, AggBrandTimeline.company_id == Company.id)
            .limit(500)
        )
        result = await db.execute(stmt)
        return [
            {
                **_model_to_dict(row.AggBrandTimeline, AggBrandTimeline),
                "brand_name": row.brand_name,
                "company_name": row.company_name,
                "company_slug": row.company_slug,
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_pay_benchmarks(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(AggPayBenchmarks).limit(500))
        return [_model_to_dict(r, AggPayBenchmarks) for r in result.scalars().all()]

    @staticmethod
    async def get_lifecycle(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(AggPostingLifecycle).limit(500))
        return [_model_to_dict(r, AggPostingLifecycle) for r in result.scalars().all()]

    @staticmethod
    async def get_churn_signals(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AggBrandChurnSignals)
            .order_by(AggBrandChurnSignals.churn_signal_score.desc())
            .limit(100)
        )
        return [_model_to_dict(r, AggBrandChurnSignals) for r in result.scalars().all()]

    @staticmethod
    async def get_coverage_gaps(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(AggMarketCoverageGaps).limit(500))
        return [_model_to_dict(r, AggMarketCoverageGaps) for r in result.scalars().all()]

    @staticmethod
    async def get_agency_overlap(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AggBrandAgencyOverlap)
            .order_by(AggBrandAgencyOverlap.agency_count.desc())
            .limit(100)
        )
        return [_model_to_dict(r, AggBrandAgencyOverlap) for r in result.scalars().all()]
