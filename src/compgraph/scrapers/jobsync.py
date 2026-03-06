"""Acosta Group JobSync (NLX/jobsyn.org) scraper adapter.

Covers the 9 agencies under the Acosta Group umbrella:
  Premium, Product Connections, Acosta, CROSSMARK, Mosaic, ActionLink,
  Acosta Group, CORE Foodservice, ADW.

API endpoint: GET https://prod-search-api.jobsyn.org/api/v1/solr/search
Required headers: X-Origin: acosta.jobs, Accept: application/json
Query params: page (1-indexed), num_items (max 14), agency (slug)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company, Posting, PostingSnapshot
from compgraph.scrapers.base import RawPosting, ScrapeResult
from compgraph.scrapers.proxy import get_proxy_client_kwargs, random_user_agent

logger = logging.getLogger(__name__)

JOBSYNC_API_BASE = "https://prod-search-api.jobsyn.org/api/v1/solr/search"
JOBSYNC_PAGE_SIZE = 14  # server-enforced maximum
JOBSYNC_X_ORIGIN = "acosta.jobs"
JOBSYNC_SITE_BASE = "https://acosta.jobs"
CIRCUIT_BREAKER_THRESHOLD = 3
DEFAULT_DELAY_MIN = 0.5
DEFAULT_DELAY_MAX = 1.5


@dataclass
class JobSyncPosting:
    """A single job posting as returned by the JobSync search API."""

    guid: str
    reqid: str
    title: str
    city: str
    state: str
    country: str
    description: str
    date_added: str
    date_updated: str
    agency_name: str  # resolved from the per-agency scrape context


@dataclass
class JobSyncPage:
    """A single page of results from the JobSync search API."""

    postings: list[JobSyncPosting]
    total_count: int
    current_page: int
    total_pages: int


def parse_job(item: dict, agency_name: str) -> JobSyncPosting:
    """Parse a single job dict from the API ``jobs`` list."""
    return JobSyncPosting(
        guid=item.get("guid", ""),
        reqid=item.get("reqid", ""),
        title=item.get("title_exact", item.get("title", "")),
        city=item.get("city_exact", item.get("city", "")),
        state=item.get("state_short", item.get("state", "")),
        country=item.get("country_exact", item.get("country", "")),
        description=item.get("description", ""),
        date_added=item.get("date_added", ""),
        date_updated=item.get("date_updated", ""),
        agency_name=agency_name,
    )


def parse_page(data: dict, agency_name: str) -> JobSyncPage:
    """Parse a full API response page into a ``JobSyncPage``."""
    pagination = data.get("pagination") or {}
    jobs_raw = data.get("jobs") or []
    postings = [parse_job(item, agency_name) for item in jobs_raw]
    return JobSyncPage(
        postings=postings,
        total_count=int(pagination.get("total_count", 0)),
        current_page=int(pagination.get("current_page", 1)),
        total_pages=int(pagination.get("total_pages", 1)),
    )


def build_posting_url(posting: JobSyncPosting) -> str:
    """Construct the canonical acosta.jobs posting URL.

    URL pattern: https://acosta.jobs/{city-state}/{title-slug}/{guid}/job/
    Falls back to a title-only path when location fields are missing.
    """
    title_slug = slugify(posting.title) if posting.title else "job"
    if posting.city and posting.state:
        location_slug = slugify(f"{posting.city} {posting.state}")
        return f"{JOBSYNC_SITE_BASE}/{location_slug}/{title_slug}/{posting.guid}/job/"
    return f"{JOBSYNC_SITE_BASE}/{title_slug}/{posting.guid}/job/"


def build_location_string(posting: JobSyncPosting) -> str:
    """Build a human-readable location string from posting fields."""
    parts = [p for p in (posting.city, posting.state, posting.country) if p]
    return ", ".join(parts)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker trips after consecutive failures."""


