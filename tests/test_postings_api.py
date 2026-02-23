from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


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


def _make_enrichment(posting_id: uuid.UUID) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.posting_id = posting_id
    e.title_normalized = "Field Sales Representative"
    e.role_archetype = "field_sales"
    e.role_level = "individual_contributor"
    e.pay_type = "hourly"
    e.pay_min = 18.0
    e.pay_max = 24.0
    e.pay_currency = "USD"
    e.pay_frequency = "hourly"
    e.employment_type = "full_time"
    e.commission_mentioned = False
    e.benefits_mentioned = True
    e.enrichment_version = "pass2"
    e.enriched_at = datetime(2024, 1, 16, 8, 0, 0, tzinfo=UTC)
    return e


def _make_brand_mention(posting_id: uuid.UUID) -> tuple[MagicMock, uuid.UUID, str]:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.posting_id = posting_id
    m.entity_name = "Samsung"
    m.entity_type = "brand"
    m.confidence_score = 0.95
    m.resolved_brand_id = uuid.uuid4()
    brand_id = m.resolved_brand_id
    brand_name = "Samsung"
    return m, brand_id, brand_name


def _make_snapshot(posting_id: uuid.UUID) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.posting_id = posting_id
    s.title_raw = "Field Sales Rep - Samsung"
    s.location_raw = "Atlanta, GA"
    s.url = "https://careers.example.com/jobs/123"
    s.snapshot_date = "2024-02-01"
    return s


def _make_list_row(
    posting: MagicMock,
    role_archetype: str | None = "field_sales",
    pay_min: float | None = 18.0,
    pay_max: float | None = 24.0,
    employment_type: str | None = "full_time",
    title_raw: str | None = "Field Sales Rep",
    location_raw: str | None = "Atlanta, GA",
) -> tuple:
    return (posting, role_archetype, pay_min, pay_max, employment_type, title_raw, location_raw)


def _make_mock_db_for_list(rows: list, total: int) -> AsyncMock:
    mock_session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = total

    rows_result = MagicMock()
    rows_result.all.return_value = rows

    mock_session.execute = AsyncMock(side_effect=[count_result, rows_result])
    return mock_session


class TestPostingsListEndpoint:
    def test_list_returns_empty_when_no_postings(self) -> None:
        mock_session = _make_mock_db_for_list(rows=[], total=0)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_returns_items_with_enrichment_data(self) -> None:
        posting = _make_posting()
        row = _make_list_row(posting)
        mock_session = _make_mock_db_for_list(rows=[row], total=1)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["id"] == str(posting.id)
        assert item["company_id"] == str(posting.company_id)
        assert item["title"] == "Field Sales Rep"
        assert item["location"] == "Atlanta, GA"
        assert item["is_active"] is True
        assert item["role_archetype"] == "field_sales"
        assert item["pay_min"] == 18.0
        assert item["pay_max"] == 24.0
        assert item["employment_type"] == "full_time"

    def test_list_item_with_no_enrichment_returns_none_fields(self) -> None:
        posting = _make_posting()
        row = _make_list_row(
            posting,
            role_archetype=None,
            pay_min=None,
            pay_max=None,
            employment_type=None,
        )
        mock_session = _make_mock_db_for_list(rows=[row], total=1)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        item = r.json()["items"][0]
        assert item["role_archetype"] is None
        assert item["pay_min"] is None
        assert item["pay_max"] is None

    def test_list_filters_by_company_id(self) -> None:
        company_id = uuid.uuid4()
        posting = _make_posting(company_id=company_id)
        row = _make_list_row(posting)
        mock_session = _make_mock_db_for_list(rows=[row], total=1)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get(f"/api/postings?company_id={company_id}")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["company_id"] == str(company_id)

    def test_list_filters_by_is_active(self) -> None:
        posting = _make_posting(is_active=False)
        row = _make_list_row(posting)
        mock_session = _make_mock_db_for_list(rows=[row], total=1)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings?is_active=false")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        assert r.json()["items"][0]["is_active"] is False

    def test_list_pagination_params_accepted(self) -> None:
        mock_session = _make_mock_db_for_list(rows=[], total=100)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings?limit=10&offset=20")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 100
        assert body["items"] == []

    def test_list_multiple_items_returned(self) -> None:
        postings = [_make_posting() for _ in range(3)]
        rows = [_make_list_row(p) for p in postings]
        mock_session = _make_mock_db_for_list(rows=rows, total=3)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3


class TestPostingsDetailEndpoint:
    def _setup_detail_mock(
        self,
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

    def test_detail_returns_404_for_unknown_posting_id(self) -> None:
        mock_session = self._setup_detail_mock(posting=None)
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get(f"/api/postings/{uuid.uuid4()}")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 404
        assert r.json()["detail"] == "Posting not found"

    def test_detail_returns_404_for_invalid_uuid(self) -> None:
        mock_session = AsyncMock()
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get("/api/postings/not-a-uuid")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 404

    def test_detail_returns_full_data_with_enrichment_and_mentions(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)
        enrichment = _make_enrichment(posting_id)
        snapshot = _make_snapshot(posting_id)
        mention, brand_id, brand_name = _make_brand_mention(posting_id)
        mention_rows = [(mention, brand_id, brand_name)]

        mock_session = self._setup_detail_mock(
            posting=posting,
            enrichment=enrichment,
            snapshot=snapshot,
            mention_rows=mention_rows,
        )
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get(f"/api/postings/{posting_id}")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["id"] == str(posting_id)
        assert body["company_id"] == str(posting.company_id)
        assert body["is_active"] is True
        assert body["title"] == "Field Sales Rep - Samsung"
        assert body["location"] == "Atlanta, GA"
        assert body["url"] == "https://careers.example.com/jobs/123"
        assert body["times_reposted"] == 0

        enr = body["enrichment"]
        assert enr is not None
        assert enr["role_archetype"] == "field_sales"
        assert enr["pay_min"] == 18.0
        assert enr["pay_max"] == 24.0
        assert enr["employment_type"] == "full_time"
        assert enr["enrichment_version"] == "pass2"

        assert len(body["brand_mentions"]) == 1
        bm = body["brand_mentions"][0]
        assert bm["brand_name"] == "Samsung"
        assert bm["entity_type"] == "brand"
        assert bm["confidence_score"] == pytest.approx(0.95)

    def test_detail_with_no_enrichment_returns_null_enrichment(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)

        mock_session = self._setup_detail_mock(
            posting=posting,
            enrichment=None,
            snapshot=None,
            mention_rows=[],
        )
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get(f"/api/postings/{posting_id}")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["enrichment"] is None
        assert body["brand_mentions"] == []
        assert body["title"] is None
        assert body["location"] is None

    def test_detail_with_no_snapshot_returns_null_title_and_location(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)
        enrichment = _make_enrichment(posting_id)

        mock_session = self._setup_detail_mock(
            posting=posting,
            enrichment=enrichment,
            snapshot=None,
            mention_rows=[],
        )
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            with TestClient(app) as client:
                r = client.get(f"/api/postings/{posting_id}")
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["title"] is None
        assert body["location"] is None
        assert body["url"] is None
        assert body["enrichment"] is not None
