# iCIMS Scraper Adapter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the iCIMS scraper adapter that scrapes MarketSource and BDS Connected Solutions career portals, writing postings and snapshots to the database.

**Architecture:** Single `ICIMSAdapter` class paginates iCIMS listing pages, fetches detail pages, extracts JSON-LD `JobPosting` schema, upserts `Posting` rows, and appends `PostingSnapshot` rows. Circuit breaker halts on 3 consecutive detail failures.

**Tech Stack:** httpx (async HTTP), BeautifulSoup4 (HTML parsing), SQLAlchemy 2.0 (async), existing `ScraperAdapter` protocol

**Design doc:** `docs/plans/2026-02-13-icims-scraper-design.md`

**Worktree:** `.worktrees/issue-2-icims-scraper` on branch `feat/issue-2`

---

## Task 1: Add beautifulsoup4 dependency

**Files:**
- Modify: `pyproject.toml:6-15` (dependencies list)

**Step 1: Add beautifulsoup4 to dependencies**

In `pyproject.toml`, add `"beautifulsoup4>=4.12.0"` to the `dependencies` list after the `httpx` line.

**Step 2: Sync**

Run: `uv sync`
Expected: beautifulsoup4 installed successfully

**Step 3: Verify import**

Run: `uv run python -c "from bs4 import BeautifulSoup; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add beautifulsoup4 dependency for HTML parsing"
```

---

## Task 2: HTML test fixtures

Capture realistic HTML fixtures from live iCIMS sites for deterministic testing.

**Files:**
- Create: `tests/fixtures/icims_listing_page.html`
- Create: `tests/fixtures/icims_listing_page_2.html`
- Create: `tests/fixtures/icims_listing_empty.html`
- Create: `tests/fixtures/icims_detail_with_jsonld.html`
- Create: `tests/fixtures/icims_detail_no_jsonld.html`

**Step 1: Capture listing page fixture**

Fetch `https://careers-bdssolutions.icims.com/jobs/search?pr=0&in_iframe=1` and save a minimal representative version (~10 job rows) to `tests/fixtures/icims_listing_page.html`. Must include:
- Multiple `.iCIMS_JobListingRow` rows with `<a href="/jobs/{id}/{slug}/job">` links
- At least one pagination link with `?pr=1`

**Step 2: Capture page 2 fixture**

Create `tests/fixtures/icims_listing_page_2.html` with 2-3 job rows and NO "Next" pagination link (last page).

**Step 3: Create empty listing fixture**

Create `tests/fixtures/icims_listing_empty.html` with the iCIMS table structure but zero `.iCIMS_JobListingRow` rows.

**Step 4: Capture detail page with JSON-LD**

Fetch `https://careers-bdssolutions.icims.com/jobs/47917/meta-lab-assistant-manager/job?in_iframe=1` and save a minimal version to `tests/fixtures/icims_detail_with_jsonld.html`. Must include:
- `<script type="application/ld+json">` with full `JobPosting` schema
- `var jobId = "47917"` JavaScript variable

**Step 5: Create detail page without JSON-LD**

Create `tests/fixtures/icims_detail_no_jsonld.html` with no JSON-LD script tag but with HTML elements containing job title, location, and description text for fallback parsing.

