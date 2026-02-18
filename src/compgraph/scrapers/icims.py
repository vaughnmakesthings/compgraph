from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.config import settings
from compgraph.db.models import Company, Posting, PostingSnapshot
from compgraph.scrapers.base import ScrapeResult
from compgraph.scrapers.proxy import get_proxy_client_kwargs, random_user_agent

logger = logging.getLogger(__name__)


def parse_listing_page(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict[str, str]] = []

    # Try legacy iCIMS layout first, then new .row-based layout
    rows = soup.select(".iCIMS_JobListingRow")
    if not rows:
        jobs_table = soup.select_one(".iCIMS_JobsTable")
        if jobs_table:
            rows = jobs_table.select(":scope > .row")

    for row in rows:
        link = row.select_one('a[href*="/jobs/"]')
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"/jobs/(\d+)/([^/]+)/job", str(href))
        if match:
            jobs.append(
                {
                    "job_id": match.group(1),
                    "slug": match.group(2),
                    "url_path": f"/jobs/{match.group(1)}/{match.group(2)}/job",
                }
            )
    return jobs


def has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.find("a", string=re.compile(r"^\s*Next\s*$", re.IGNORECASE))  # type: ignore[call-overload]
    if next_link:
        return True
    next_link = soup.select_one('a.iCIMS_PagingNext, a[title="Next"]')
    return next_link is not None


def parse_json_ld(html: str) -> dict[str, str | int | None] | None:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, dict) and "@graph" in data:
            data = data["@graph"]
        if isinstance(data, list):
            data = next(
                (d for d in data if isinstance(d, dict) and d.get("@type") == "JobPosting"),
                None,
            )
            if not data:
                continue
        if not isinstance(data, dict) or data.get("@type") != "JobPosting":
            continue

        location_data = data.get("jobLocation", {})
        if isinstance(location_data, list):
            location_data = location_data[0] if location_data else {}
        if isinstance(location_data, dict):
            address = location_data.get("address", {})
            if isinstance(address, dict):
                location = ", ".join(
                    filter(
                        None,
                        [
                            address.get("addressLocality"),
                            address.get("addressRegion"),
                            address.get("addressCountry"),
                        ],
                    )
                )
            elif isinstance(address, str):
                location = address
            else:
                location = ""
        else:
            location = str(location_data)

        salary = data.get("baseSalary", {})
        salary_value = salary.get("value", {}) if isinstance(salary, dict) else {}

        job_id: str | None = None
        url = str(data.get("url") or "")
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


def parse_html_fallback(html: str) -> dict[str, str | int | None] | None:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1, .iCIMS_Header")
    title = title_el.get_text(strip=True) if title_el else None

    desc_el = soup.select_one(".iCIMS_JobContent, .iCIMS_InfoMsg_Job")
    description = str(desc_el) if desc_el else None

    job_id: str | None = None
    id_match = re.search(r'var\s+jobId\s*=\s*["\'](\d+)["\']', html)
    if id_match:
        job_id = id_match.group(1)

    if not title and not description:
        return None

    # Extract location from common iCIMS location elements
    location = ""
    loc_el = soup.select_one(
        ".iCIMS_JobHeaderData .iCIMS_JobHeaderField:-soup-contains('Location'),"
        " .header-location, .iCIMS_InfoField_Job:-soup-contains('Location')"
    )
    if loc_el:
        # Get sibling or child text that contains the actual location value
        value_el = loc_el.find_next_sibling() or loc_el
        location = value_el.get_text(strip=True)
    if not location:
        # Fallback: look for common location patterns in meta tags
        meta_loc = soup.find("meta", attrs={"name": "location"}) or soup.find(
            "meta", attrs={"property": "og:location"}
        )
        if meta_loc:
            location = meta_loc.get("content", "")  # type: ignore[assignment]

    return {
        "title": title or "",
        "description": description or "",
        "location": location,
        "job_id": job_id,
    }


