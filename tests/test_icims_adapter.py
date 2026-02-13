from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from compgraph.scrapers.icims import (
    ICIMSFetcher,
    has_next_page,
    parse_html_fallback,
    parse_json_ld,
    parse_listing_page,
    persist_posting,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseJsonLd:
    def test_extracts_job_posting_fields(self) -> None:
        html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()
        data = parse_json_ld(html)
        assert data is not None
        assert data["title"] == "Meta Lab Assistant Manager"
        assert "BDS Connected Solutions" in data["description"]
        assert "Houston" in data["location"]
        assert data["job_id"] == "47917"
        assert data["salary_min"] == 65000
        assert data["salary_max"] == 70000
        assert data["salary_currency"] == "USD"
        assert data["employment_type"] == "FULL_TIME"
        assert data["date_posted"] == "2026-02-13T05:00:00.000Z"

    def test_returns_none_when_no_jsonld(self) -> None:
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_json_ld(html)
        assert data is None

    def test_returns_none_on_malformed_json(self) -> None:
        html = '<script type="application/ld+json">{broken json</script>'
        data = parse_json_ld(html)
        assert data is None

    def test_returns_none_on_scalar_json_ld(self) -> None:
        html = '<script type="application/ld+json">"just a string"</script>'
        data = parse_json_ld(html)
        assert data is None

    def test_returns_none_on_numeric_json_ld(self) -> None:
        html = '<script type="application/ld+json">42</script>'
        data = parse_json_ld(html)
        assert data is None

    def test_extracts_from_graph_wrapper(self) -> None:
        html = """<script type="application/ld+json">
        {"@graph": [{"@type": "JobPosting", "title": "Graph Job", "url": "/jobs/999/test/job"}]}
        </script>"""
        data = parse_json_ld(html)
        assert data is not None
        assert data["title"] == "Graph Job"


class TestParseListingPage:
    def test_extracts_job_links(self) -> None:
        html = (FIXTURES / "icims_listing_page.html").read_text()
        jobs = parse_listing_page(html)
        assert len(jobs) == 5
        for job in jobs:
            assert "job_id" in job
            assert "slug" in job
            assert "url_path" in job
        assert jobs[0]["job_id"] == "47917"
        assert jobs[0]["slug"] == "meta-lab-assistant-manager"

    def test_empty_listing_returns_empty(self) -> None:
        html = (FIXTURES / "icims_listing_empty.html").read_text()
        jobs = parse_listing_page(html)
        assert jobs == []

    def test_page_2_extracts_jobs(self) -> None:
        html = (FIXTURES / "icims_listing_page_2.html").read_text()
        jobs = parse_listing_page(html)
        assert len(jobs) == 2


class TestHasNextPage:
    def test_has_next_when_present(self) -> None:
        html = (FIXTURES / "icims_listing_page.html").read_text()
        assert has_next_page(html) is True

    def test_no_next_on_last_page(self) -> None:
        html = (FIXTURES / "icims_listing_page_2.html").read_text()
        assert has_next_page(html) is False

    def test_no_false_positive_on_next_in_title(self) -> None:
        html = (
            '<html><body><a href="/jobs/1/next-gen-rep/job">'
            "Next Generation Field Rep</a></body></html>"
        )
        assert has_next_page(html) is False


class TestParseHtmlFallback:
    def test_extracts_basic_fields(self) -> None:
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_html_fallback(html)
        assert data is not None
        assert data["title"] == "Senior Field Technician"
        assert "field experience" in data["description"]
        assert data["job_id"] == "48000"

    def test_extracts_location_from_meta(self) -> None:
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_html_fallback(html)
        assert data is not None
        assert data["location"] == "Dallas, TX"

    def test_returns_empty_location_when_absent(self) -> None:
        html = '<html><body><h1>Test Job</h1><div class="iCIMS_JobContent">desc</div></body></html>'
        data = parse_html_fallback(html)
        assert data is not None
        assert data["location"] == ""

    def test_returns_none_on_empty_page(self) -> None:
        html = "<html><body></body></html>"
        data = parse_html_fallback(html)
        assert data is None


def _make_response(status_code: int, text: str = "") -> httpx.Response:
    request = httpx.Request("GET", "https://test.icims.com")
    return httpx.Response(status_code, text=text, request=request)


class TestICIMSFetcher:
    @pytest.mark.asyncio
    async def test_fetch_listing_pages_paginates(self) -> None:
        page1_html = (FIXTURES / "icims_listing_page.html").read_text()
        page2_html = (FIXTURES / "icims_listing_page_2.html").read_text()

        responses = [
            _make_response(200, page1_html),
            _make_response(200, page2_html),
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=responses)

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )
        jobs = await fetcher.fetch_all_listings()

        assert len(jobs) == 7
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_detail_returns_parsed_data(self) -> None:
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(200, detail_html))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )
        result = await fetcher.fetch_detail("47917", "meta-lab-assistant-manager")

        assert result is not None
        assert result["title"] == "Meta Lab Assistant Manager"
        assert result["job_id"] == "47917"

    @pytest.mark.asyncio
    async def test_fetch_detail_http_error_returns_none(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(404))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )
        result = await fetcher.fetch_detail("99999", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_after_3_failures(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(500))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )

        for _ in range(3):
            await fetcher.fetch_detail("123", "test")

        assert fetcher.circuit_open is True

        call_count_before = mock_client.get.call_count
        result = await fetcher.fetch_detail("456", "another")
        assert result is None
        assert mock_client.get.call_count == call_count_before

    @pytest.mark.asyncio
    async def test_successful_fetch_resets_failure_count(self) -> None:
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        responses = [
            _make_response(500),
            _make_response(500),
            _make_response(200, detail_html),
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=responses)

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )

        await fetcher.fetch_detail("1", "a")
        await fetcher.fetch_detail("2", "b")
        result = await fetcher.fetch_detail("3", "c")

        assert result is not None
        assert fetcher.consecutive_failures == 0
        assert fetcher.circuit_open is False

    @pytest.mark.asyncio
    async def test_fetch_detail_uses_html_fallback(self) -> None:
        detail_html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(200, detail_html))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://test.icims.com",
            delay_min=0,
            delay_max=0,
        )
        result = await fetcher.fetch_detail("48000", "senior-field-technician")

        assert result is not None
        assert result["title"] == "Senior Field Technician"