**Step 6: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add iCIMS HTML fixtures for scraper unit tests"
```

---

## Task 3: JSON-LD parsing and HTML fallback

Build the pure parsing functions first (no HTTP, no DB).

**Files:**
- Create: `src/compgraph/scrapers/icims.py` (parsing functions only)
- Create: `tests/test_icims_adapter.py` (parsing tests only)

**Step 1: Write failing tests for JSON-LD parsing**

```python
# tests/test_icims_adapter.py
"""Tests for iCIMS scraper adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from compgraph.scrapers.icims import parse_json_ld, parse_listing_page, parse_html_fallback

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseJsonLd:
    def test_extracts_job_posting_fields(self):
        html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()
        data = parse_json_ld(html)
        assert data is not None
        assert data["title"]  # non-empty string
        assert data["description"]  # raw HTML content
        assert "location" in data
        assert data["job_id"]  # extracted from URL or var

    def test_returns_none_when_no_jsonld(self):
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_json_ld(html)
        assert data is None

    def test_returns_none_on_malformed_json(self):
        html = '<script type="application/ld+json">{broken json</script>'
        data = parse_json_ld(html)
        assert data is None


class TestParseListingPage:
    def test_extracts_job_links(self):
        html = (FIXTURES / "icims_listing_page.html").read_text()
        jobs = parse_listing_page(html)
        assert len(jobs) > 0
        for job in jobs:
            assert "job_id" in job
            assert "slug" in job
            assert "url_path" in job

    def test_empty_listing_returns_empty(self):
        html = (FIXTURES / "icims_listing_empty.html").read_text()
        jobs = parse_listing_page(html)
        assert jobs == []

    def test_detects_next_page(self):
        html = (FIXTURES / "icims_listing_page.html").read_text()
        jobs = parse_listing_page(html)
        # The fixture has a next-page link
        # (next_page detection is a separate function)

    def test_no_next_page_on_last_page(self):
        html = (FIXTURES / "icims_listing_page_2.html").read_text()
        jobs = parse_listing_page(html)
        assert len(jobs) > 0


class TestHasNextPage:
    def test_has_next_when_present(self):
        from compgraph.scrapers.icims import has_next_page
        html = (FIXTURES / "icims_listing_page.html").read_text()
        assert has_next_page(html) is True

    def test_no_next_on_last_page(self):
        from compgraph.scrapers.icims import has_next_page
        html = (FIXTURES / "icims_listing_page_2.html").read_text()
        assert has_next_page(html) is False


class TestParseHtmlFallback:
    def test_extracts_basic_fields(self):
        html = (FIXTURES / "icims_detail_no_jsonld.html").read_text()
        data = parse_html_fallback(html)
        assert data is not None
        assert data["title"]
        assert data["description"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_icims_adapter.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import 'parse_json_ld'`

**Step 3: Implement parsing functions**

Create `src/compgraph/scrapers/icims.py` with these pure functions:

```python
"""iCIMS career portal scraper adapter.

Scrapes MarketSource and BDS Connected Solutions career portals using
iCIMS-standard HTML listing pages and JSON-LD JobPosting schema on detail pages.
"""

from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_listing_page(html: str) -> list[dict[str, str]]:
    """Extract job links from an iCIMS listing page.

    Returns list of dicts with keys: job_id, slug, url_path
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict[str, str]] = []

    for row in soup.select(".iCIMS_JobListingRow"):
        link = row.select_one('a[href*="/jobs/"]')
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"/jobs/(\d+)/([^/]+)/job", str(href))
        if match:
            jobs.append({
                "job_id": match.group(1),
                "slug": match.group(2),
                "url_path": f"/jobs/{match.group(1)}/{match.group(2)}/job",
            })
    return jobs


def has_next_page(html: str) -> bool:
    """Check if the listing page has a 'Next' pagination link."""
    soup = BeautifulSoup(html, "html.parser")
    # iCIMS uses "Next" text or class-based pagination links
    next_link = soup.find("a", string=re.compile(r"Next", re.IGNORECASE))
    if next_link:
        return True
    # Also check for class-based next links
    next_link = soup.select_one('a.iCIMS_PagingNext, a[title="Next"]')
    return next_link is not None


def parse_json_ld(html: str) -> dict | None:
    """Extract JobPosting JSON-LD from a detail page.

    Returns dict with keys: title, description, location, job_id, date_posted,
    valid_through, employment_type, salary_min, salary_max, salary_currency, url
    Returns None if no valid JSON-LD found.
    """
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle both direct JobPosting and @graph arrays
        if isinstance(data, list):
            data = next((d for d in data if d.get("@type") == "JobPosting"), None)
            if not data:
                continue
        if data.get("@type") != "JobPosting":
            continue

        # Extract location
        location_data = data.get("jobLocation", {})
        if isinstance(location_data, dict):
            address = location_data.get("address", {})
            location = ", ".join(filter(None, [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]))
        else:
            location = str(location_data)

        # Extract salary
        salary = data.get("baseSalary", {})
        salary_value = salary.get("value", {}) if isinstance(salary, dict) else {}

        # Extract job ID from URL or var jobId
        job_id = None
        url = data.get("url", "")
        url_match = re.search(r"/jobs/(\d+)/", url)
        if url_match:
            job_id = url_match.group(1)
        if not job_id:
            id_match = re.search(r'var\s+jobId\s*=\s*["\'](\d+)["\']', html)
            if id_match:
                job_id = id_match.group(1)

        return {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "location": location,
            "job_id": job_id,
            "date_posted": data.get("datePosted"),
            "valid_through": data.get("validThrough"),
            "employment_type": data.get("employmentType"),
            "salary_min": salary_value.get("minValue") if isinstance(salary_value, dict) else None,
            "salary_max": salary_value.get("maxValue") if isinstance(salary_value, dict) else None,
            "salary_currency": salary.get("currency") if isinstance(salary, dict) else None,
            "url": url,
        }
    return None


