from __future__ import annotations

import asyncio
import json
import logging
import random
import re

import httpx
from bs4 import BeautifulSoup

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
    next_link = soup.find("a", string=re.compile(r"Next", re.IGNORECASE))
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

        if isinstance(data, list):
            data = next((d for d in data if d.get("@type") == "JobPosting"), None)
            if not data:
                continue
        if data.get("@type") != "JobPosting":
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


def parse_html_fallback(html: str) -> dict[str, str | None] | None:
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
        max_concurrency: int = 5,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.semaphore = asyncio.Semaphore(max_concurrency)
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

        async with self.semaphore:
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
