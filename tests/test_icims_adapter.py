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

    def test_handles_job_location_as_list(self) -> None:
        html = """<script type="application/ld+json">
        {
          "@type": "JobPosting",
          "title": "Merchandiser",
          "description": "A merch role",
          "jobLocation": [
            {
              "@type": "Place",
              "address": {
                "@type": "PostalAddress",
                "addressLocality": "West Hollywood",
                "addressRegion": "CA",
                "addressCountry": "US"
              }
            }
          ],
          "url": "/jobs/50001/merchandiser/job"
        }
        </script>"""
        data = parse_json_ld(html)
        assert data is not None
        assert data["location"] == "West Hollywood, CA, US"

    def test_handles_empty_job_location_list(self) -> None:
        html = """<script type="application/ld+json">
        {
          "@type": "JobPosting",
          "title": "Remote Role",
          "description": "Remote work",
          "jobLocation": [],
          "url": "/jobs/50002/remote/job"
        }
        </script>"""
        data = parse_json_ld(html)
        assert data is not None
        assert data["location"] == ""


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

    def test_new_layout_extracts_jobs(self) -> None:
        """New iCIMS layout uses .iCIMS_JobsTable > .row instead of .iCIMS_JobListingRow."""
        html = (FIXTURES / "icims_listing_new_layout.html").read_text()
        jobs = parse_listing_page(html)
        assert len(jobs) == 3
        assert jobs[0]["job_id"] == "47939"
        assert jobs[0]["slug"] == "motorola-retail-territory-representative"
        assert jobs[2]["job_id"] == "47936"


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
    async def test_fetch_listing_with_search_url(self) -> None:
        """When search_url is set, it's used as the pagination base instead of base_url."""
        page1_html = (FIXTURES / "icims_listing_page_2.html").read_text()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(200, page1_html))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://careers-bdssolutions.icims.com",
            delay_min=0,
            delay_max=0,
            search_url="https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25262",
        )
        jobs = await fetcher.fetch_all_listings()

        assert len(jobs) == 2
        # Verify the search_url was used (with & separator since it has ?)
        called_url = mock_client.get.call_args_list[0][0][0]
        assert "searchCategory=25262" in called_url
        assert "&pr=0&in_iframe=1" in called_url

    @pytest.mark.asyncio
    async def test_fetch_listing_search_url_no_query_params(self) -> None:
        """When search_url has no query params, ? separator is used."""
        page1_html = (FIXTURES / "icims_listing_page_2.html").read_text()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_response(200, page1_html))

        fetcher = ICIMSFetcher(
            client=mock_client,
            base_url="https://careers-apolloretail.icims.com",
            delay_min=0,
            delay_max=0,
            search_url="https://careers-apolloretail.icims.com/jobs/search",
        )
        jobs = await fetcher.fetch_all_listings()

        assert len(jobs) == 2
        called_url = mock_client.get.call_args_list[0][0][0]
        assert "?pr=0&in_iframe=1" in called_url

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


class TestBaseUrlFromSearchUrl:
    def test_extracts_scheme_and_host(self) -> None:
        from compgraph.scrapers.icims import _base_url_from_search_url

        assert (
            _base_url_from_search_url(
                "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25262"
            )
            == "https://careers-bdssolutions.icims.com"
        )

    def test_strips_path_and_query(self) -> None:
        from compgraph.scrapers.icims import _base_url_from_search_url

        assert (
            _base_url_from_search_url("https://careers-apolloretail.icims.com/jobs/search")
            == "https://careers-apolloretail.icims.com"
        )


