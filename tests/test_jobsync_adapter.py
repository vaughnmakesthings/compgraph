"""Unit tests for the Acosta Group JobSync scraper adapter.

Covers:
- Response parsing (parse_job, parse_page)
- URL construction (build_posting_url, build_location_string)
- Pagination logic (JobSyncFetcher.fetch_all_for_agency)
- Circuit breaker behaviour
- Per-posting persist-error isolation
- Adapter registration
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from compgraph.scrapers.jobsync import (
    JOBSYNC_X_ORIGIN,
    CircuitBreakerOpen,
    JobSyncAdapter,
    JobSyncFetcher,
    JobSyncPage,
    JobSyncPosting,
    _hash_text,
    build_location_string,
    build_posting_url,
    parse_job,
    parse_page,
    persist_posting,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _make_company(
    slug: str = "premium",
    name: str = "Premium",
    ats_platform: str = "jobsyn",
    career_site_url: str = "https://acosta.jobs",
    scraper_config: dict | None = None,
) -> MagicMock:
    company = MagicMock()
    company.id = uuid.uuid4()
    company.slug = slug
    company.name = name
    company.ats_platform = ats_platform
    company.career_site_url = career_site_url
    company.scraper_config = (
        scraper_config
        if scraper_config is not None
        else {
            "agency_slug": "premium",
            "agency_name": "Premium",
            "page_size": 14,
            "delay_min": 0.0,
            "delay_max": 0.0,
        }
    )
    return company


def _mock_response(data: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "https://prod-search-api.jobsyn.org/api/v1/solr/search"),
    )


def _make_session_mocks(posting_id: uuid.UUID | None = None) -> AsyncMock:
    """Return a session mock wired for multiple successful persist_posting calls."""
    session = AsyncMock()
    pid = posting_id or uuid.uuid4()

    posting_result = MagicMock()
    posting_result.scalar_one.return_value = pid

    snapshot_check = MagicMock()
    snapshot_check.scalar_one_or_none.return_value = None

    prev_hash = MagicMock()
    prev_hash.scalar_one_or_none.return_value = None

    snapshot_insert = MagicMock()
    snapshot_insert.rowcount = 1

    session.execute = AsyncMock(
        side_effect=[posting_result, snapshot_check, prev_hash, snapshot_insert] * 10
    )
    session.begin_nested = MagicMock(return_value=AsyncMock())
    session.commit = AsyncMock()
    return session


class TestParseJob:
    def test_parses_full_item(self):
        data = _load("jobsync_page_1.json")
        item = data["jobs"][0]
        posting = parse_job(item, agency_name="Premium")

        assert isinstance(posting, JobSyncPosting)
        assert posting.guid == "abc123def456"
        assert posting.reqid == "REQ-001"
        assert posting.title == "Retail Sales Merchandiser"
        assert posting.city == "Chicago"
        assert posting.state == "IL"
        assert posting.country == "United States"
        assert "Retail Sales Merchandiser" in posting.description
        assert posting.date_added == "2026-02-15T00:00:00"
        assert posting.agency_name == "Premium"

    def test_falls_back_to_non_exact_fields(self):
        item = {
            "guid": "xyz",
            "title": "Fallback Title",
            "city": "Dallas",
            "state": "TX",
            "country": "US",
            "description": "desc",
            "date_added": "",
            "date_updated": "",
        }
        posting = parse_job(item, agency_name="Acosta")

        assert posting.title == "Fallback Title"
        assert posting.city == "Dallas"
        assert posting.state == "TX"
        assert posting.country == "US"
        assert posting.agency_name == "Acosta"

    def test_handles_missing_fields_gracefully(self):
        posting = parse_job({}, agency_name="CROSSMARK")

        assert posting.guid == ""
        assert posting.title == ""
        assert posting.city == ""
        assert posting.description == ""
        assert posting.agency_name == "CROSSMARK"

    def test_title_exact_takes_precedence_over_title(self):
        item = {"title_exact": "Preferred Title", "title": "Fallback Title"}
        posting = parse_job(item, agency_name="Mosaic")

        assert posting.title == "Preferred Title"


class TestParsePage:
    def test_parses_first_page(self):
        data = _load("jobsync_page_1.json")
        page = parse_page(data, agency_name="Premium")

        assert isinstance(page, JobSyncPage)
        assert page.total_count == 42
        assert page.current_page == 1
        assert page.total_pages == 3
        assert len(page.postings) == 3
        assert page.postings[0].guid == "abc123def456"

    def test_parses_empty_response(self):
        data = _load("jobsync_empty.json")
        page = parse_page(data, agency_name="ADW")

        assert page.total_count == 0
        assert page.total_pages == 0
        assert page.postings == []

    def test_handles_missing_pagination(self):
        data = {"jobs": [{"guid": "g1", "title_exact": "T1"}]}
        page = parse_page(data, agency_name="Acosta")

        assert page.total_count == 0
        assert page.current_page == 1
        assert page.total_pages == 1
        assert len(page.postings) == 1

    def test_handles_missing_jobs_key(self):
        data = {"pagination": {"current_page": 1, "total_pages": 1, "total_count": 0}}
        page = parse_page(data, agency_name="ActionLink")

        assert page.postings == []


class TestBuildPostingUrl:
    def _posting(self, **kwargs) -> JobSyncPosting:
        defaults = dict(
            guid="abc123",
            reqid="REQ-1",
            title="Retail Sales Merchandiser",
            city="Chicago",
            state="IL",
            country="United States",
            description="",
            date_added="",
            date_updated="",
            agency_name="Premium",
        )
        defaults.update(kwargs)
        return JobSyncPosting(**defaults)

    def test_full_url_with_city_and_state(self):
        url = build_posting_url(
            self._posting(
                title="Retail Sales Merchandiser", city="Chicago", state="IL", guid="abc123"
            )
        )
        assert url == "https://acosta.jobs/chicago-il/retail-sales-merchandiser/abc123/job/"

    def test_url_slugifies_spaces(self):
        url = build_posting_url(
            self._posting(
                title="Field Sales Representative", city="New York", state="NY", guid="xyz789"
            )
        )
        assert url == "https://acosta.jobs/new-york-ny/field-sales-representative/xyz789/job/"

    def test_url_slugifies_special_chars(self):
        url = build_posting_url(
            self._posting(
                title="Manager & Leader (Part-Time)", city="St. Louis", state="MO", guid="qqq111"
            )
        )
        assert "qqq111" in url
        assert url.startswith("https://acosta.jobs/")
        assert url.endswith("/job/")

    def test_url_without_location(self):
        url = build_posting_url(
            self._posting(title="Remote Role", city="", state="", guid="rem999")
        )
        assert url == "https://acosta.jobs/remote-role/rem999/job/"

    def test_url_without_title(self):
        url = build_posting_url(
            self._posting(title="", city="Chicago", state="IL", guid="notitle1")
        )
        assert "notitle1" in url
        assert url.endswith("/job/")


class TestBuildLocationString:
    def _posting(self, city: str, state: str, country: str) -> JobSyncPosting:
        return JobSyncPosting(
            guid="g",
            reqid="r",
            title="T",
            city=city,
            state=state,
            country=country,
            description="",
            date_added="",
            date_updated="",
            agency_name="A",
        )

    def test_full_location(self):
        assert (
            build_location_string(self._posting("Chicago", "IL", "United States"))
            == "Chicago, IL, United States"
        )

    def test_city_state_only(self):
        assert build_location_string(self._posting("Chicago", "IL", "")) == "Chicago, IL"

    def test_state_only(self):
        assert build_location_string(self._posting("", "TX", "")) == "TX"

    def test_all_empty(self):
        assert build_location_string(self._posting("", "", "")) == ""


class TestJobSyncFetcher:
    def _fetcher(self, **kwargs) -> JobSyncFetcher:
        defaults = dict(delay_min=0.0, delay_max=0.0)
        defaults.update(kwargs)
        return JobSyncFetcher(**defaults)

    async def test_fetch_page_returns_parsed_page(self):
        fetcher = self._fetcher()
        page_data = _load("jobsync_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(page_data))

        result = await fetcher.fetch_page(client, "premium", "Premium", page=1)

        assert isinstance(result, JobSyncPage)
        assert result.total_count == 42
        assert len(result.postings) == 3
        client.get.assert_called_once()

    async def test_fetch_page_includes_x_origin_header(self):
        fetcher = self._fetcher()
        page_data = _load("jobsync_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(page_data))

        await fetcher.fetch_page(client, "premium", "Premium", page=1)

        call_kwargs = client.get.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("X-Origin") == JOBSYNC_X_ORIGIN
        assert headers.get("Accept") == "application/json"

    async def test_fetch_page_sends_agency_param(self):
        fetcher = self._fetcher()
        page_data = _load("jobsync_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(page_data))

        await fetcher.fetch_page(client, "crossmark", "CROSSMARK", page=2)

        call_kwargs = client.get.call_args.kwargs
        params = call_kwargs.get("params", {})
        assert params.get("agency") == "crossmark"
        assert params.get("page") == 2

    async def test_fetch_all_paginates(self):
        fetcher = self._fetcher()
        page1 = _load("jobsync_page_1.json")
        page2 = _load("jobsync_page_2.json")
        page3_data = {
            "jobs": [],
            "pagination": {"current_page": 3, "total_pages": 3, "total_count": 42},
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=[
                _mock_response(page1),
                _mock_response(page2),
                _mock_response(page3_data),
            ]
        )

        postings = await fetcher.fetch_all_for_agency(client, "premium", "Premium", delay=0.0)

        assert len(postings) == 5
        assert client.get.call_count == 3

    async def test_fetch_all_deduplicates_guids(self):
        fetcher = self._fetcher()
        page1 = _load("jobsync_page_1.json")
        dup_guid = page1["jobs"][0]["guid"]

        page2_data = {
            "jobs": [
                {**page1["jobs"][0]},
                {
                    "guid": "newguid999",
                    "reqid": "REQ-NEW",
                    "title_exact": "New Job",
                    "city_exact": "Miami",
                    "state_short": "FL",
                    "country_exact": "United States",
                    "description": "New job desc",
                    "date_added": "",
                    "date_updated": "",
                },
            ],
            "pagination": {"current_page": 2, "total_pages": 2, "total_count": 10},
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=[_mock_response(page1), _mock_response(page2_data)])

        postings = await fetcher.fetch_all_for_agency(client, "premium", "Premium", delay=0.0)

        guids = [p.guid for p in postings]
        assert len(guids) == len(set(guids)), "No duplicate GUIDs"
        assert dup_guid in guids
        assert "newguid999" in guids

    async def test_fetch_all_stops_on_empty_jobs(self):
        fetcher = self._fetcher()
        empty = _load("jobsync_empty.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(empty))

        postings = await fetcher.fetch_all_for_agency(client, "adw", "ADW", delay=0.0)

        assert postings == []
        assert client.get.call_count == 1

    async def test_circuit_breaker_trips_after_threshold(self):
        fetcher = self._fetcher(circuit_breaker_threshold=3)

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(500),
            )
        )

        for _ in range(3):
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_page(client, "premium", "Premium", page=1)

        assert fetcher._circuit_open is True

        with pytest.raises(CircuitBreakerOpen):
            await fetcher.fetch_page(client, "premium", "Premium", page=1)

    async def test_circuit_breaker_resets_on_success(self):
        fetcher = self._fetcher(circuit_breaker_threshold=3)
        page_data = _load("jobsync_page_1.json")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(500),
            )
        )

        for _ in range(2):
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_page(client, "premium", "Premium", page=1)

        assert fetcher._consecutive_failures == 2
        assert fetcher._circuit_open is False

        client.get = AsyncMock(return_value=_mock_response(page_data))
        await fetcher.fetch_page(client, "premium", "Premium", page=1)

        assert fetcher._consecutive_failures == 0
        assert fetcher._circuit_open is False

    async def test_pages_fetched_increments(self):
        fetcher = self._fetcher()
        page_data = _load("jobsync_page_1.json")
        page_data_single = {
            **page_data,
            "pagination": {**page_data["pagination"], "total_pages": 1},
        }

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(page_data_single))

        await fetcher.fetch_all_for_agency(client, "premium", "Premium", delay=0.0)

        assert fetcher.pages_fetched == 1


class TestPersistPosting:
    @pytest.fixture(autouse=True)
    def _patch_geocode(self):
        with patch(
            "compgraph.scrapers.persistence._maybe_geocode_posting",
            new_callable=AsyncMock,
        ):
            yield

    def _raw(
        self,
        external_job_id: str = "abc123def456",
        title: str = "Retail Sales Merchandiser",
        location: str = "Chicago, IL, United States",
        url: str = "https://acosta.jobs/chicago-il/retail-sales-merchandiser/abc123def456/job/",
        full_text: str = "<p>Job description</p>",
    ) -> MagicMock:
        raw = MagicMock()
        raw.external_job_id = external_job_id
        raw.title = title
        raw.location = location
        raw.url = url
        raw.full_text = full_text
        return raw

    async def test_creates_posting_and_snapshot(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id
        snapshot_check = MagicMock()
        snapshot_check.scalar_one_or_none.return_value = None
        prev_hash = MagicMock()
        prev_hash.scalar_one_or_none.return_value = None
        snapshot_insert = MagicMock()
        snapshot_insert.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[posting_result, snapshot_check, prev_hash, snapshot_insert]
        )

        created = await persist_posting(session, company_id, self._raw())

        assert created is True
        assert session.execute.call_count == 4

    async def test_skips_duplicate_snapshot(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id
        snapshot_check = MagicMock()
        snapshot_check.scalar_one_or_none.return_value = uuid.uuid4()

        session.execute = AsyncMock(side_effect=[posting_result, snapshot_check])

        created = await persist_posting(session, company_id, self._raw())

        assert created is False
        assert session.execute.call_count == 2

    async def test_detects_content_change(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id
        snapshot_check = MagicMock()
        snapshot_check.scalar_one_or_none.return_value = None
        prev_hash_result = MagicMock()
        prev_hash_result.scalar_one_or_none.return_value = "oldhash"
        snapshot_insert = MagicMock()
        snapshot_insert.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[posting_result, snapshot_check, prev_hash_result, snapshot_insert]
        )

        created = await persist_posting(
            session, company_id, self._raw(full_text="<p>Updated description</p>")
        )

        assert created is True

    async def test_respects_first_seen_at(self):
        session = AsyncMock()
        posting_id = uuid.uuid4()
        company_id = uuid.uuid4()
        first_seen = datetime(2026, 2, 15, tzinfo=UTC)

        posting_result = MagicMock()
        posting_result.scalar_one.return_value = posting_id
        snapshot_check = MagicMock()
        snapshot_check.scalar_one_or_none.return_value = None
        prev_hash = MagicMock()
        prev_hash.scalar_one_or_none.return_value = None
        snapshot_insert = MagicMock()
        snapshot_insert.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[posting_result, snapshot_check, prev_hash, snapshot_insert]
        )

        created = await persist_posting(session, company_id, self._raw(), first_seen_at=first_seen)

        assert created is True


class TestHashText:
    def test_consistent(self):
        text = "<p>Hello world</p>"
        assert _hash_text(text) == _hash_text(text)

    def test_different_input_different_hash(self):
        assert _hash_text("hello") != _hash_text("world")

    def test_returns_64_char_hex(self):
        result = _hash_text("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestJobSyncAdapter:
    @pytest.fixture(autouse=True)
    def _patch_geocode(self):
        with patch(
            "compgraph.scrapers.persistence._maybe_geocode_posting",
            new_callable=AsyncMock,
        ):
            yield

    async def test_scrape_missing_agency_slug_returns_error(self):
        company = _make_company(scraper_config={})
        session = AsyncMock()

        adapter = JobSyncAdapter()
        result = await adapter.scrape(company, session)

        assert not result.success
        assert any("agency_slug" in e for e in result.errors)
        assert result.finished_at is not None

    async def test_scrape_end_to_end(self):
        company = _make_company()
        page1 = _load("jobsync_page_1.json")
        page1_single = {**page1, "pagination": {**page1["pagination"], "total_pages": 1}}
        session = _make_session_mocks()

        def _mock_get(url: str, **kwargs) -> httpx.Response:
            return httpx.Response(200, json=page1_single, request=httpx.Request("GET", url))

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=_mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        adapter = JobSyncAdapter()
        with patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert result.postings_found == 3
        assert result.snapshots_created == 3
        assert result.success
        assert result.finished_at is not None
        session.commit.assert_called_once()

    async def test_scrape_handles_circuit_breaker(self):
        company = _make_company()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(500),
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()

        adapter = JobSyncAdapter()
        with patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert not result.success
        assert len(result.errors) > 0
        assert result.finished_at is not None

    async def test_scrape_persist_error_isolated_per_posting(self):
        company = _make_company()
        page1 = _load("jobsync_page_1.json")
        page1_single = {**page1, "pagination": {**page1["pagination"], "total_pages": 1}}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            return_value=httpx.Response(
                200, json=page1_single, request=httpx.Request("GET", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        call_count = {"count": 0}

        async def _mock_persist(session, company_id, raw, first_seen_at=None):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("DB constraint violation")
            return True

        session = AsyncMock()
        session.begin_nested = MagicMock(return_value=AsyncMock())
        session.commit = AsyncMock()

        adapter = JobSyncAdapter()
        with (
            patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client),
            patch("compgraph.scrapers.jobsync.persist_posting", side_effect=_mock_persist),
        ):
            result = await adapter.scrape(company, session)

        assert result.postings_found == 3
        assert result.snapshots_created == 2
        assert len(result.errors) == 1
        assert result.finished_at is not None

    async def test_scrape_skips_postings_with_no_guid(self):
        company = _make_company()
        page_data = {
            "jobs": [
                {"guid": "", "title_exact": "No GUID Job", "description": "desc"},
                {
                    "guid": "valid-guid-1",
                    "title_exact": "Valid Job",
                    "city_exact": "Atlanta",
                    "state_short": "GA",
                    "country_exact": "US",
                    "description": "desc",
                    "date_added": "",
                    "date_updated": "",
                },
            ],
            "pagination": {"current_page": 1, "total_pages": 1, "total_count": 2},
        }

        session = _make_session_mocks()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            return_value=httpx.Response(
                200, json=page_data, request=httpx.Request("GET", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        adapter = JobSyncAdapter()
        with patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        # The empty-guid posting is filtered by the fetcher (logged, not added to result.warnings).
        # Only the valid-guid posting reaches the persist loop.
        assert result.snapshots_created == 1
        assert result.postings_found == 1  # fetcher only returns valid-guid postings

    async def test_scrape_records_pages_scraped(self):
        company = _make_company()
        page1 = _load("jobsync_page_1.json")
        page1_single = {**page1, "pagination": {**page1["pagination"], "total_pages": 1}}
        session = _make_session_mocks()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(page1_single))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        adapter = JobSyncAdapter()
        with patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert result.pages_scraped == 1

    async def test_scrape_uses_scraper_config_agency_slug(self):
        company = _make_company(
            scraper_config={
                "agency_slug": "crossmark",
                "agency_name": "CROSSMARK",
                "delay_min": 0.0,
                "delay_max": 0.0,
            }
        )
        empty = _load("jobsync_empty.json")
        captured_params: dict = {}

        def _mock_get(url: str, **kwargs) -> httpx.Response:
            captured_params.update(kwargs.get("params", {}))
            return httpx.Response(200, json=empty, request=httpx.Request("GET", url))

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=_mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        session.commit = AsyncMock()

        adapter = JobSyncAdapter()
        with patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.scrape(company, session)

        assert result.success
        assert captured_params.get("agency") == "crossmark"

    async def test_scrape_parses_date_added_as_first_seen(self):
        company = _make_company()
        page_data = {
            "jobs": [
                {
                    "guid": "dated-guid-1",
                    "title_exact": "Dated Job",
                    "city_exact": "Denver",
                    "state_short": "CO",
                    "country_exact": "US",
                    "description": "desc",
                    "date_added": "2026-02-15T00:00:00",
                    "date_updated": "",
                }
            ],
            "pagination": {"current_page": 1, "total_pages": 1, "total_count": 1},
        }

        captured_first_seen: list = []

        async def _mock_persist(session, company_id, raw, first_seen_at=None):
            captured_first_seen.append(first_seen_at)
            return True

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            return_value=httpx.Response(
                200, json=page_data, request=httpx.Request("GET", "https://example.com")
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = AsyncMock()
        session.begin_nested = MagicMock(return_value=AsyncMock())
        session.commit = AsyncMock()

        adapter = JobSyncAdapter()
        with (
            patch("compgraph.scrapers.jobsync.httpx.AsyncClient", return_value=mock_client),
            patch("compgraph.scrapers.jobsync.persist_posting", side_effect=_mock_persist),
        ):
            await adapter.scrape(company, session)

        assert len(captured_first_seen) == 1
        fs = captured_first_seen[0]
        assert fs is not None
        assert fs.year == 2026
        assert fs.month == 2
        assert fs.day == 15
        assert fs.tzinfo is not None


class TestAgencyTagging:
    def test_all_postings_tagged_with_agency_name(self):
        data = _load("jobsync_page_1.json")
        page = parse_page(data, agency_name="CROSSMARK")

        for posting in page.postings:
            assert posting.agency_name == "CROSSMARK"

    def test_different_agencies_get_different_tags(self):
        data = _load("jobsync_page_1.json")
        page_premium = parse_page(data, agency_name="Premium")
        page_crossmark = parse_page(data, agency_name="CROSSMARK")

        for p in page_premium.postings:
            assert p.agency_name == "Premium"
        for p in page_crossmark.postings:
            assert p.agency_name == "CROSSMARK"


class TestAdapterRegistration:
    def test_jobsyn_registered(self):
        from compgraph.scrapers.registry import _ADAPTER_REGISTRY

        assert "jobsyn" in _ADAPTER_REGISTRY
        assert _ADAPTER_REGISTRY["jobsyn"] is JobSyncAdapter

    def test_get_adapter_returns_jobsync(self):
        from compgraph.scrapers import get_adapter

        adapter = get_adapter("jobsyn")
        assert isinstance(adapter, JobSyncAdapter)


@pytest.mark.integration
class TestJobSyncLiveIntegration:
    """Live integration tests against the Acosta Group JobSync API.

    These tests hit the real API and require network access.
    Run with: uv run pytest -m integration -k jobsync
    """

    async def test_premium_agency_returns_postings(self):
        fetcher = JobSyncFetcher(delay_min=0.5, delay_max=1.5)

        async with httpx.AsyncClient(timeout=30.0) as client:
            result = await fetcher.fetch_page(client, "premium", "Premium", page=1)

        assert result.total_count > 0, "Premium should have active postings"
        assert len(result.postings) > 0, "First page should return postings"
        assert result.postings[0].guid, "Postings should have GUIDs"
        assert result.postings[0].title, "Postings should have titles"