class ICIMSFetcher:
    CIRCUIT_BREAKER_THRESHOLD = 3

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        delay_min: float = 2.0,
        delay_max: float = 8.0,
        search_url: str | None = None,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.search_url = search_url
        self.consecutive_failures = 0
        self.circuit_open = False
        self.pages_fetched = 0

    async def _delay(self) -> None:
        if self.delay_min > 0 or self.delay_max > 0:
            await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))  # noqa: S311

    async def fetch_all_listings(self) -> list[dict[str, str]]:
        all_jobs: list[dict[str, str]] = []
        page = 0

        while True:
            if self.search_url:
                sep = "&" if "?" in self.search_url else "?"
                url = f"{self.search_url}{sep}pr={page}&in_iframe=1"
            else:
                url = f"{self.base_url}/jobs/search?pr={page}&in_iframe=1"
            await self._delay()
            response = await self.client.get(url)
            response.raise_for_status()

            html = response.text
            jobs = parse_listing_page(html)
            all_jobs.extend(jobs)
            if jobs or page > 0:
                self.pages_fetched += 1

            if not has_next_page(html) or not jobs:
                break
            page += 1

        return all_jobs

    async def fetch_detail(self, job_id: str, slug: str) -> dict[str, str | int | None] | None:
        if self.circuit_open:
            logger.warning("Circuit breaker open — skipping job %s", job_id)
            return None

        await self._delay()
        try:
            url = f"{self.base_url}/jobs/{job_id}/{slug}/job?in_iframe=1"
            response = await self.client.get(url)

            if response.status_code != 200:
                logger.warning("HTTP %d for job %s", response.status_code, job_id)
                self._record_failure()
                return None

            html = response.text
            data = parse_json_ld(html)
            if data is None:
                data = parse_html_fallback(html)
            if data is None:
                logger.warning("Failed to parse job %s — no JSON-LD or HTML fallback", job_id)
                self._record_failure()
                return None

            self.consecutive_failures = 0
            return data

        except httpx.HTTPError as exc:
            logger.warning("HTTP error for job %s: %r", job_id, exc)
            self._record_failure()
            return None

    def _record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
            self.circuit_open = True
            logger.error(
                "Circuit breaker tripped after %d failures",
                self.consecutive_failures,
            )


async def persist_posting(
    session: AsyncSession,
    raw: dict[str, str | int | None],
    company_id: uuid.UUID,
    base_url: str,
    url_path: str | None = None,
) -> bool:
    external_job_id = raw.get("job_id")
    if not external_job_id:
        logger.warning("Skipping posting with no job_id")
        return False

    full_text = str(raw.get("description", ""))
    full_text_hash = hashlib.sha256(full_text.encode()).hexdigest()

    now = datetime.now(UTC)

    posting_result = await session.execute(
        pg_insert(Posting)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            external_job_id=str(external_job_id),
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
        )
        .on_conflict_do_update(
            index_elements=["company_id", "external_job_id"],
            set_={"last_seen_at": now, "is_active": True},
        )
        .returning(Posting.id)
    )
    posting_id = posting_result.scalar_one()

    snap_result = await session.execute(
        select(PostingSnapshot.full_text_hash)
        .where(PostingSnapshot.posting_id == posting_id)
        .order_by(PostingSnapshot.created_at.desc())
        .limit(1)
    )
    last_hash = snap_result.scalar_one_or_none()
    content_changed = last_hash is not None and last_hash != full_text_hash

    raw_url = raw.get("url") or ""
    if raw_url and not str(raw_url).startswith("http"):
        raw_url = f"{base_url}{raw_url}"
    url = raw_url or (
        f"{base_url}{url_path}" if url_path else f"{base_url}/jobs/{external_job_id}/job"
    )

    snapshot_date = datetime.now(UTC).date()
    stmt = pg_insert(PostingSnapshot).values(
        id=uuid.uuid4(),
        posting_id=posting_id,
        snapshot_date=snapshot_date,
        title_raw=str(raw.get("title", "")),
        location_raw=str(raw.get("location", "")),
        url=str(url),
        full_text_raw=full_text,
        full_text_hash=full_text_hash,
        content_changed=content_changed,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_snapshots_posting_date",
        set_={
            "title_raw": str(raw.get("title", "")),
            "location_raw": str(raw.get("location", "")),
            "url": str(url),
            "full_text_raw": full_text,
            "full_text_hash": full_text_hash,
            "content_changed": stmt.excluded.content_changed
            | PostingSnapshot.__table__.c.content_changed,
        },
    )
    await session.execute(stmt)

    return True


def _base_url_from_search_url(search_url: str) -> str:
    """Extract scheme + host from a full search URL for use as base_url."""

    parsed = urlparse(search_url)
    return f"{parsed.scheme}://{parsed.netloc}"


