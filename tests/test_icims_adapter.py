from __future__ import annotations

from pathlib import Path

from compgraph.scrapers.icims import (
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
