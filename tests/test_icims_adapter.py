from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from compgraph.scrapers.icims import (
    ICIMSFetcher,
    has_next_page,
    parse_html_fallback,
    parse_json_ld,
    parse_listing_page,
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


class TestParseHtmlFallback:
    def test_extracts_basic_fields(self) -> None:
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_html_fallback(html)
        assert data is not None
        assert data["title"] == "Senior Field Technician"
        assert "field experience" in data["description"]
        assert data["job_id"] == "48000"

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
