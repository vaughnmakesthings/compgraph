"""Scraper adapter protocol and shared data types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company
from compgraph.scrapers.proxy import get_proxy_client_kwargs, random_user_agent


@dataclass
class RawPosting:
    """A single posting as scraped from the career site."""

    external_job_id: str
    title: str
    location: str
    url: str
    full_text: str


@dataclass
class ScrapeResult:
    """Result of scraping a single company."""

    company_id: uuid.UUID
    company_slug: str
    postings_found: int = 0
    snapshots_created: int = 0
    postings_closed: int = 0
    pages_scraped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@runtime_checkable
class ScraperAdapter(Protocol):
    """Protocol that all scraper adapters must implement.

    The orchestrator calls scrape() once per company. The adapter is responsible
    for listing postings, fetching details, and persisting to the database.
    """

    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult: ...


def create_scraper_client(
    settings: Any,
    domain: str,
    timeout: float = 30.0,
    follow_redirects: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> httpx.AsyncClient:
    proxy_kwargs = get_proxy_client_kwargs(settings, domain=domain)
    headers = {"User-Agent": random_user_agent()}
    if extra_headers:
        headers.update(extra_headers)
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=follow_redirects,
        **proxy_kwargs,
    )