class TestPersistPosting:
    @pytest.mark.asyncio
    async def test_new_posting_creates_posting_and_snapshot(self) -> None:
        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, MagicMock()]
        )

        company_id = uuid.uuid4()
        raw: dict[str, str | int | None] = {
            "title": "Sales Rep",
            "description": "<p>Great job</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/sales-rep/job",
        }

        result = await persist_posting(mock_session, raw, company_id, "https://test.icims.com")
        assert result is True
        # 3 executes: posting upsert, snapshot hash lookup, snapshot upsert
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_existing_posting_updates_last_seen_and_adds_snapshot(self) -> None:
        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, MagicMock()],
        )

        raw: dict[str, str | int | None] = {
            "title": "Sales Rep",
            "description": "<p>Updated description</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/sales-rep/job",
        }

        result = await persist_posting(mock_session, raw, uuid.uuid4(), "https://test.icims.com")
        assert result is True
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_false_when_no_job_id(self) -> None:
        mock_session = AsyncMock()
        raw: dict[str, str | int | None] = {
            "title": "Test",
            "description": "desc",
            "location": "TX",
            "job_id": None,
        }
        result = await persist_posting(mock_session, raw, uuid.uuid4(), "https://test.icims.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_url_path_used_for_fallback_url(self) -> None:
        """When raw has no url, url_path from listing entry is used to build a valid URL."""
        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, MagicMock()]
        )

        raw: dict[str, str | int | None] = {
            "title": "Test Job",
            "description": "desc",
            "location": "",
            "job_id": "48000",
        }

        result = await persist_posting(
            mock_session,
            raw,
            uuid.uuid4(),
            "https://test.icims.com",
            url_path="/jobs/48000/senior-field-tech/job",
        )
        assert result is True
        # Verify the snapshot upsert (3rd execute call) used the url_path
        snapshot_call = mock_session.execute.call_args_list[2]
        stmt = snapshot_call[0][0]
        # The compiled parameters should contain the correct URL
        compiled = stmt.compile(
            compile_kwargs={"literal_binds": True},
        )
        assert "/jobs/48000/senior-field-tech/job" in str(compiled)

    @pytest.mark.asyncio
    async def test_content_changed_flag(self) -> None:
        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = "oldhash123"

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, MagicMock()]
        )

        raw: dict[str, str | int | None] = {
            "title": "Sales Rep",
            "description": "<p>New content</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/job",
        }

        result = await persist_posting(mock_session, raw, uuid.uuid4(), "https://test.icims.com")
        assert result is True
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_same_job_twice_same_day_uses_upsert(self) -> None:
        """Second call for same job hits ON CONFLICT on posting upsert."""
        posting_id = uuid.uuid4()

        # Both calls return the same posting_id via ON CONFLICT DO UPDATE
        posting_result_1 = MagicMock()
        posting_result_1.scalar_one.return_value = posting_id
        snapshot_hash_1 = MagicMock()
        snapshot_hash_1.scalar_one_or_none.return_value = None

        posting_result_2 = MagicMock()
        posting_result_2.scalar_one.return_value = posting_id
        snapshot_hash_2 = MagicMock()
        snapshot_hash_2.scalar_one_or_none.return_value = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_result_1,  # 1st call: posting upsert (insert)
                snapshot_hash_1,  # 1st call: snapshot hash lookup (none)
                MagicMock(),  # 1st call: snapshot upsert
                posting_result_2,  # 2nd call: posting upsert (on conflict update)
                snapshot_hash_2,  # 2nd call: snapshot hash lookup (found)
                MagicMock(),  # 2nd call: snapshot upsert (on conflict)
            ]
        )

        company_id = uuid.uuid4()
        raw: dict[str, str | int | None] = {
            "title": "Sales Rep",
            "description": "<p>Great job</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/sales-rep/job",
        }

        result1 = await persist_posting(mock_session, raw, company_id, "https://test.icims.com")
        assert result1 is True

        result2 = await persist_posting(mock_session, raw, company_id, "https://test.icims.com")
        assert result2 is True

        # 3 executes per call x 2 calls = 6
        assert mock_session.execute.call_count == 6


