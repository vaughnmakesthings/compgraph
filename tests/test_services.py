"""Tests for the service layer — PostingService, AggregationService, CompanyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from compgraph.enrichment.constants import ENRICHMENT_VERSION_PASS2
from compgraph.services.aggregation_service import AggregationService, _model_to_dict
from compgraph.services.company_service import CompanyService
from compgraph.services.posting_service import (
    SORT_BY_ALLOWED,
    PostingService,
    _build_filters,
    _escape_like,
)

# --- Helpers ---


def _make_posting(
    posting_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> MagicMock:
    p = MagicMock()
    p.id = posting_id or uuid.uuid4()
    p.company_id = company_id or uuid.uuid4()
    p.external_job_id = "EXT-001"
    p.is_active = is_active
    p.times_reposted = 0
    p.first_seen_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    p.last_seen_at = datetime(2024, 2, 1, 12, 0, 0, tzinfo=UTC)
    return p


def _make_list_row(posting: MagicMock) -> tuple:
    return (
        posting,
        "field_sales",
        18.0,
        24.0,
        "USD",
        "full_time",
        "Field Sales Rep",
        "Atlanta, GA",
        "Test Company",
        "test-company",
    )


def _make_mock_db_for_list(rows: list, total: int) -> AsyncMock:
    mock_session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    rows_result = MagicMock()
    rows_result.all.return_value = rows
    mock_session.execute = AsyncMock(side_effect=[count_result, rows_result])
    return mock_session


def _make_detail_mock(
    posting: MagicMock | None,
    enrichment: MagicMock | None = None,
    snapshot: MagicMock | None = None,
    mention_rows: list | None = None,
) -> AsyncMock:
    mock_session = AsyncMock()
    posting_result = MagicMock()
    posting_result.scalar_one_or_none.return_value = posting
    enrichment_result = MagicMock()
    enrichment_result.scalar_one_or_none.return_value = enrichment
    snapshot_result = MagicMock()
    snapshot_result.scalar_one_or_none.return_value = snapshot
    mentions_result = MagicMock()
    mentions_result.all.return_value = mention_rows or []
    mock_session.execute = AsyncMock(
        side_effect=[posting_result, enrichment_result, snapshot_result, mentions_result]
    )
    return mock_session


# --- PostingService Tests ---


class TestPostingServiceListPostings:
    @pytest.mark.asyncio
    async def test_returns_empty_list_and_zero_total(self) -> None:
        db = _make_mock_db_for_list(rows=[], total=0)
        items, total = await PostingService.list_postings(db)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_returns_items_with_correct_fields(self) -> None:
        posting = _make_posting()
        row = _make_list_row(posting)
        db = _make_mock_db_for_list(rows=[row], total=1)

        items, total = await PostingService.list_postings(db)
        assert total == 1
        assert len(items) == 1
        item = items[0]
        assert item["id"] == posting.id
        assert item["company_name"] == "Test Company"
        assert item["title"] == "Field Sales Rep"
        assert item["role_archetype"] == "field_sales"
        assert item["pay_min"] == 18.0
        assert item["pay_max"] == 24.0

    @pytest.mark.asyncio
    async def test_pagination_params_passed_through(self) -> None:
        db = _make_mock_db_for_list(rows=[], total=50)
        items, total = await PostingService.list_postings(db, limit=10, offset=20)
        assert total == 50
        assert items == []
        # Verify execute was called twice (count + data)
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_items(self) -> None:
        postings = [_make_posting() for _ in range(3)]
        rows = [_make_list_row(p) for p in postings]
        db = _make_mock_db_for_list(rows=rows, total=3)
        items, total = await PostingService.list_postings(db)
        assert total == 3
        assert len(items) == 3


class TestPostingServiceGetPosting:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        db = _make_detail_mock(posting=None)
        result = await PostingService.get_posting(db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_full_detail(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)
        enrichment = MagicMock()
        enrichment.id = uuid.uuid4()
        enrichment.title_normalized = "Field Sales Rep"
        enrichment.role_archetype = "field_sales"
        enrichment.role_level = "ic"
        enrichment.pay_type = "hourly"
        enrichment.pay_min = 18.0
        enrichment.pay_max = 24.0
        enrichment.pay_currency = "USD"
        enrichment.pay_frequency = "hourly"
        enrichment.employment_type = "full_time"
        enrichment.commission_mentioned = False
        enrichment.benefits_mentioned = True
        enrichment.enrichment_version = ENRICHMENT_VERSION_PASS2
        enrichment.enriched_at = datetime(2024, 1, 16, tzinfo=UTC)

        snapshot = MagicMock()
        snapshot.title_raw = "Field Sales Rep - Samsung"
        snapshot.location_raw = "Atlanta, GA"
        snapshot.url = "https://example.com/job/123"

        mention = MagicMock()
        mention.id = uuid.uuid4()
        mention.entity_name = "Samsung"
        mention.entity_type = "brand"
        mention.confidence_score = 0.95
        brand_id = uuid.uuid4()
        brand_name = "Samsung"

        db = _make_detail_mock(
            posting=posting,
            enrichment=enrichment,
            snapshot=snapshot,
            mention_rows=[(mention, brand_id, brand_name)],
        )

        result = await PostingService.get_posting(db, posting_id)
        assert result is not None
        assert result["id"] == posting_id
        assert result["title"] == "Field Sales Rep - Samsung"
        assert result["enrichment"]["role_archetype"] == "field_sales"
        assert len(result["brand_mentions"]) == 1
        assert result["brand_mentions"][0]["brand_name"] == "Samsung"

    @pytest.mark.asyncio
    async def test_returns_null_fields_when_no_enrichment(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)
        db = _make_detail_mock(posting=posting)
        result = await PostingService.get_posting(db, posting_id)
        assert result is not None
        assert result["enrichment"] is None
        assert result["brand_mentions"] == []
        assert result["title"] is None


# --- PostingService Helpers ---


class TestPostingServiceHelpers:
    def test_escape_like(self) -> None:
        assert _escape_like("test_file") == "test\\_file"
        assert _escape_like("50%") == "50\\%"
        assert _escape_like("a%b_c") == "a\\%b\\_c"

    def test_sort_by_allowed_values(self) -> None:
        expected = {"first_seen_desc", "first_seen_asc", "pay_desc", "pay_asc", "title_asc"}
        assert SORT_BY_ALLOWED == expected

    def test_build_filters_no_params(self) -> None:
        filters, needs_snapshot = _build_filters(None, None, None, None)
        assert filters == []
        assert needs_snapshot is False

    def test_build_filters_with_search(self) -> None:
        filters, needs_snapshot = _build_filters(None, None, None, "samsung")
        assert needs_snapshot is True
        assert len(filters) == 1

    def test_build_filters_with_company_id(self) -> None:
        cid = uuid.uuid4()
        filters, needs_snapshot = _build_filters(cid, None, None, None)
        assert len(filters) == 1
        assert needs_snapshot is False


# --- AggregationService Tests ---


class TestAggregationService:
    @pytest.mark.asyncio
    async def test_get_pay_benchmarks_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_pay_benchmarks(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_lifecycle_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_lifecycle(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_churn_signals_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_churn_signals(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_coverage_gaps_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_coverage_gaps(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agency_overlap_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_agency_overlap(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_velocity_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_velocity(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_brand_timeline_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await AggregationService.get_brand_timeline(db)
        assert result == []


class TestModelToDict:
    def test_serializes_model_columns(self) -> None:
        mock_model = MagicMock()
        col1 = MagicMock()
        col1.key = "id"
        col2 = MagicMock()
        col2.key = "name"
        mock_model.__table__ = MagicMock()
        mock_model.__table__.columns = [col1, col2]

        row = MagicMock()
        row.id = "test-id"
        row.name = "test-name"

        result = _model_to_dict(row, mock_model)
        assert result == {"id": "test-id", "name": "test-name"}


# --- CompanyService Tests ---


class TestCompanyService:
    @pytest.mark.asyncio
    async def test_list_companies_empty(self) -> None:
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        result = await CompanyService.list_companies(db)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_companies_returns_dicts(self) -> None:
        company = MagicMock()
        company.id = uuid.uuid4()
        company.name = "Acme Corp"
        company.slug = "acme-corp"
        company.ats_platform = "icims"

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [company]
        db.execute = AsyncMock(return_value=result_mock)

        result = await CompanyService.list_companies(db)
        assert len(result) == 1
        assert result[0]["name"] == "Acme Corp"
        assert result[0]["slug"] == "acme-corp"
        assert result[0]["id"] == str(company.id)
