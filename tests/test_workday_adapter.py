from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from compgraph.scrapers.persistence import _hash_text, persist_posting
from compgraph.scrapers.workday import (
    WORKDAY_PAGE_SIZE,
    CircuitBreakerOpen,
    DetailResult,
    SearchResult,
    WorkdayAdapter,
    WorkdayFetcher,
    parse_detail_response,
    parse_search_response,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


_SENTINEL = object()


def _make_company(
    slug: str = "advantage",
    career_site_url: str = "https://advantage.wd1.myworkdayjobs.com",
    scraper_config: dict | None | object = _SENTINEL,
) -> MagicMock:
    company = MagicMock()
    company.id = uuid.uuid4()
    company.slug = slug
    company.name = slug.replace("-", " ").title()
    company.ats_platform = "workday"
    company.career_site_url = career_site_url
    if scraper_config is _SENTINEL:
        company.scraper_config = {"tenant": "advantage", "site": "External_Careers"}
    else:
        company.scraper_config = scraper_config
    return company


class TestParseSearchResponse:
    def test_parses_page_with_postings(self):
        data = _load_fixture("workday_search_page_1.json")
        result = parse_search_response(data)

        assert isinstance(result, SearchResult)
        assert result.total == 25
        assert len(result.postings) == 5

    def test_first_posting_fields(self):
        data = _load_fixture("workday_search_page_1.json")
        result = parse_search_response(data)
        first = result.postings[0]

        assert first.title == "Retail Sales Specialist - Samsung"
        assert first.external_path == "Retail-Sales-Specialist-Samsung/R12345"
        assert first.location == "New York, NY"
        assert first.posted_on == "Posted 2 Days Ago"
        assert first.time_type == "Full time"
        assert len(first.bullet_fields) == 2

    def test_parses_empty_response(self):
        data = _load_fixture("workday_search_empty.json")
        result = parse_search_response(data)

        assert result.total == 0
        assert result.postings == []

    def test_handles_missing_fields(self):
        data = {"total": 1, "jobPostings": [{"title": "Test", "externalPath": "test/1"}]}
        result = parse_search_response(data)

        assert len(result.postings) == 1
        assert result.postings[0].location == ""
        assert result.postings[0].posted_on == ""
        assert result.postings[0].bullet_fields == []
        assert result.postings[0].time_type == ""

    def test_handles_null_total(self):
        data = {"total": None, "jobPostings": []}
        result = parse_search_response(data)

        assert result.total == 0

    def test_handles_missing_job_postings_key(self):
        data = {"total": 0}
        result = parse_search_response(data)

        assert result.postings == []


class TestParseDetailResponse:
    def test_parses_full_detail(self):
        data = _load_fixture("workday_detail.json")
        result = parse_detail_response(data)

        assert isinstance(result, DetailResult)
        assert result.job_req_id == "REQ_099113"
        assert result.title == "Retail Sales Specialist - Samsung"
        assert "Samsung products" in result.description_html
        assert result.location == "New York, NY"
        assert result.start_date == "2026-02-10T00:00:00Z"
        assert result.time_type == "Full time"
        assert result.country == "US"
        assert result.remote is False
        assert len(result.additional_locations) == 2
        assert "Brooklyn, NY" in result.additional_locations

    def test_external_url(self):
        data = _load_fixture("workday_detail.json")
        result = parse_detail_response(data)

        assert "advantage.wd1.myworkdayjobs.com" in result.external_url

    def test_handles_missing_optional_fields(self):
        data = {"jobPostingInfo": {"title": "Test Job", "jobReqId": "REQ_001"}}
        result = parse_detail_response(data)

        assert result.title == "Test Job"
        assert result.job_req_id == "REQ_001"
        assert result.description_html == ""
        assert result.start_date is None
        assert result.country is None
        assert result.remote is False
        assert result.additional_locations == []

    def test_handles_empty_response(self):
        data = {}
        result = parse_detail_response(data)

        assert result.job_req_id == ""
        assert result.title == ""


class TestWorkdayFetcher:
    def _make_fetcher(self, **kwargs) -> WorkdayFetcher:
        defaults = {
            "base_url": "https://advantage.wd1.myworkdayjobs.com",
            "tenant": "advantage",
            "site": "External_Careers",
            "search_delay": 0.0,
            "detail_delay": 0.0,
        }
        defaults.update(kwargs)
        return WorkdayFetcher(**defaults)

    def _mock_response(self, data: dict, status_code: int = 200) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            json=data,
            request=httpx.Request("POST", "https://example.com"),
        )

    async def test_fetch_search_page(self):
        fetcher = self._make_fetcher()
        page_data = _load_fixture("workday_search_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=self._mock_response(page_data))

        result = await fetcher.fetch_search_page(client, offset=0)

        assert result.total == 25
        assert len(result.postings) == 5
        client.post.assert_called_once()

        call_kwargs = client.post.call_args
        assert call_kwargs.kwargs["json"]["offset"] == 0
        assert call_kwargs.kwargs["json"]["limit"] == WORKDAY_PAGE_SIZE

    async def test_fetch_all_postings_paginates(self):
        fetcher = self._make_fetcher()
        page1 = _load_fixture("workday_search_page_1.json")
        page2 = _load_fixture("workday_search_page_2.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(
            side_effect=[
                self._mock_response(page1),
                self._mock_response(page2),
            ]
        )

        postings = await fetcher.fetch_all_postings(client)

        assert len(postings) == 7
        assert client.post.call_count == 2

        offsets = [call.kwargs["json"]["offset"] for call in client.post.call_args_list]
        assert offsets == [0, 20]

    async def test_fetch_all_postings_deduplicates(self):
        fetcher = self._make_fetcher()
        page1 = _load_fixture("workday_search_page_1.json")
        page2_with_dup = {
            "total": 25,
            "jobPostings": [
                {
                    "title": "Retail Sales Specialist - Samsung",
                    "externalPath": "Retail-Sales-Specialist-Samsung/R12345",
                    "locationsText": "New York, NY",
                    "postedOn": "Posted 2 Days Ago",
                    "bulletFields": [],
                    "timeType": "Full time",
                },
                {
                    "title": "New Job",
                    "externalPath": "New-Job/R99999",
                    "locationsText": "Boston, MA",
                    "postedOn": "Posted Today",
                    "bulletFields": [],
                    "timeType": "Full time",
                },
            ],
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(
            side_effect=[
                self._mock_response(page1),
                self._mock_response(page2_with_dup),
            ]
        )

        postings = await fetcher.fetch_all_postings(client)

        paths = [p.external_path for p in postings]
        assert len(paths) == len(set(paths))
        assert len(postings) == 6

    async def test_fetch_all_postings_stops_on_empty(self):
        fetcher = self._make_fetcher()
        empty = _load_fixture("workday_search_empty.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(return_value=self._mock_response(empty))

        postings = await fetcher.fetch_all_postings(client)

        assert postings == []
        assert client.post.call_count == 1

    async def test_fetch_detail(self):
        fetcher = self._make_fetcher()
        detail_data = _load_fixture("workday_detail.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=self._mock_response(detail_data))

        result = await fetcher.fetch_detail(client, "Retail-Sales-Specialist-Samsung/R12345")

        assert result.job_req_id == "REQ_099113"
        assert result.title == "Retail Sales Specialist - Samsung"
        client.get.assert_called_once()

    async def test_circuit_breaker_trips_after_threshold(self):
        fetcher = self._make_fetcher(circuit_breaker_threshold=3)

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(500),
            )
        )

        for _ in range(3):
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_search_page(client, offset=0)

        assert fetcher._circuit_open is True

        with pytest.raises(CircuitBreakerOpen):
            await fetcher.fetch_search_page(client, offset=0)

    async def test_circuit_breaker_resets_on_success(self):
        fetcher = self._make_fetcher(circuit_breaker_threshold=3)
        page_data = _load_fixture("workday_search_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(500),
            )
        )

        for _ in range(2):
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_search_page(client, offset=0)

        assert fetcher._consecutive_failures == 2
        assert fetcher._circuit_open is False

        client.post = AsyncMock(return_value=self._mock_response(page_data))
        await fetcher.fetch_search_page(client, offset=0)

        assert fetcher._consecutive_failures == 0
        assert fetcher._circuit_open is False

    async def test_fetch_details_batch(self):
        fetcher = self._make_fetcher()
        detail_data = _load_fixture("workday_detail.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=self._mock_response(detail_data))

        paths = ["path/1", "path/2", "path/3"]
        results = await fetcher.fetch_details_batch(client, paths)

        assert len(results) == 3
        assert all(isinstance(v, DetailResult) for v in results.values())

    async def test_fetch_details_batch_handles_partial_failures(self):
        fetcher = self._make_fetcher(circuit_breaker_threshold=10)
        detail_data = _load_fixture("workday_detail.json")

        call_count = 0

        async def _side_effect(url: str) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise httpx.ConnectError("Connection refused")
            return self._mock_response(detail_data)

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=_side_effect)

        paths = ["path/1", "path/2", "path/3"]
        results = await fetcher.fetch_details_batch(client, paths)

        assert len(results) == 2
        assert "path/1" in results
        assert "path/2" not in results
        assert "path/3" in results


class TestPersistPosting:
    @pytest.fixture(autouse=True)
    def _patch_geocode(self):
        with patch(
            "compgraph.scrapers.persistence._maybe_geocode_posting",
            new_callable=AsyncMock,
        ):
            yield

    def _make_raw_posting(
        self,
        external_job_id: str = "REQ_099113",
        title: str = "Retail Sales Specialist",
        location: str = "New York, NY",
        url: str = "https://example.com/job/123",
        full_text: str = "<p>Job description here</p>",
    ) -> MagicMock:
        raw = MagicMock()
        raw.external_job_id = external_job_id
        raw.title = title
        raw.location = location
        raw.url = url
        raw.full_text = full_text
        return raw

    async def test_persist_creates_posting_and_snapshot(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()
        raw = self._make_raw_posting()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id

        snapshot_check_result = MagicMock()
        snapshot_check_result.scalar_one_or_none.return_value = None

        prev_hash_result = MagicMock()
        prev_hash_result.scalar_one_or_none.return_value = None

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[
                posting_result,
                snapshot_check_result,
                prev_hash_result,
                snapshot_insert_result,
            ]
        )

        created = await persist_posting(session, company_id, raw)

        assert created is True
        assert session.execute.call_count == 4

    async def test_persist_skips_duplicate_snapshot(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()
        raw = self._make_raw_posting()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id

        snapshot_check_result = MagicMock()
        snapshot_check_result.scalar_one_or_none.return_value = uuid.uuid4()

        session.execute = AsyncMock(side_effect=[posting_result, snapshot_check_result])

        created = await persist_posting(session, company_id, raw)

        assert created is False
        assert session.execute.call_count == 2

    async def test_persist_detects_content_change(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()
        raw = self._make_raw_posting(full_text="<p>New description</p>")

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id

        snapshot_check_result = MagicMock()
        snapshot_check_result.scalar_one_or_none.return_value = None

        prev_hash_result = MagicMock()
        prev_hash_result.scalar_one_or_none.return_value = "oldhash123"

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[
                posting_result,
                snapshot_check_result,
                prev_hash_result,
                snapshot_insert_result,
            ]
        )

        created = await persist_posting(session, company_id, raw)

        assert created is True

    async def test_persist_with_first_seen_at(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()
        raw = self._make_raw_posting()
        first_seen = datetime(2026, 2, 10, tzinfo=UTC)

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id

        snapshot_check_result = MagicMock()
        snapshot_check_result.scalar_one_or_none.return_value = None

        prev_hash_result = MagicMock()
        prev_hash_result.scalar_one_or_none.return_value = None

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[
                posting_result,
                snapshot_check_result,
                prev_hash_result,
                snapshot_insert_result,
            ]
        )

        created = await persist_posting(session, company_id, raw, first_seen_at=first_seen)

        assert created is True


class TestHashText:
    def test_consistent_hashing(self):
        text = "<p>Hello world</p>"
        assert _hash_text(text) == _hash_text(text)

    def test_different_text_different_hash(self):
        assert _hash_text("hello") != _hash_text("world")

    def test_returns_hex_string(self):
        result = _hash_text("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestWorkdayAdapter:
    @pytest.fixture(autouse=True)
    def _patch_geocode(self):
        with patch(
            "compgraph.scrapers.persistence._maybe_geocode_posting",
            new_callable=AsyncMock,
        ):
            yield

    async def test_scrape_end_to_end(self):
        company = _make_company()
        page1 = _load_fixture("workday_search_page_1.json")
        empty = _load_fixture("workday_search_empty.json")
        detail_data = _load_fixture("workday_detail.json")

        def _mock_post(url: str, **kwargs) -> httpx.Response:
            offset = kwargs.get("json", {}).get("offset", 0)
            if offset == 0:
                return httpx.Response(200, json=page1, request=httpx.Request("POST", url))
            return httpx.Response(200, json=empty, request=httpx.Request("POST", url))

        def _mock_get(url: str) -> httpx.Response:
            return httpx.Response(200, json=detail_data, request=httpx.Request("GET", url))

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=_mock_post)
        mock_client.get = AsyncMock(side_effect=_mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        posting_id = uuid.uuid4()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id
        snapshot_check = MagicMock()
        snapshot_check.scalar_one_or_none.return_value = None
        prev_hash = MagicMock()
        prev_hash.scalar_one_or_none.return_value = None

        snapshot_insert = MagicMock()
        snapshot_insert.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[posting_result, snapshot_check, prev_hash, snapshot_insert] * 5
        )
        session.begin_nested = MagicMock(return_value=AsyncMock())
        session.commit = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert result.postings_found == 5
        assert result.snapshots_created == 5
        assert result.success
        assert result.finished_at is not None
        session.commit.assert_called_once()

    async def test_scrape_uses_config_tenant_and_site(self):
        company = _make_company(
            slug="acosta",
            career_site_url="https://acosta.wd1.myworkdayjobs.com",
            scraper_config={"tenant": "acosta", "site": "Acosta_Careers"},
        )
        empty = _load_fixture("workday_search_empty.json")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            return_value=httpx.Response(
                200, json=empty, request=httpx.Request("POST", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        session.commit = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        call_url = mock_client.post.call_args[0][0]
        assert "/wday/cxs/acosta/Acosta_Careers/jobs" in call_url
        assert result.success

    async def test_scrape_handles_search_failure(self):
        company = _make_company()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert not result.success
        assert len(result.errors) > 0
        assert result.finished_at is not None

    async def test_scrape_handles_circuit_breaker(self):
        company = _make_company()

        call_count = 0

        async def _failing_post(url: str, **kwargs) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            raise httpx.HTTPStatusError(
                "500",
                request=httpx.Request("POST", url),
                response=httpx.Response(500),
            )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=_failing_post)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert not result.success
        assert result.finished_at is not None

    async def test_scrape_defaults_tenant_to_slug(self):
        company = _make_company(
            slug="testco",
            career_site_url="https://testco.wd1.myworkdayjobs.com",
            scraper_config={},
        )
        empty = _load_fixture("workday_search_empty.json")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            return_value=httpx.Response(
                200, json=empty, request=httpx.Request("POST", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        session.commit = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            await adapter.scrape(company, session)

        call_url = mock_client.post.call_args[0][0]
        assert "/wday/cxs/testco/External_Careers/jobs" in call_url

    async def test_scrape_persist_error_isolated_per_job(self):
        company = _make_company()
        page1_data = {
            "total": 2,
            "jobPostings": [
                {
                    "title": "Job A",
                    "externalPath": "job-a/1",
                    "locationsText": "NYC",
                    "postedOn": "Today",
                    "bulletFields": [],
                    "timeType": "Full time",
                },
                {
                    "title": "Job B",
                    "externalPath": "job-b/2",
                    "locationsText": "LA",
                    "postedOn": "Today",
                    "bulletFields": [],
                    "timeType": "Full time",
                },
            ],
        }
        empty = _load_fixture("workday_search_empty.json")
        detail_data = _load_fixture("workday_detail.json")

        call_count = {"post": 0}

        def _mock_post(url: str, **kwargs) -> httpx.Response:
            call_count["post"] += 1
            if call_count["post"] == 1:
                return httpx.Response(200, json=page1_data, request=httpx.Request("POST", url))
            return httpx.Response(200, json=empty, request=httpx.Request("POST", url))

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=_mock_post)
        mock_client.get = AsyncMock(
            return_value=httpx.Response(
                200, json=detail_data, request=httpx.Request("GET", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        persist_call_count = {"count": 0}

        async def _mock_persist(session, company_id, raw, first_seen_at=None):
            persist_call_count["count"] += 1
            if persist_call_count["count"] == 1:
                raise Exception("DB constraint violation")
            return True

        session = AsyncMock()
        session.begin_nested = MagicMock(return_value=AsyncMock())
        session.commit = AsyncMock()

        adapter = WorkdayAdapter()
        with (
            patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client),
            patch("compgraph.scrapers.workday.persist_posting", side_effect=_mock_persist),
        ):
            result = await adapter.scrape(company, session)

        assert result.postings_found == 2
        assert result.snapshots_created == 1
        assert len(result.errors) == 1
        assert result.finished_at is not None


class TestTrocConfig:
    """Verify WorkdayAdapter works with T-ROC's Workday CXS configuration."""

    async def test_scrape_uses_troc_tenant_and_site(self):
        company = _make_company(
            slug="troc",
            career_site_url="https://troc.wd501.myworkdayjobs.com",
            scraper_config={"tenant": "troc", "site": "TROC_External"},
        )
        empty = _load_fixture("workday_search_empty.json")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            return_value=httpx.Response(
                200, json=empty, request=httpx.Request("POST", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        session.commit = AsyncMock()

        adapter = WorkdayAdapter()
        with patch("compgraph.scrapers.workday.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        call_url = mock_client.post.call_args[0][0]
        assert "/wday/cxs/troc/TROC_External/jobs" in call_url
        assert "wd501" in call_url
        assert result.success

    async def test_troc_fetcher_constructs_correct_urls(self):
        fetcher = WorkdayFetcher(
            base_url="https://troc.wd501.myworkdayjobs.com",
            tenant="troc",
            site="TROC_External",
            search_delay=0.0,
            detail_delay=0.0,
        )
        assert fetcher.tenant == "troc"
        assert fetcher.site == "TROC_External"


class TestAdapterRegistration:
    def test_workday_adapter_registered(self):
        from compgraph.scrapers.registry import _ADAPTER_REGISTRY

        assert "workday" in _ADAPTER_REGISTRY
        assert _ADAPTER_REGISTRY["workday"] is WorkdayAdapter

    def test_get_adapter_returns_workday(self):
        from compgraph.scrapers import get_adapter

        adapter = get_adapter("workday")
        assert isinstance(adapter, WorkdayAdapter)


@pytest.mark.integration
class TestTrocLiveIntegration:
    """Live integration tests against T-ROC's Workday CXS instance.

    These tests hit the real T-ROC career site API and require network access.
    Run with: uv run pytest -m integration -k troc
    """

    async def test_troc_search_returns_jobs(self):
        """Verify T-ROC's Workday CXS endpoint returns job postings."""
        fetcher = WorkdayFetcher(
            base_url="https://troc.wd501.myworkdayjobs.com",
            tenant="troc",
            site="TROC_External",
            search_delay=1.0,
            detail_delay=1.0,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            result = await fetcher.fetch_search_page(client, offset=0)

        assert result.total > 0, "T-ROC should have active job postings"
        assert len(result.postings) > 0, "First page should return postings"
        assert result.postings[0].title, "Postings should have titles"
        assert result.postings[0].external_path, "Postings should have external paths"

    async def test_troc_detail_fetches_job(self):
        """Verify T-ROC job detail endpoint returns structured data."""
        fetcher = WorkdayFetcher(
            base_url="https://troc.wd501.myworkdayjobs.com",
            tenant="troc",
            site="TROC_External",
            search_delay=1.0,
            detail_delay=1.0,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            search_result = await fetcher.fetch_search_page(client, offset=0)
            assert len(search_result.postings) > 0, "Need at least one posting for detail test"

            first_path = search_result.postings[0].external_path
            detail = await fetcher.fetch_detail(client, first_path)

        assert detail.title, "Detail should have a title"
        assert detail.job_req_id, "Detail should have a job req ID"
