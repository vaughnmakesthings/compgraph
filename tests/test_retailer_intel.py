from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from compgraph.api.schemas.aggregation import (
    AgencyOverlapItem,
    BrandTimelineItem,
    ChurnSignalItem,
    CoverageGapItem,
    LifecycleItem,
    PayBenchmarkItem,
    VelocityItem,
)
from compgraph.services.aggregation_service import AggregationService, _model_to_dict


def _make_agg_model_row(model_class, **overrides):
    row = MagicMock()
    for col in model_class.__table__.columns:
        setattr(row, col.key, overrides.get(col.key))
    if "id" not in overrides:
        row.id = uuid.uuid4()
    return row


def _make_velocity_row(
    company_id: uuid.UUID | None = None,
    dt: date | None = None,
    active: int = 10,
    new: int = 3,
    closed: int = 1,
) -> MagicMock:
    from compgraph.db.models import AggDailyVelocity

    row = MagicMock()
    vel = _make_agg_model_row(
        AggDailyVelocity,
        company_id=company_id or uuid.uuid4(),
        date=dt or date.today(),
        brand_id=None,
        market_id=None,
        active_postings=active,
        new_postings=new,
        closed_postings=closed,
        net_change=new - closed,
    )
    row.AggDailyVelocity = vel
    row.company_name = "Test Company"
    row.company_slug = "test-company"
    return row


def _make_brand_timeline_row(
    company_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    is_active: bool = True,
    total: int = 50,
    current: int = 10,
    peak: int = 20,
) -> MagicMock:
    from compgraph.db.models import AggBrandTimeline

    row = MagicMock()
    bt = _make_agg_model_row(
        AggBrandTimeline,
        company_id=company_id or uuid.uuid4(),
        brand_id=brand_id or uuid.uuid4(),
        first_seen_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2024, 6, 1, tzinfo=UTC),
        is_currently_active=is_active,
        total_postings_all_time=total,
        current_active_postings=current,
        peak_active_postings=peak,
        peak_date=date(2024, 3, 15),
    )
    row.AggBrandTimeline = bt
    row.brand_name = "Samsung"
    row.company_name = "Test Company"
    row.company_slug = "test-company"
    return row


def _scalars_mock(items: list) -> MagicMock:
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = items
    return result_mock


def _rows_mock(items: list) -> MagicMock:
    result_mock = MagicMock()
    result_mock.all.return_value = items
    return result_mock


# ---------------------------------------------------------------------------
# AggregationService.get_velocity
# ---------------------------------------------------------------------------


class TestGetVelocity:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        row = _make_velocity_row(active=25, new=5, closed=2)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock([row]))

        result = await AggregationService.get_velocity(db)

        assert len(result) == 1
        assert result[0]["company_name"] == "Test Company"
        assert result[0]["company_slug"] == "test-company"

    @pytest.mark.asyncio
    async def test_days_clamped_to_minimum_1(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock([]))
        await AggregationService.get_velocity(db, days=0)
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_days_clamped_to_maximum_365(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock([]))
        await AggregationService.get_velocity(db, days=9999)
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_companies(self) -> None:
        rows = [
            _make_velocity_row(active=10),
            _make_velocity_row(active=20),
        ]
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock(rows))

        result = await AggregationService.get_velocity(db)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# AggregationService.get_brand_timeline
# ---------------------------------------------------------------------------


class TestGetBrandTimeline:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        row = _make_brand_timeline_row()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock([row]))

        result = await AggregationService.get_brand_timeline(db)

        assert len(result) == 1
        assert result[0]["brand_name"] == "Samsung"
        assert result[0]["company_name"] == "Test Company"

    @pytest.mark.asyncio
    async def test_inactive_brand_relationship(self) -> None:
        row = _make_brand_timeline_row(is_active=False, current=0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock([row]))

        result = await AggregationService.get_brand_timeline(db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_multiple_brands_same_company(self) -> None:
        cid = uuid.uuid4()
        rows = [
            _make_brand_timeline_row(company_id=cid, brand_id=uuid.uuid4()),
            _make_brand_timeline_row(company_id=cid, brand_id=uuid.uuid4()),
        ]
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_rows_mock(rows))

        result = await AggregationService.get_brand_timeline(db)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# AggregationService.get_pay_benchmarks