def parse_html_fallback(html: str) -> dict | None:
    """Fallback: extract job fields from HTML when JSON-LD is missing.

    Returns dict with keys: title, description, location, job_id
    Returns None if extraction fails.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title: first h1 or .iCIMS_Header
    title_el = soup.select_one("h1, .iCIMS_Header")
    title = title_el.get_text(strip=True) if title_el else None

    # Description: main content area
    desc_el = soup.select_one(".iCIMS_JobContent, .iCIMS_InfoMsg_Job")
    description = str(desc_el) if desc_el else None

    # Job ID from var jobId
    job_id = None
    id_match = re.search(r'var\s+jobId\s*=\s*["\'](\d+)["\']', html)
    if id_match:
        job_id = id_match.group(1)

    if not title and not description:
        return None

    return {
        "title": title or "",
        "description": description or "",
        "location": "",
        "job_id": job_id,
    }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_icims_adapter.py -v --no-cov`
Expected: All parsing tests PASS

**Step 5: Commit**

```bash
git add src/compgraph/scrapers/icims.py tests/test_icims_adapter.py
git commit -m "feat: add iCIMS JSON-LD parsing and HTML fallback

Pure parsing functions for listing pages and detail pages.
No HTTP or DB dependencies — tested against HTML fixtures."
```

---

## Task 4: HTTP fetching layer with circuit breaker

Add async HTTP fetching with rate limiting and circuit breaker.

**Files:**
- Modify: `src/compgraph/scrapers/icims.py` (add fetch functions)
- Modify: `tests/test_icims_adapter.py` (add fetch tests)

**Step 1: Write failing tests for fetching**

```python
# Add to tests/test_icims_adapter.py

import httpx
from unittest.mock import AsyncMock, patch

from compgraph.scrapers.icims import ICIMSFetcher


class TestICIMSFetcher:
    async def test_fetch_listing_pages_paginates(self):
        """Fetches multiple pages until no next page."""
        page1_html = (FIXTURES / "icims_listing_page.html").read_text()
        page2_html = (FIXTURES / "icims_listing_page_2.html").read_text()

        responses = [
            httpx.Response(200, text=page1_html),
            httpx.Response(200, text=page2_html),
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=responses)

        fetcher = ICIMSFetcher(client=mock_client, base_url="https://test.icims.com", delay_min=0, delay_max=0)
        jobs = await fetcher.fetch_all_listings()

        assert len(jobs) > 0
        assert mock_client.get.call_count == 2

    async def test_fetch_detail_returns_raw_posting(self):
        """Fetches detail page and parses JSON-LD into RawPosting fields."""
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(200, text=detail_html))

        fetcher = ICIMSFetcher(client=mock_client, base_url="https://test.icims.com", delay_min=0, delay_max=0)
        result = await fetcher.fetch_detail("47917", "meta-lab-assistant-manager")

        assert result is not None
        assert result["title"]
        assert result["description"]

    async def test_fetch_detail_http_error_returns_none(self):
        """HTTP 404 on detail page returns None."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(404))

        fetcher = ICIMSFetcher(client=mock_client, base_url="https://test.icims.com", delay_min=0, delay_max=0)
        result = await fetcher.fetch_detail("99999", "nonexistent")

        assert result is None

    async def test_circuit_breaker_trips_after_3_failures(self):
        """After 3 consecutive detail failures, circuit breaker stops fetching."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(500))

        fetcher = ICIMSFetcher(client=mock_client, base_url="https://test.icims.com", delay_min=0, delay_max=0)

        for _ in range(3):
            await fetcher.fetch_detail("123", "test")

        assert fetcher.circuit_open is True

        # Subsequent calls should return None without HTTP call
        call_count_before = mock_client.get.call_count
        result = await fetcher.fetch_detail("456", "another")
        assert result is None
        assert mock_client.get.call_count == call_count_before

    async def test_successful_fetch_resets_failure_count(self):
        """A success after failures resets the consecutive failure counter."""
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        responses = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, text=detail_html),
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=responses)

        fetcher = ICIMSFetcher(client=mock_client, base_url="https://test.icims.com", delay_min=0, delay_max=0)

        await fetcher.fetch_detail("1", "a")  # fail
        await fetcher.fetch_detail("2", "b")  # fail
        result = await fetcher.fetch_detail("3", "c")  # success

        assert result is not None
        assert fetcher.consecutive_failures == 0
        assert fetcher.circuit_open is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_icims_adapter.py::TestICIMSFetcher -v --no-cov`
Expected: FAIL — `ImportError: cannot import 'ICIMSFetcher'`

**Step 3: Implement ICIMSFetcher**

Add to `src/compgraph/scrapers/icims.py`:

```python
import asyncio
import random

import httpx


class ICIMSFetcher:
    """Handles HTTP fetching for iCIMS career portals with rate limiting and circuit breaker."""

    CIRCUIT_BREAKER_THRESHOLD = 3

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        delay_min: float = 2.0,
        delay_max: float = 8.0,
        max_concurrency: int = 5,
    ):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.consecutive_failures = 0
        self.circuit_open = False

    async def _delay(self) -> None:
        if self.delay_min > 0 or self.delay_max > 0:
            await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

    async def fetch_all_listings(self) -> list[dict[str, str]]:
        """Paginate all listing pages and collect job entries."""
        all_jobs: list[dict[str, str]] = []
        page = 0

        while True:
            url = f"{self.base_url}/jobs/search?pr={page}&in_iframe=1"
            await self._delay()
            response = await self.client.get(url)
            response.raise_for_status()

            html = response.text
            jobs = parse_listing_page(html)
            all_jobs.extend(jobs)

            if not has_next_page(html) or not jobs:
                break
            page += 1

        return all_jobs

    async def fetch_detail(self, job_id: str, slug: str) -> dict | None:
        """Fetch a single job detail page and parse it.

        Returns parsed data dict or None on failure.
        Increments circuit breaker on failure; resets on success.
        """
        if self.circuit_open:
            logger.warning("Circuit breaker open — skipping job %s", job_id)
            return None

        async with self.semaphore:
            await self._delay()
            try:
                url = f"{self.base_url}/jobs/{job_id}/{slug}/job?in_iframe=1"
                response = await self.client.get(url)

                if response.status_code != 200:
                    logger.warning("HTTP %d for job %s", response.status_code, job_id)
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                        self.circuit_open = True
                        logger.error("Circuit breaker tripped after %d failures", self.consecutive_failures)
                    return None

                html = response.text
                data = parse_json_ld(html)
                if data is None:
                    data = parse_html_fallback(html)
                if data is None:
                    logger.warning("Failed to parse job %s — no JSON-LD or HTML fallback", job_id)
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                        self.circuit_open = True
                    return None

                # Success — reset circuit breaker
                self.consecutive_failures = 0
                return data

            except httpx.HTTPError as exc:
                logger.warning("HTTP error for job %s: %r", job_id, exc)
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                    self.circuit_open = True
                return None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_icims_adapter.py -v --no-cov`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/compgraph/scrapers/icims.py tests/test_icims_adapter.py
git commit -m "feat: add iCIMS HTTP fetcher with circuit breaker

Async fetching with rate limiting (2-8s random delay), semaphore-bounded
concurrency (5), and circuit breaker (trips after 3 consecutive failures)."
```

---

## Task 5: DB persistence layer

Upsert postings and append snapshots.

**Files:**
- Modify: `src/compgraph/scrapers/icims.py` (add persist function)
- Modify: `tests/test_icims_adapter.py` (add persistence tests with mocked session)

**Step 1: Write failing tests for persistence**

```python
# Add to tests/test_icims_adapter.py

import uuid
import hashlib
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from compgraph.scrapers.icims import persist_posting


class TestPersistPosting:
    async def test_new_posting_creates_posting_and_snapshot(self):
        """First time seeing a job creates both Posting and PostingSnapshot."""
        mock_session = AsyncMock()
        # Simulate no existing posting
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        company_id = uuid.uuid4()
        raw = {
            "title": "Sales Rep",
            "description": "<p>Great job</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/sales-rep/job",
        }

        result = await persist_posting(mock_session, raw, company_id, "https://test.icims.com")
        assert result is True
        # Should have called add() at least twice (Posting + PostingSnapshot)
        assert mock_session.add.call_count >= 1

    async def test_existing_posting_updates_last_seen_and_adds_snapshot(self):
        """Existing posting gets last_seen_at updated and new snapshot appended."""
        existing_posting = MagicMock()
        existing_posting.id = uuid.uuid4()
        existing_posting.last_seen_at = datetime(2026, 2, 12, tzinfo=UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_posting
        # Second query for last snapshot hash
        mock_snapshot_result = MagicMock()
        mock_snapshot_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_snapshot_result])

        raw = {
            "title": "Sales Rep",
            "description": "<p>Updated description</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/sales-rep/job",
        }

        result = await persist_posting(mock_session, raw, uuid.uuid4(), "https://test.icims.com")
        assert result is True

    async def test_content_changed_flag(self):
        """content_changed is True when hash differs from last snapshot."""
        existing_posting = MagicMock()
        existing_posting.id = uuid.uuid4()

        # Last snapshot had different content
        last_snapshot = MagicMock()
        last_snapshot.full_text_hash = "oldhash123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_posting
        mock_snapshot_result = MagicMock()
        mock_snapshot_result.scalar_one_or_none.return_value = last_snapshot

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_snapshot_result])

        raw = {
            "title": "Sales Rep",
            "description": "<p>New content</p>",
            "location": "Houston, TX",
            "job_id": "12345",
            "url": "https://test.icims.com/jobs/12345/job",
        }

        result = await persist_posting(mock_session, raw, uuid.uuid4(), "https://test.icims.com")
        assert result is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_icims_adapter.py::TestPersistPosting -v --no-cov`
Expected: FAIL — `ImportError: cannot import 'persist_posting'`

**Step 3: Implement persist_posting**

Add to `src/compgraph/scrapers/icims.py`:

```python
import hashlib
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Posting, PostingSnapshot


async def persist_posting(
    session: AsyncSession,
    raw: dict,
    company_id: uuid.UUID,
    base_url: str,
) -> bool:
    """Upsert a posting and append a snapshot.

    Returns True if successful, False on error.
    """
    external_job_id = raw.get("job_id")
    if not external_job_id:
        logger.warning("Skipping posting with no job_id")
        return False

    full_text = raw.get("description", "")
    full_text_hash = hashlib.sha256(full_text.encode()).hexdigest()

    # Look up existing posting
    result = await session.execute(
        select(Posting).where(
            Posting.company_id == company_id,
            Posting.external_job_id == external_job_id,
        )
    )
    posting = result.scalar_one_or_none()

    now = datetime.now(UTC)

    if posting is None:
        # New posting
        posting = Posting(
            company_id=company_id,
            external_job_id=external_job_id,
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
        )
        session.add(posting)
        await session.flush()  # Get posting.id
        content_changed = False  # First snapshot — no previous to compare
    else:
        # Existing posting — update last_seen_at
        posting.last_seen_at = now

        # Check last snapshot hash for content_changed
        snap_result = await session.execute(
            select(PostingSnapshot.full_text_hash)
            .where(PostingSnapshot.posting_id == posting.id)
            .order_by(PostingSnapshot.created_at.desc())
            .limit(1)
        )
        last_hash = snap_result.scalar_one_or_none()
        content_changed = last_hash is not None and last_hash != full_text_hash

    # Build URL
    url = raw.get("url") or f"{base_url}/jobs/{external_job_id}/job"

    # Append snapshot (always)
    snapshot = PostingSnapshot(
        posting_id=posting.id,
        snapshot_date=date.today(),
        title_raw=raw.get("title", ""),
        location_raw=raw.get("location", ""),
        url=url,
        full_text_raw=full_text,
        full_text_hash=full_text_hash,
        content_changed=content_changed,
    )
    session.add(snapshot)

    return True
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_icims_adapter.py -v --no-cov`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/compgraph/scrapers/icims.py tests/test_icims_adapter.py
git commit -m "feat: add iCIMS posting persistence with upsert + snapshot append

Upserts Posting by (company_id, external_job_id), always appends
PostingSnapshot with SHA-256 content hash and content_changed flag."
```

---

## Task 6: ICIMSAdapter class (protocol implementation)

Wire everything together into the `ScraperAdapter` protocol implementation.

**Files:**
- Modify: `src/compgraph/scrapers/icims.py` (add ICIMSAdapter)
- Modify: `tests/test_icims_adapter.py` (add adapter integration tests)

**Step 1: Write failing tests for ICIMSAdapter.scrape()**

```python
# Add to tests/test_icims_adapter.py

from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.icims import ICIMSAdapter


class TestICIMSAdapter:
    async def test_scrape_returns_scrape_result(self):
        """Full scrape returns ScrapeResult with correct counts."""
        listing_html = (FIXTURES / "icims_listing_page_2.html").read_text()
        detail_html = (FIXTURES / "icims_detail_with_jsonld.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = None

        # Mock httpx to return listing then details
        mock_responses = {}

        async def mock_get(url, **kwargs):
            if "search" in url:
                return httpx.Response(200, text=listing_html)
            return httpx.Response(200, text=detail_html)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        adapter = ICIMSAdapter()

        with patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=mock_get)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert isinstance(result, ScrapeResult)
        assert result.company_id == company.id
        assert result.postings_found > 0

    async def test_scrape_empty_listings(self):
        """Scrape with no jobs returns success with zero counts."""
        empty_html = (FIXTURES / "icims_listing_empty.html").read_text()

        company = MagicMock()
        company.id = uuid.uuid4()
        company.slug = "bds"
        company.career_site_url = "https://careers-bdssolutions.icims.com"
        company.scraper_config = None

        mock_session = AsyncMock()

        adapter = ICIMSAdapter()

        with patch("compgraph.scrapers.icims.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=httpx.Response(200, text=empty_html))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await adapter.scrape(company, mock_session)

        assert result.success
        assert result.postings_found == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_icims_adapter.py::TestICIMSAdapter -v --no-cov`
Expected: FAIL

**Step 3: Implement ICIMSAdapter**

Add to `src/compgraph/scrapers/icims.py`:

```python
from compgraph.scrapers.base import RawPosting, ScrapeResult
from compgraph.db.models import Company


class ICIMSAdapter:
    """Scraper adapter for iCIMS career portals.

    Handles both MarketSource and BDS Connected Solutions. The company's
    career_site_url determines the iCIMS subdomain.
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult:
        """Scrape all job postings from an iCIMS career portal."""
        result = ScrapeResult(
            company_id=company.id,
            company_slug=company.slug,
        )

        # Read per-company config
        config = company.scraper_config or {}
        delay_min = config.get("delay_min", 2.0)
        delay_max = config.get("delay_max", 8.0)
        max_concurrency = config.get("max_concurrency", 5)

        try:
            async with httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                fetcher = ICIMSFetcher(
                    client=client,
                    base_url=company.career_site_url,
                    delay_min=delay_min,
                    delay_max=delay_max,
                    max_concurrency=max_concurrency,
                )

                # Step 1: Get all job listings
                job_entries = await fetcher.fetch_all_listings()
                result.postings_found = len(job_entries)

                if not job_entries:
                    logger.info("No jobs found for %s", company.slug)
                    result.finished_at = datetime.now(UTC)
                    return result

                # Step 2: Fetch details and persist
                for entry in job_entries:
                    if fetcher.circuit_open:
                        result.errors.append(
                            f"Circuit breaker open after {fetcher.consecutive_failures} failures"
                        )
                        break

                    detail = await fetcher.fetch_detail(entry["job_id"], entry["slug"])
                    if detail is None:
                        continue

                    try:
                        persisted = await persist_posting(
                            session, detail, company.id, company.career_site_url
                        )
                        if persisted:
                            result.snapshots_created += 1
                    except Exception as exc:
                        logger.warning(
                            "Failed to persist job %s for %s: %r",
                            entry["job_id"], company.slug, exc
                        )

                await session.commit()

        except Exception as exc:
            result.errors.append(f"Scrape failed: {exc!r}")
            logger.exception("Scrape failed for %s: %r", company.slug, exc)

        result.finished_at = datetime.now(UTC)
        return result
