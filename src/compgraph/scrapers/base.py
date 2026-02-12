"""Scraper adapter protocol and shared data types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company


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
    errors: list[str] = field(default_factory=list)
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
