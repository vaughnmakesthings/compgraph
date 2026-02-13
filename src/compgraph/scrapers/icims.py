from __future__ import annotations

import json
import logging
import re

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