class ICIMSAdapter:
    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult:
        result = ScrapeResult(
            company_id=company.id,
            company_slug=company.slug,
        )

        config = company.scraper_config or {}
        delay_min = config.get("delay_min", 2.0)
        delay_max = config.get("delay_max", 8.0)
        search_urls: list[str] = config.get("search_urls", [])

        proxy_kwargs = get_proxy_client_kwargs(settings)
        headers = {"User-Agent": random_user_agent()}

        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                **proxy_kwargs,
            ) as client:
                # Collect job entries — multi-URL or single default
                if search_urls:
                    job_entries, failed_urls, pages = await self._fetch_multi_url(
                        client, search_urls, delay_min, delay_max
                    )
                    result.pages_scraped = pages
                    if failed_urls and job_entries:
                        # Partial success — warn, don't error
                        for url in failed_urls:
                            result.warnings.append(f"Failed to fetch listings from {url}")
                    elif failed_urls:
                        # Total failure — error
                        for url in failed_urls:
                            result.errors.append(f"Failed to fetch listings from {url}")
                else:
                    fetcher = ICIMSFetcher(
                        client=client,
                        base_url=company.career_site_url,
                        delay_min=delay_min,
                        delay_max=delay_max,
                    )
                    job_entries = [
                        (entry, company.career_site_url)
                        for entry in await fetcher.fetch_all_listings()
                    ]
                    result.pages_scraped = fetcher.pages_fetched

                result.postings_found = len(job_entries)

                if not job_entries:
                    logger.info("No jobs found for %s", company.slug)
                    result.finished_at = datetime.now(UTC)
                    return result

                # Determine portal count from config (not runtime results) to ensure
                # consistent ID prefixing across runs, even when a portal is down.
                if search_urls:
                    distinct_portals = len({_base_url_from_search_url(u) for u in search_urls})
                else:
                    distinct_portals = 1
                fetchers: dict[str, ICIMSFetcher] = {}
                for entry, base_url in job_entries:
                    if base_url not in fetchers:
                        fetchers[base_url] = ICIMSFetcher(
                            client=client,
                            base_url=base_url,
                            delay_min=delay_min,
                            delay_max=delay_max,
                        )

                    fetcher = fetchers[base_url]
                    if fetcher.circuit_open:
                        result.errors.append(
                            f"Circuit breaker open for {base_url} after "
                            f"{fetcher.consecutive_failures} failures"
                        )
                        continue

                    detail = await fetcher.fetch_detail(entry["job_id"], entry["slug"])
                    if detail is None:
                        continue

                    # Disambiguate cross-portal IDs when multiple portals present
                    if distinct_portals > 1 and detail.get("job_id"):
                        portal_host = urlparse(base_url).netloc
                        detail["job_id"] = f"{portal_host}:{detail['job_id']}"

                    try:
                        async with session.begin_nested():
                            persisted = await persist_posting(
                                session,
                                detail,
                                company.id,
                                base_url,
                                url_path=entry.get("url_path"),
                            )
                        if persisted:
                            result.snapshots_created += 1
                    except Exception as exc:
                        logger.warning(
                            "Failed to persist job %s for %s: %r",
                            entry["job_id"],
                            company.slug,
                            exc,
                        )

                # Report any tripped circuit breakers
                for base_url, fetcher in fetchers.items():
                    if fetcher.circuit_open and not any(base_url in e for e in result.errors):
                        result.errors.append(
                            f"Circuit breaker open for {base_url} after "
                            f"{fetcher.consecutive_failures} failures"
                        )

                await session.commit()

        except Exception as exc:
            result.errors.append(f"Scrape failed: {exc!r}")
            logger.exception("Scrape failed for %s: %r", company.slug, exc)

        result.finished_at = datetime.now(UTC)
        return result

    async def _fetch_multi_url(
        self,
        client: httpx.AsyncClient,
        search_urls: list[str],
        delay_min: float,
        delay_max: float,
    ) -> tuple[list[tuple[dict[str, str], str]], list[str], int]:
        """Fetch listings from multiple search URLs, deduplicating by (base_url, job_id).

        Dedup is scoped per-portal (base_url) since iCIMS job IDs are per-tenant.
        The same numeric ID on different portals represents different jobs.

        Returns (entries, failed_urls, pages_scraped) where failed_urls lists URLs
        that raised exceptions.
        """
        seen: set[tuple[str, str]] = set()  # (base_url, job_id)
        entries: list[tuple[dict[str, str], str]] = []
        failed_urls: list[str] = []
        total_pages = 0

        for search_url in search_urls:
            base_url = _base_url_from_search_url(search_url)
            fetcher = ICIMSFetcher(
                client=client,
                base_url=base_url,
                delay_min=delay_min,
                delay_max=delay_max,
                search_url=search_url,
            )
            try:
                jobs = await fetcher.fetch_all_listings()
            except Exception as exc:
                logger.warning("Failed to fetch listings from %s: %r", search_url, exc)
                failed_urls.append(search_url)
                total_pages += fetcher.pages_fetched
                continue
            total_pages += fetcher.pages_fetched
            for job in jobs:
                key = (base_url, job["job_id"])
                if key not in seen:
                    seen.add(key)
                    entries.append((job, base_url))
                else:
                    logger.debug(
                        "Dedup: skipping job %s on %s (already seen)",
                        job["job_id"],
                        base_url,
                    )

        return entries, failed_urls, total_pages