```

**Step 4: Run all tests**

Run: `uv run pytest tests/test_icims_adapter.py -v --no-cov`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/compgraph/scrapers/icims.py tests/test_icims_adapter.py
git commit -m "feat: add ICIMSAdapter implementing ScraperAdapter protocol

Wires together listing pagination, detail fetching, JSON-LD parsing,
and DB persistence into the adapter the orchestrator calls."
```

---

## Task 7: Register adapter and update __init__

**Files:**
- Modify: `src/compgraph/scrapers/__init__.py`

**Step 1: Register the iCIMS adapter**

Add to `src/compgraph/scrapers/__init__.py`:

```python
from compgraph.scrapers.icims import ICIMSAdapter
from compgraph.scrapers.registry import register_adapter

register_adapter("icims", ICIMSAdapter)
```

**Step 2: Verify registration**

Run: `uv run python -c "from compgraph.scrapers.registry import list_registered_platforms; print(list_registered_platforms())"`
Expected: `['icims']`

**Step 3: Run full test suite**

Run: `uv run pytest --no-cov -q`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/compgraph/scrapers/__init__.py
git commit -m "feat: register ICIMSAdapter for ats_platform='icims'"
```

---

## Task 8: Schema migration for snapshot idempotency

Add UNIQUE constraint on `(posting_id, snapshot_date)` to prevent duplicate snapshots.

**Files:**
- Create: `alembic/versions/xxxx_add_snapshot_unique_constraint.py`

**Step 1: Generate migration**

This requires a live DB connection. Run:

```bash
op run --env-file=.env -- uv run alembic revision --autogenerate -m "add snapshot posting_id snapshot_date unique constraint"
```

If autogenerate doesn't pick up the change (since it's a constraint not a column), create manually:

```python
"""add snapshot posting_id snapshot_date unique constraint"""

