from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.config import settings
from compgraph.db.models import Company, Posting, PostingSnapshot
from compgraph.scrapers.base import RawPosting, ScrapeResult
from compgraph.scrapers.proxy import get_proxy_client_kwargs, random_user_agent

logger = logging.getLogger(__name__)

WORKDAY_PAGE_SIZE = 20
SEARCH_DELAY_SECONDS = 1.0
DETAIL_DELAY_SECONDS = 0.5
DETAIL_CONCURRENCY = 5
CIRCUIT_BREAKER_THRESHOLD = 3


@dataclass
class SearchResult:
    total: int
    postings: list[SearchPosting]


@dataclass
class SearchPosting:
    title: str
    external_path: str
    location: str
    posted_on: str
    bullet_fields: list[str]
    time_type: str


@dataclass
class DetailResult:
    job_req_id: str
    title: str
    description_html: str
    location: str
    start_date: str | None
    time_type: str
    external_url: str
    country: str | None
    remote: bool
    additional_locations: list[str]


def parse_search_response(data: dict) -> SearchResult:
    total = data.get("total") or 0
    raw_postings = data.get("jobPostings") or []
    postings: list[SearchPosting] = []
    for item in raw_postings:
        postings.append(
            SearchPosting(
                title=item.get("title", ""),
                external_path=item.get("externalPath", ""),
                location=item.get("locationsText", ""),
                posted_on=item.get("postedOn", ""),
                bullet_fields=item.get("bulletFields", []),
                time_type=item.get("timeType", ""),
            )
        )
    return SearchResult(total=total, postings=postings)


def parse_detail_response(data: dict) -> DetailResult:
    info = data.get("jobPostingInfo", {})
    return DetailResult(
        job_req_id=info.get("jobReqId", ""),
        title=info.get("title", ""),
        description_html=info.get("jobDescription", ""),
        location=info.get("location", ""),
        start_date=info.get("startDate"),
        time_type=info.get("timeType", ""),
        external_url=info.get("externalUrl", ""),
        country=info.get("country"),
        remote=info.get("remote", False),
        additional_locations=info.get("additionalLocations") or [],
    )


def _build_search_url(base_url: str, tenant: str, site: str) -> str:
    return f"{base_url}/wday/cxs/{tenant}/{site}/jobs"


_EXTERNAL_PATH_PREFIX = re.compile(r"^(?:[a-z]{2}-[A-Z]{2}/)?job/")


def _build_detail_url(base_url: str, tenant: str, site: str, external_path: str) -> str:
    cleaned = _EXTERNAL_PATH_PREFIX.sub("", external_path.lstrip("/"))
    return f"{base_url}/wday/cxs/{tenant}/{site}/job/{cleaned}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class CircuitBreakerOpen(Exception):
    pass


@dataclass
class WorkdayFetcher:
    base_url: str
    tenant: str
    site: str
    search_delay: float = SEARCH_DELAY_SECONDS
    detail_delay: float = DETAIL_DELAY_SECONDS
    detail_concurrency: int = DETAIL_CONCURRENCY
    circuit_breaker_threshold: int = CIRCUIT_BREAKER_THRESHOLD
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _circuit_open: bool = field(default=False, init=False, repr=False)

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_breaker_threshold:
            self._circuit_open = True
            logger.error(
                "Circuit breaker OPEN after %d consecutive failures for %s/%s",
                self._consecutive_failures,
                self.tenant,
                self.site,
            )

    def _check_circuit(self) -> None:
        if self._circuit_open:
            raise CircuitBreakerOpen(
                f"Circuit breaker open for {self.tenant}/{self.site} "
                f"after {self._consecutive_failures} consecutive failures"
            )

    async def fetch_search_page(self, client: httpx.AsyncClient, offset: int) -> SearchResult:
        self._check_circuit()
        url = _build_search_url(self.base_url, self.tenant, self.site)
        payload = {
            "appliedFacets": {},
            "limit": WORKDAY_PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }
        try:
            resp = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = parse_search_response(resp.json())
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    async def fetch_all_postings(self, client: httpx.AsyncClient) -> list[SearchPosting]:
        seen_paths: set[str] = set()
        all_postings: list[SearchPosting] = []
        offset = 0

        while True:
            self._check_circuit()
            result = await self.fetch_search_page(client, offset)

            if not result.postings:
                break

            for posting in result.postings:
                if posting.external_path not in seen_paths:
                    seen_paths.add(posting.external_path)
                    all_postings.append(posting)

            offset += WORKDAY_PAGE_SIZE
            if offset >= result.total:
                break

            await asyncio.sleep(self.search_delay)

        logger.info(
            "Fetched %d unique postings from %s/%s (total reported: %d)",
            len(all_postings),
            self.tenant,
            self.site,
            result.total if result.postings or offset == 0 else 0,
        )
        return all_postings

    async def fetch_detail(self, client: httpx.AsyncClient, external_path: str) -> DetailResult:
        self._check_circuit()
        url = _build_detail_url(self.base_url, self.tenant, self.site, external_path)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            result = parse_detail_response(resp.json())
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    async def fetch_details_batch(
        self, client: httpx.AsyncClient, external_paths: list[str]
    ) -> dict[str, DetailResult]:
        semaphore = asyncio.Semaphore(self.detail_concurrency)
        results: dict[str, DetailResult] = {}
        errors: list[str] = []

        async def _fetch_one(path: str) -> None:
            async with semaphore:
                try:
                    self._check_circuit()
                    detail = await self.fetch_detail(client, path)
                    results[path] = detail
                except CircuitBreakerOpen:
                    errors.append(f"Circuit breaker open, skipping {path}")
                    raise
                except Exception as exc:
                    errors.append(f"Failed to fetch detail for {path}: {exc!r}")
                    logger.warning("Detail fetch failed for %s: %r", path, exc)
                finally:
                    await asyncio.sleep(self.detail_delay)

        tasks = [_fetch_one(path) for path in external_paths]
        gather_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in gather_results:
            if isinstance(result, CircuitBreakerOpen):
                logger.error("Detail batch hit circuit breaker")
                break

        if errors:
            logger.warning("Detail fetch had %d errors out of %d", len(errors), len(external_paths))

        return results