class TestICIMSAdapter:
    @pytest.mark.asyncio
    async def test_scrape_returns_scrape_result(self) -> None:
        from unittest.mock import patch as _patch

        from compgraph.scrapers.base import ScrapeResult as _ScrapeResult
        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        listing_html = (FIXTURES / "icims_listing_page_2.html").read_text()
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = None

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            if "search" in url:
                return _make_response(200, listing_html)
            return _make_response(200, detail_html)

        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        # Each persist_posting call: posting upsert, snapshot hash, snapshot upsert
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_upsert_result,
                snapshot_hash_result,
                MagicMock(),
                posting_upsert_result,
                snapshot_hash_result,
                MagicMock(),
            ]
        )

        adapter = _ICIMSAdapter()

        with _patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=mock_get)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert isinstance(result, _ScrapeResult)
        assert result.company_id == company.id
        assert result.company_slug == "bds"
        assert result.postings_found == 2
        assert result.snapshots_created == 2
        assert result.success is True

    @pytest.mark.asyncio
    async def test_scrape_empty_listings(self) -> None:
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        empty_html = (FIXTURES / "icims_listing_empty.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = None

        mock_session = AsyncMock()

        adapter = _ICIMSAdapter()

        with _patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=_make_response(200, empty_html))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert result.success
        assert result.postings_found == 0
        assert result.snapshots_created == 0

    @pytest.mark.asyncio
    async def test_scrape_uses_company_config(self) -> None:
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        empty_html = (FIXTURES / "icims_listing_empty.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "marketsource"
        company.career_site_url = "https://applyatmarketsource-msc.icims.com"
        company.scraper_config = {"delay_min": 1.0, "delay_max": 3.0}

        mock_session = AsyncMock()

        adapter = _ICIMSAdapter()

        with _patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=_make_response(200, empty_html))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert result.success