class TestPersistPosting:
    @pytest.mark.asyncio
    async def test_new_posting_creates_posting_and_snapshot(self) -> None:
        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, snapshot_insert_result]
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

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, snapshot_insert_result],
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

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, snapshot_insert_result]
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

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[posting_upsert_result, snapshot_hash_result, snapshot_insert_result]
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
    async def test_same_job_twice_same_day_skips_duplicate_snapshot(self) -> None:
        """Second call for same job updates last_seen_at but skips snapshot (do_nothing)."""
        posting_id = uuid.uuid4()

        # Both calls return the same posting_id via ON CONFLICT DO UPDATE
        posting_result_1 = MagicMock()
        posting_result_1.scalar_one.return_value = posting_id
        snapshot_hash_1 = MagicMock()
        snapshot_hash_1.scalar_one_or_none.return_value = None
        snapshot_insert_1 = MagicMock()
        snapshot_insert_1.rowcount = 1  # New snapshot inserted

        posting_result_2 = MagicMock()
        posting_result_2.scalar_one.return_value = posting_id
        snapshot_hash_2 = MagicMock()
        snapshot_hash_2.scalar_one_or_none.return_value = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        snapshot_insert_2 = MagicMock()
        snapshot_insert_2.rowcount = 0  # Conflict — do nothing

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_result_1,  # 1st call: posting upsert (insert)
                snapshot_hash_1,  # 1st call: snapshot hash lookup (none)
                snapshot_insert_1,  # 1st call: snapshot insert (new)
                posting_result_2,  # 2nd call: posting upsert (on conflict update)
                snapshot_hash_2,  # 2nd call: snapshot hash lookup (found)
                snapshot_insert_2,  # 2nd call: snapshot insert (conflict, do nothing)
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
        assert result1 is True  # New snapshot created

        result2 = await persist_posting(mock_session, raw, company_id, "https://test.icims.com")
        assert result2 is False  # Snapshot already existed, do nothing

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

        snapshot_insert_result = MagicMock()
        snapshot_insert_result.rowcount = 1

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        # Each persist_posting call: posting upsert, snapshot hash, snapshot insert
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_upsert_result,
                snapshot_hash_result,
                snapshot_insert_result,
                posting_upsert_result,
                snapshot_hash_result,
                snapshot_insert_result,
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

    @pytest.mark.asyncio
    async def test_scrape_multi_url_cross_portal(self) -> None:
        """Cross-portal jobs with same IDs are treated as distinct (per-portal dedup).

        Verifies that job_ids are prefixed with portal hostname to prevent
        DB unique constraint collisions on (company_id, external_job_id).
        """
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        listing_html = (FIXTURES / "icims_listing_page_2.html").read_text()
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = {
            "search_urls": [
                "https://careers-bdssolutions.icims.com/jobs/search",
                "https://careers-apolloretail.icims.com/jobs/search",
            ],
        }

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            if "search" in url:
                return _make_response(200, listing_html)
            return _make_response(200, detail_html)

        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        snap_ok = MagicMock()
        snap_ok.rowcount = 1

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        # 2 portals x 2 jobs each = 4 entries (iCIMS IDs are per-tenant, not global)
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
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

        assert result.success
        # Same IDs on different portals are distinct jobs
        assert result.postings_found == 4
        assert result.snapshots_created == 4
        # Verify portal-prefixed job IDs via the posting upsert SQL statements.
        # Every 3rd execute call (index 0, 3, 6, 9) is a posting upsert.
        execute_calls = mock_session.execute.call_args_list
        persisted_stmts: list[str] = []
        for i in range(0, len(execute_calls), 3):
            stmt = execute_calls[i][0][0]
            compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            persisted_stmts.append(str(compiled))
        bds_matches = [s for s in persisted_stmts if "careers-bdssolutions" in s]
        apollo_matches = [s for s in persisted_stmts if "careers-apolloretail" in s]
        assert len(bds_matches) == 2, f"Expected 2 BDS-prefixed IDs, got {persisted_stmts}"
        assert len(apollo_matches) == 2, f"Expected 2 Apollo-prefixed IDs, got {persisted_stmts}"

    @pytest.mark.asyncio
    async def test_scrape_multi_url_empty(self) -> None:
        """Multi-URL scraping handles empty results from all URLs."""
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        empty_html = (FIXTURES / "icims_listing_empty.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "marketsource"
        company.career_site_url = "https://applyatmarketsource-msc.icims.com"
        company.scraper_config = {
            "search_urls": [
                "https://applyatmarketsource-msc.icims.com/jobs/search",
                "https://careers-marketsource.icims.com/jobs/search",
            ],
        }

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

    @pytest.mark.asyncio
    async def test_scrape_multi_url_same_portal_keeps_plain_ids(self) -> None:
        """Single-portal multi-URL (2 category URLs on same domain) keeps plain numeric IDs."""
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        listing_html = (FIXTURES / "icims_listing_page_2.html").read_text()
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = {
            "search_urls": [
                "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=111",
                "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=222",
            ],
        }

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            if "search" in url:
                return _make_response(200, listing_html)
            return _make_response(200, detail_html)

        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        snap_ok = MagicMock()
        snap_ok.rowcount = 1

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        # Same portal, dedup means only 2 unique jobs (not 4)
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
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

        assert result.success
        # Same domain = 1 fetcher, so no portal prefix applied
        assert result.postings_found == 2
        assert result.snapshots_created == 2
        # Verify IDs are plain numeric (no portal prefix for single-portal)
        execute_calls = mock_session.execute.call_args_list
        for i in range(0, len(execute_calls), 3):
            stmt = execute_calls[i][0][0]
            compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            # Should NOT contain portal hostname prefix
            assert "careers-bdssolutions.icims.com:" not in compiled

    @pytest.mark.asyncio
    async def test_scrape_multi_url_isolates_failures(self) -> None:
        """One failing search URL doesn't abort scraping from other URLs."""
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        listing_html = (FIXTURES / "icims_listing_page_2.html").read_text()
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = {
            "search_urls": [
                "https://careers-bdssolutions.icims.com/jobs/search",
                "https://careers-apolloretail.icims.com/jobs/search",
            ],
        }

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            # First search URL fails, second succeeds
            if "search" in url and "bdssolutions" in url:
                raise httpx.ConnectError("DNS resolution failed")
            if "search" in url:
                return _make_response(200, listing_html)
            return _make_response(200, detail_html)

        posting_id = uuid.uuid4()
        posting_upsert_result = MagicMock()
        posting_upsert_result.scalar_one.return_value = posting_id
        snapshot_hash_result = MagicMock()
        snapshot_hash_result.scalar_one_or_none.return_value = None

        snap_ok = MagicMock()
        snap_ok.rowcount = 1

        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())
        mock_session.execute = AsyncMock(
            side_effect=[
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
                posting_upsert_result,
                snapshot_hash_result,
                snap_ok,
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

        # First URL failed but second URL's 2 jobs were still scraped
        assert result.postings_found == 2
        assert result.snapshots_created == 2
        # Partial success: failure goes to warnings, not errors
        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert "bdssolutions" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_scrape_multi_url_all_fail_reports_errors(self) -> None:
        """When all search URLs fail, result has errors and is not a silent success."""
        from unittest.mock import patch as _patch

        from compgraph.scrapers.icims import ICIMSAdapter as _ICIMSAdapter

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = {
            "search_urls": [
                "https://careers-bdssolutions.icims.com/jobs/search",
                "https://careers-apolloretail.icims.com/jobs/search",
            ],
        }

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("DNS resolution failed")

        mock_session = AsyncMock()
        adapter = _ICIMSAdapter()

        with _patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=mock_get)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert result.postings_found == 0
        # Both URLs failed — errors should be reported
        assert len(result.errors) == 2
        assert not result.success


class TestValidateRedirectDomain:
    def test_no_redirects_passes(self) -> None:
        from compgraph.scrapers.icims import _validate_redirect_domain

        response = httpx.Response(
            200,
            request=httpx.Request("GET", "https://careers-bds.icims.com/jobs/search"),
        )
        _validate_redirect_domain(response, "https://careers-bds.icims.com/jobs/search")

    def test_same_domain_redirect_passes(self) -> None:
        from compgraph.scrapers.icims import _validate_redirect_domain

        redirect_resp = httpx.Response(
            301,
            request=httpx.Request("GET", "https://careers-bds.icims.com/jobs/search"),
            headers={"Location": "https://careers-bds.icims.com/jobs/search?pr=0"},
        )
        final_resp = httpx.Response(
            200,
            request=httpx.Request("GET", "https://careers-bds.icims.com/jobs/search?pr=0"),
            history=[redirect_resp],
        )
        _validate_redirect_domain(final_resp, "https://careers-bds.icims.com/jobs/search")

    def test_different_domain_raises(self) -> None:
        from compgraph.scrapers.icims import _validate_redirect_domain

        redirect_resp = httpx.Response(
            301,
            request=httpx.Request("GET", "https://careers.advantagesolutions.net/jobs/search"),
            headers={"Location": "https://careers.youradv.com/"},
        )
        final_resp = httpx.Response(
            200,
            request=httpx.Request("GET", "https://careers.youradv.com/"),
            history=[redirect_resp],
        )
        with pytest.raises(ValueError, match="unexpected domain"):
            _validate_redirect_domain(
                final_resp, "https://careers.advantagesolutions.net/jobs/search"
            )

    def test_error_message_includes_chain(self) -> None:
        from compgraph.scrapers.icims import _validate_redirect_domain

        hop1 = httpx.Response(
            301,
            request=httpx.Request("GET", "https://old.example.com/a"),
            headers={"Location": "https://mid.example.com/b"},
        )
        hop2 = httpx.Response(
            302,
            request=httpx.Request("GET", "https://mid.example.com/b"),
            headers={"Location": "https://new.example.com/c"},
        )
        final = httpx.Response(
            200,
            request=httpx.Request("GET", "https://new.example.com/c"),
            history=[hop1, hop2],
        )
        with pytest.raises(
            ValueError, match=r"old\.example\.com.*mid\.example\.com.*new\.example\.com"
        ):
            _validate_redirect_domain(final, "https://old.example.com/a")

    def test_port_stripped_for_comparison(self) -> None:
        from compgraph.scrapers.icims import _validate_redirect_domain

        redirect_resp = httpx.Response(
            301,
            request=httpx.Request("GET", "https://careers-bds.icims.com:443/jobs"),
            headers={"Location": "https://careers-bds.icims.com/jobs"},
        )
        final_resp = httpx.Response(
            200,
            request=httpx.Request("GET", "https://careers-bds.icims.com/jobs"),
            history=[redirect_resp],
        )
        _validate_redirect_domain(final_resp, "https://careers-bds.icims.com:443/jobs")