async def persist_posting(
    session: AsyncSession,
    company_id: uuid.UUID,
    raw: RawPosting,
    first_seen_at: datetime | None = None,
) -> bool:
    now = datetime.now(UTC)
    fingerprint = _hash_text(raw.full_text) if raw.full_text else None

    posting_stmt = (
        pg_insert(Posting)
        .values(
            id=uuid.uuid4(),
            company_id=company_id,
            external_job_id=raw.external_job_id,
            fingerprint_hash=fingerprint,
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

    today = date.today()
    text_hash = _hash_text(raw.full_text) if raw.full_text else None

    existing_snapshot = await session.execute(
        select(PostingSnapshot.id).where(
            PostingSnapshot.posting_id == posting_id,
            PostingSnapshot.snapshot_date == today,
        )
    )
    if existing_snapshot.scalar_one_or_none() is not None:
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
    await session.execute(snapshot_stmt)
    return True


class WorkdayAdapter:
    async def scrape(self, company: Company, session: AsyncSession) -> ScrapeResult:
        result = ScrapeResult(company_id=company.id, company_slug=company.slug)

        if not company.career_site_url:
            result.errors.append(f"Missing career_site_url for {company.slug}")
            result.finished_at = datetime.now(UTC)
            return result

        config = company.scraper_config or {}
        tenant = config.get("tenant") or company.slug
        site = config.get("site") or "External_Careers"

        if not tenant or not site:
            result.errors.append(
                f"Invalid scraper_config for {company.slug}: tenant={tenant!r}, site={site!r}"
            )
            result.finished_at = datetime.now(UTC)
            return result

        base_url = company.career_site_url.rstrip("/")

        fetcher = WorkdayFetcher(base_url=base_url, tenant=tenant, site=site)

        proxy_kwargs = get_proxy_client_kwargs(settings)
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": random_user_agent()},
            **proxy_kwargs,
        ) as client:
            try:
                search_postings = await fetcher.fetch_all_postings(client)
            except CircuitBreakerOpen as exc:
                result.errors.append(str(exc))
                result.finished_at = datetime.now(UTC)
                return result
            except Exception as exc:
                result.errors.append(f"Search pagination failed: {exc!r}")
                result.finished_at = datetime.now(UTC)
                return result

            result.postings_found = len(search_postings)

            external_paths = [p.external_path for p in search_postings]
            try:
                details = await fetcher.fetch_details_batch(client, external_paths)
            except CircuitBreakerOpen as exc:
                result.errors.append(str(exc))
                result.finished_at = datetime.now(UTC)
                return result

        failed_details = len(external_paths) - len(details)
        if failed_details:
            result.errors.append(f"{failed_details} of {len(external_paths)} detail fetches failed")

        for sp in search_postings:
            detail = details.get(sp.external_path)
            if detail is None:
                result.errors.append(f"Detail fetch failed for {sp.external_path}")
                continue

            first_seen: datetime | None = None
            if detail.start_date:
                try:
                    parsed_date = datetime.fromisoformat(detail.start_date)
                    if parsed_date.tzinfo is None:
                        first_seen = parsed_date.replace(tzinfo=UTC)
                    else:
                        first_seen = parsed_date
                except ValueError:
                    logger.warning("Could not parse startDate: %s", detail.start_date)

            raw = RawPosting(
                external_job_id=detail.job_req_id,
                title=detail.title,
                location=detail.location,
                url=detail.external_url
                or _build_detail_url(base_url, tenant, site, sp.external_path),
                full_text=detail.description_html,
            )

            try:
                async with session.begin_nested():
                    created = await persist_posting(
                        session, company.id, raw, first_seen_at=first_seen
                    )
                    if created:
                        result.snapshots_created += 1
            except Exception as exc:
                result.errors.append(f"Persist failed for {detail.job_req_id}: {exc!r}")
                logger.warning("Failed to persist posting %s: %r", detail.job_req_id, exc)

        await session.commit()
        result.finished_at = datetime.now(UTC)

        logger.info(
            "Workday scrape for %s complete: %d found, %d snapshots, %d errors",
            company.slug,
            result.postings_found,
            result.snapshots_created,
            len(result.errors),
        )
        return result
