from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import uuid
from datetime import UTC, datetime
from typing import ClassVar

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company, Posting, PostingSnapshot
from compgraph.scrapers.base import ScrapeResult

logger = logging.getLogger(__name__)


def parse_listing_page(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict[str, str]] = []

    for row in soup.select(".iCIMS_JobListingRow"):
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
        if isinstance(location_data, dict):
            address = location_data.get("address", {})
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
        else:
            location = str(location_data)

        salary = data.get("baseSalary", {})
        salary_value = salary.get("value", {}) if isinstance(salary, dict) else {}

        job_id: str | None = None
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

    return {
        "title": title or "",
        "description": description or "",
        "location": "",
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
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.consecutive_failures = 0
        self.circuit_open = False

    async def _delay(self) -> None:
        if self.delay_min > 0 or self.delay_max > 0:
            await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))  # noqa: S311

    async def fetch_all_listings(self) -> list[dict[str, str]]:
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
            set_={"last_seen_at": now},
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

    url = raw.get("url") or f"{base_url}/jobs/{external_job_id}/job"

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


class ICIMSAdapter:
    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult:
        result = ScrapeResult(
            company_id=company.id,
            company_slug=company.slug,
        )

        config = company.scraper_config or {}
        delay_min = config.get("delay_min", 2.0)
        delay_max = config.get("delay_max", 8.0)

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
                )

                job_entries = await fetcher.fetch_all_listings()
                result.postings_found = len(job_entries)

                if not job_entries:
                    logger.info("No jobs found for %s", company.slug)
                    result.finished_at = datetime.now(UTC)
                    return result

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
                        async with session.begin_nested():
                            persisted = await persist_posting(
                                session, detail, company.id, company.career_site_url
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

                if fetcher.circuit_open and not any("Circuit breaker" in e for e in result.errors):
                    result.errors.append(
                        f"Circuit breaker open after {fetcher.consecutive_failures} failures"
                    )

                await session.commit()

        except Exception as exc:
            result.errors.append(f"Scrape failed: {exc!r}")
            logger.exception("Scrape failed for %s: %r", company.slug, exc)

        result.finished_at = datetime.now(UTC)
        return result