@dataclass
class JobSyncFetcher:
    """Fetches all pages for a single agency from the JobSync API."""

    api_base: str = JOBSYNC_API_BASE
    x_origin: str = JOBSYNC_X_ORIGIN
    page_size: int = JOBSYNC_PAGE_SIZE
    delay_min: float = DEFAULT_DELAY_MIN
    delay_max: float = DEFAULT_DELAY_MAX
    circuit_breaker_threshold: int = CIRCUIT_BREAKER_THRESHOLD
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _circuit_open: bool = field(default=False, init=False, repr=False)
    pages_fetched: int = field(default=0, init=False, repr=False)

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_breaker_threshold:
            self._circuit_open = True
            logger.error(
                "Circuit breaker OPEN after %d consecutive failures on JobSync API",
                self._consecutive_failures,
            )

    def _check_circuit(self) -> None:
        if self._circuit_open:
            raise CircuitBreakerOpen(
                f"Circuit breaker open after {self._consecutive_failures} consecutive failures"
            )

    async def fetch_page(
        self,
        client: httpx.AsyncClient,
        agency_slug: str,
        agency_name: str,
        page: int,
    ) -> JobSyncPage:
        """Fetch a single page for an agency. Page numbers are 1-indexed."""
        self._check_circuit()
        params: dict[str, str | int] = {
            "page": page,
            "num_items": self.page_size,
        }
        if agency_slug:
            params["agency"] = agency_slug

        try:
            resp = await client.get(
                self.api_base,
                params=params,
                headers={
                    "X-Origin": self.x_origin,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            result = parse_page(resp.json(), agency_name)
            self._record_success()
            self.pages_fetched += 1
            return result
        except Exception:
            self._record_failure()
            raise

    async def fetch_all_for_agency(
        self,
        client: httpx.AsyncClient,
        agency_slug: str,
        agency_name: str,
        delay: float = DEFAULT_DELAY_MIN,
    ) -> list[JobSyncPosting]:
        """Paginate through all pages for a single agency."""
        all_postings: list[JobSyncPosting] = []
        seen_guids: set[str] = set()
        page = 1

        while True:
            self._check_circuit()
            page_result = await self.fetch_page(client, agency_slug, agency_name, page)

            for posting in page_result.postings:
                if not posting.guid:
                    logger.warning(
                        "Skipping posting with no guid on page %d (title: %r)",
                        page,
                        posting.title,
                    )
                    continue
                if posting.guid not in seen_guids:
                    seen_guids.add(posting.guid)
                    all_postings.append(posting)

            if page >= page_result.total_pages or not page_result.postings:
                break

            page += 1
            await asyncio.sleep(delay)

        logger.info(
            "Fetched %d postings for agency %r (%d pages)",
            len(all_postings),
            agency_name,
            self.pages_fetched,
        )
        return all_postings


async def persist_posting(
    session: AsyncSession,
    company_id: uuid.UUID,
    raw: RawPosting,
    first_seen_at: datetime | None = None,
) -> bool:
    """Upsert a posting and append a snapshot for today if not already present.

    Returns True when a new snapshot was inserted, False when today's snapshot
    already existed (idempotent on same-day re-runs).
    """
    now = datetime.now(UTC)
    text_hash = _hash_text(raw.full_text) if raw.full_text else None

    posting_stmt = (
        pg_insert(Posting)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            external_job_id=raw.external_job_id,
            fingerprint_hash=text_hash,
            first_seen_at=first_seen_at or now,
            last_seen_at=now,
            is_active=True,
            times_reposted=0,
        )
        .on_conflict_do_update(
            index_elements=["company_id", "external_job_id"],
            set_={
                "last_seen_at": now,
                "is_active": True,
            },
        )
        .returning(Posting.id)
    )
    result = await session.execute(posting_stmt)
    posting_id = result.scalar_one()

    today = now.date()

    existing = await session.execute(
        select(PostingSnapshot.id).where(
            PostingSnapshot.posting_id == posting_id,
            PostingSnapshot.snapshot_date == today,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    prev_snapshot = await session.execute(
        select(PostingSnapshot.full_text_hash)
        .where(PostingSnapshot.posting_id == posting_id)
        .order_by(PostingSnapshot.snapshot_date.desc())
        .limit(1)
    )
    prev_hash = prev_snapshot.scalar_one_or_none()
    content_changed = prev_hash is not None and prev_hash != text_hash

    snapshot_stmt = pg_insert(PostingSnapshot).values(
        id=uuid.uuid4(),
        posting_id=posting_id,
        snapshot_date=today,
        title_raw=raw.title,
        location_raw=raw.location,
        url=raw.url,
        full_text_raw=raw.full_text,
        full_text_hash=text_hash,
        content_changed=content_changed,
    )
    snapshot_stmt = snapshot_stmt.on_conflict_do_nothing(constraint="uq_snapshots_posting_date")
    insert_result = await session.execute(snapshot_stmt)
    return insert_result.rowcount > 0  # type: ignore[no-any-return, attr-defined]


class JobSyncAdapter:
    """Scraper adapter for the Acosta Group JobSync (NLX) platform.

    Each company row in the ``companies`` table represents one agency.
    The ``scraper_config`` JSON must include:
      - ``agency_slug`` (str): agency filter slug (e.g. "premium")
      - ``agency_name`` (str): display name for tagging (e.g. "Premium")
      - ``api_base`` (optional str): override API base URL
      - ``x_origin`` (optional str): override X-Origin header value
      - ``page_size`` (optional int): override page size (max 14)
      - ``delay_min`` (optional float): min seconds between page requests
      - ``delay_max`` (optional float): max seconds between page requests
    """

    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult:
        result = ScrapeResult(company_id=company.id, company_slug=company.slug)

        config = company.scraper_config or {}
        agency_slug: str = config.get("agency_slug", "")
        agency_name: str = config.get("agency_name", company.name or company.slug)
        api_base: str = config.get("api_base", JOBSYNC_API_BASE)
        x_origin: str = config.get("x_origin", JOBSYNC_X_ORIGIN)
        page_size: int = int(config.get("page_size", JOBSYNC_PAGE_SIZE))
        delay_min: float = float(config.get("delay_min", DEFAULT_DELAY_MIN))
        delay_max: float = float(config.get("delay_max", DEFAULT_DELAY_MAX))

        if not agency_slug:
            result.errors.append(f"Missing agency_slug in scraper_config for {company.slug}")
            result.finished_at = datetime.now(UTC)
            return result

        # Use the midpoint of the delay range for page-to-page waits.
        page_delay = (delay_min + delay_max) / 2.0

        fetcher = JobSyncFetcher(
            api_base=api_base,
            x_origin=x_origin,
            page_size=page_size,
            delay_min=delay_min,
            delay_max=delay_max,
        )

        from compgraph.config import settings  # local import avoids circular dep at module level

        proxy_kwargs = get_proxy_client_kwargs(settings)
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": random_user_agent()},
                follow_redirects=True,
                **proxy_kwargs,
            ) as client:
                try:
                    postings = await fetcher.fetch_all_for_agency(
                        client,
                        agency_slug=agency_slug,
                        agency_name=agency_name,
                        delay=page_delay,
                    )
                except CircuitBreakerOpen as exc:
                    result.errors.append(str(exc))
                    result.finished_at = datetime.now(UTC)
                    return result
                except Exception as exc:
                    result.errors.append(f"API pagination failed: {exc!r}")
                    result.finished_at = datetime.now(UTC)
                    return result
        except Exception as exc:
            result.errors.append(f"HTTP client setup failed: {exc!r}")
            result.finished_at = datetime.now(UTC)
            return result

        result.postings_found = len(postings)
        result.pages_scraped = fetcher.pages_fetched

        for posting in postings:
            first_seen: datetime | None = None
            if posting.date_added:
                try:
                    parsed = datetime.fromisoformat(posting.date_added)
                    first_seen = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
                except ValueError:
                    logger.warning("Could not parse date_added: %s", posting.date_added)

            raw = RawPosting(
                external_job_id=posting.guid,
                title=posting.title,
                location=build_location_string(posting),
                url=build_posting_url(posting),
                full_text=posting.description,
            )

            try:
                async with session.begin_nested():
                    created = await persist_posting(
                        session, company.id, raw, first_seen_at=first_seen
                    )
                    if created:
                        result.snapshots_created += 1
            except Exception as exc:
                result.errors.append(f"Persist failed for {posting.guid}: {exc!r}")
                logger.warning("Failed to persist posting %s: %r", posting.guid, exc)

        await session.commit()
        result.finished_at = datetime.now(UTC)

        logger.info(
            "JobSync scrape for %s (%s) complete: %d found, %d snapshots, %d errors",
            company.slug,
            agency_name,
            result.postings_found,
            result.snapshots_created,
            len(result.errors),
        )
        return result