# ---------------------------------------------------------------------------


class TestGetPayBenchmarks:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        from compgraph.db.models import AggPayBenchmarks

        item = _make_agg_model_row(
            AggPayBenchmarks,
            company_id=uuid.uuid4(),
            role_archetype="field_sales",
            market_id=None,
            brand_id=None,
            period=date(2024, 6, 1),
            avg_pay_min=18.0,
            avg_pay_max=24.0,
            median_pay_min=17.0,
            median_pay_max=23.0,
            sample_size=42,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_pay_benchmarks(db)
        assert len(result) == 1
        assert result[0]["avg_pay_min"] == 18.0
        assert result[0]["sample_size"] == 42

    @pytest.mark.asyncio
    async def test_null_pay_values(self) -> None:
        from compgraph.db.models import AggPayBenchmarks

        item = _make_agg_model_row(
            AggPayBenchmarks,
            company_id=uuid.uuid4(),
            role_archetype=None,
            market_id=None,
            brand_id=None,
            period=date(2024, 6, 1),
            avg_pay_min=None,
            avg_pay_max=None,
            median_pay_min=None,
            median_pay_max=None,
            sample_size=0,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_pay_benchmarks(db)
        assert len(result) == 1
        assert result[0]["avg_pay_min"] is None
        assert result[0]["sample_size"] == 0


# ---------------------------------------------------------------------------
# AggregationService.get_lifecycle
# ---------------------------------------------------------------------------


class TestGetLifecycle:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        from compgraph.db.models import AggPostingLifecycle

        item = _make_agg_model_row(
            AggPostingLifecycle,
            company_id=uuid.uuid4(),
            role_archetype="field_sales",
            brand_id=None,
            market_id=None,
            period=date(2024, 6, 1),
            avg_days_open=14.5,
            median_days_open=12.0,
            repost_rate=0.15,
            avg_repost_gap_days=7.0,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_lifecycle(db)
        assert len(result) == 1
        assert result[0]["avg_days_open"] == 14.5
        assert result[0]["repost_rate"] == 0.15

    @pytest.mark.asyncio
    async def test_null_lifecycle_values(self) -> None:
        from compgraph.db.models import AggPostingLifecycle

        item = _make_agg_model_row(
            AggPostingLifecycle,
            company_id=uuid.uuid4(),
            role_archetype=None,
            brand_id=None,
            market_id=None,
            period=date(2024, 6, 1),
            avg_days_open=None,
            median_days_open=None,
            repost_rate=None,
            avg_repost_gap_days=None,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_lifecycle(db)
        assert len(result) == 1
        assert result[0]["avg_days_open"] is None


# ---------------------------------------------------------------------------
# AggregationService.get_churn_signals
# ---------------------------------------------------------------------------


class TestGetChurnSignals:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        from compgraph.db.models import AggBrandChurnSignals

        item = _make_agg_model_row(
            AggBrandChurnSignals,
            company_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            active_posting_count=20,
            prior_period_count=30,
            velocity_delta=-0.33,
            avg_days_active=45.0,
            repost_rate=0.2,
            churn_signal_score=0.75,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_churn_signals(db)
        assert len(result) == 1
        assert result[0]["churn_signal_score"] == 0.75
        assert result[0]["velocity_delta"] == -0.33

    @pytest.mark.asyncio
    async def test_zero_churn_score(self) -> None:
        from compgraph.db.models import AggBrandChurnSignals

        item = _make_agg_model_row(
            AggBrandChurnSignals,
            company_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            active_posting_count=10,
            prior_period_count=10,
            velocity_delta=0.0,
            avg_days_active=30.0,
            repost_rate=0.0,
            churn_signal_score=0.0,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_churn_signals(db)
        assert result[0]["churn_signal_score"] == 0.0


# ---------------------------------------------------------------------------
# AggregationService.get_coverage_gaps
# ---------------------------------------------------------------------------


class TestGetCoverageGaps:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        from compgraph.db.models import AggMarketCoverageGaps

        item = _make_agg_model_row(
            AggMarketCoverageGaps,
            company_id=uuid.uuid4(),
            market_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            total_active_postings=5,
            brand_count=2,
            brand_names=["Samsung", "LG"],
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_coverage_gaps(db)
        assert len(result) == 1
        assert result[0]["brand_count"] == 2
        assert result[0]["brand_names"] == ["Samsung", "LG"]

    @pytest.mark.asyncio
    async def test_null_brand_names(self) -> None:
        from compgraph.db.models import AggMarketCoverageGaps

        item = _make_agg_model_row(
            AggMarketCoverageGaps,
            company_id=uuid.uuid4(),
            market_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            total_active_postings=0,
            brand_count=0,
            brand_names=None,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_coverage_gaps(db)
        assert result[0]["brand_names"] is None
        assert result[0]["brand_count"] == 0


# ---------------------------------------------------------------------------
# AggregationService.get_agency_overlap
# ---------------------------------------------------------------------------


class TestGetAgencyOverlap:
    @pytest.mark.asyncio
    async def test_returns_populated_data(self) -> None:
        from compgraph.db.models import AggBrandAgencyOverlap

        item = _make_agg_model_row(
            AggBrandAgencyOverlap,
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            agency_count=3,
            agency_names=["Advantage", "BDS", "MarketSource"],
            primary_company_id=uuid.uuid4(),
            primary_share=0.6,
            is_exclusive=False,
            is_contested=True,
            total_postings=45,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_agency_overlap(db)
        assert len(result) == 1
        assert result[0]["agency_count"] == 3
        assert result[0]["is_contested"] is True
        assert result[0]["is_exclusive"] is False
        assert result[0]["total_postings"] == 45

    @pytest.mark.asyncio
    async def test_exclusive_brand(self) -> None:
        from compgraph.db.models import AggBrandAgencyOverlap

        item = _make_agg_model_row(
            AggBrandAgencyOverlap,
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            agency_count=1,
            agency_names=["Advantage"],
            primary_company_id=uuid.uuid4(),
            primary_share=1.0,
            is_exclusive=True,
            is_contested=False,
            total_postings=20,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_agency_overlap(db)
        assert result[0]["is_exclusive"] is True
        assert result[0]["primary_share"] == 1.0

    @pytest.mark.asyncio
    async def test_null_primary_company(self) -> None:
        from compgraph.db.models import AggBrandAgencyOverlap

        item = _make_agg_model_row(
            AggBrandAgencyOverlap,
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            agency_count=0,
            agency_names=None,
            primary_company_id=None,
            primary_share=None,
            is_exclusive=False,
            is_contested=False,
            total_postings=0,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalars_mock([item]))

        result = await AggregationService.get_agency_overlap(db)
        assert result[0]["primary_company_id"] is None
        assert result[0]["primary_share"] is None


# ---------------------------------------------------------------------------
# _model_to_dict edge cases
# ---------------------------------------------------------------------------


class TestModelToDictEdgeCases:
    def test_none_values_preserved(self) -> None:
        mock_model = MagicMock()
        col = MagicMock()
        col.key = "optional_field"
        mock_model.__table__ = MagicMock()
        mock_model.__table__.columns = [col]

        row = MagicMock()
        row.optional_field = None

        result = _model_to_dict(row, mock_model)
        assert result == {"optional_field": None}

    def test_empty_model_returns_empty_dict(self) -> None:
        mock_model = MagicMock()
        mock_model.__table__ = MagicMock()
        mock_model.__table__.columns = []

        row = MagicMock()
        result = _model_to_dict(row, mock_model)
        assert result == {}

    def test_uuid_values_preserved(self) -> None:
        mock_model = MagicMock()
        col = MagicMock()
        col.key = "id"
        mock_model.__table__ = MagicMock()
        mock_model.__table__.columns = [col]

        uid = uuid.uuid4()
        row = MagicMock()
        row.id = uid

        result = _model_to_dict(row, mock_model)
        assert result["id"] == uid

    def test_multiple_columns(self) -> None:
        mock_model = MagicMock()
        cols = []
        for key in ["id", "name", "count", "is_active"]:
            c = MagicMock()
            c.key = key
            cols.append(c)
        mock_model.__table__ = MagicMock()
        mock_model.__table__.columns = cols

        row = MagicMock()
        row.id = uuid.uuid4()
        row.name = "test"
        row.count = 42
        row.is_active = True

        result = _model_to_dict(row, mock_model)
        assert len(result) == 4
        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["is_active"] is True


# ---------------------------------------------------------------------------
# Schema validation tests — ensure Pydantic models accept/reject edge cases
# ---------------------------------------------------------------------------


class TestAggregationSchemaValidation:
    def test_velocity_item_accepts_null_brand_and_market(self) -> None:
        item = VelocityItem(
            id=uuid.uuid4(),
            date=date(2024, 6, 1),
            company_id=uuid.uuid4(),
            brand_id=None,
            market_id=None,
            active_postings=10,
            new_postings=3,
            closed_postings=1,
            net_change=2,
            company_name="Test",
            company_slug="test",
        )
        assert item.brand_id is None
        assert item.market_id is None

    def test_brand_timeline_item_requires_brand_id(self) -> None:
        item = BrandTimelineItem(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            first_seen_at=None,
            last_seen_at=None,
            is_currently_active=False,
            total_postings_all_time=0,
            current_active_postings=0,
            peak_active_postings=0,
            peak_date=None,
            brand_name="Samsung",
            company_name="Test",
            company_slug="test",
        )
        assert item.brand_id is not None
        assert item.first_seen_at is None
        assert item.peak_date is None

    def test_pay_benchmark_item_accepts_all_nulls(self) -> None:
        item = PayBenchmarkItem(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            role_archetype=None,
            market_id=None,
            brand_id=None,
            period=date(2024, 6, 1),
            avg_pay_min=None,
            avg_pay_max=None,
            median_pay_min=None,
            median_pay_max=None,
            sample_size=0,
        )
        assert item.avg_pay_min is None
        assert item.sample_size == 0

    def test_lifecycle_item_accepts_all_nulls(self) -> None:
        item = LifecycleItem(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            role_archetype=None,
            brand_id=None,
            market_id=None,
            period=date(2024, 6, 1),
            avg_days_open=None,
            median_days_open=None,
            repost_rate=None,
            avg_repost_gap_days=None,
        )
        assert item.avg_days_open is None
        assert item.repost_rate is None

    def test_churn_signal_item_negative_velocity_delta(self) -> None:
        item = ChurnSignalItem(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            active_posting_count=5,
            prior_period_count=15,
            velocity_delta=-0.67,
            avg_days_active=60.0,
            repost_rate=0.3,
            churn_signal_score=0.9,
        )
        assert item.velocity_delta == -0.67

    def test_coverage_gap_item_empty_brand_list(self) -> None:
        item = CoverageGapItem(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            market_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            total_active_postings=0,
            brand_count=0,
            brand_names=[],
        )
        assert item.brand_names == []

    def test_agency_overlap_contested_and_exclusive_mutually_exclusive_in_practice(self) -> None:
        contested = AgencyOverlapItem(
            id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            agency_count=3,
            agency_names=["A", "B", "C"],
            primary_company_id=uuid.uuid4(),
            primary_share=0.4,
            is_exclusive=False,
            is_contested=True,
            total_postings=30,
        )
        assert contested.is_contested is True
        assert contested.is_exclusive is False

        exclusive = AgencyOverlapItem(
            id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2024, 6, 1),
            agency_count=1,
            agency_names=["A"],
            primary_company_id=uuid.uuid4(),
            primary_share=1.0,
            is_exclusive=True,
            is_contested=False,
            total_postings=10,
        )
        assert exclusive.is_exclusive is True
        assert exclusive.is_contested is False