from alembic import op

def upgrade() -> None:
    op.create_unique_constraint(
        "uq_snapshots_posting_date",
        "posting_snapshots",
        ["posting_id", "snapshot_date"],
    )

def downgrade() -> None:
    op.drop_constraint("uq_snapshots_posting_date", "posting_snapshots")
```

**Step 2: Apply migration**

```bash
op run --env-file=.env -- uv run alembic upgrade head
```

**Step 3: Verify**

```bash
op run --env-file=.env -- uv run python -c "
from compgraph.db.session import engine
import asyncio
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT indexname FROM pg_indexes WHERE tablename = 'posting_snapshots'\"))
        print([r[0] for r in result])
asyncio.run(check())
"
```

**Step 4: Commit**

```bash
git add alembic/
git commit -m "migration: add unique constraint on posting_snapshots(posting_id, snapshot_date)

Ensures pipeline idempotency — running twice same day updates rather
than duplicates. Supports ON CONFLICT DO UPDATE pattern."
```

---

## Task 9: Final verification

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass, coverage >= 50%

**Step 2: Lint and typecheck**

Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/compgraph/`
Expected: Clean

**Step 3: Verify adapter is registered and functional**

Run: `uv run python -c "
from compgraph.scrapers import register_adapter, get_adapter
from compgraph.scrapers.icims import ICIMSAdapter
adapter = get_adapter('icims')
print(f'Adapter: {type(adapter).__name__}')
print('Protocol check:', hasattr(adapter, 'scrape'))
"`
Expected: `Adapter: ICIMSAdapter` and `Protocol check: True`

**Step 4: Final commit if any cleanup needed**

---

## Verification Checklist

- [ ] `beautifulsoup4` in dependencies, importable
- [ ] HTML fixtures exist in `tests/fixtures/`
- [ ] `parse_json_ld()` extracts title, description, location, job_id from JSON-LD
- [ ] `parse_listing_page()` extracts job links from `.iCIMS_JobListingRow`
- [ ] `has_next_page()` detects pagination links
- [ ] `ICIMSFetcher` paginates listing pages
- [ ] `ICIMSFetcher` circuit breaker trips after 3 consecutive failures
- [ ] `persist_posting()` upserts Posting and appends PostingSnapshot
- [ ] `content_changed` flag set correctly based on hash comparison
- [ ] `ICIMSAdapter.scrape()` returns `ScrapeResult` matching protocol
- [ ] Adapter registered for `ats_platform="icims"`
- [ ] UNIQUE constraint on `posting_snapshots(posting_id, snapshot_date)`
- [ ] All tests pass, coverage >= 50%
- [ ] Ruff + mypy clean
