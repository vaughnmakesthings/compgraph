# FastAPI Pagination & Filtering Patterns

> Reference for CompGraph M4c detail API endpoints. Covers pagination strategies,
> filter parameter design, and SQLAlchemy 2.0 async query patterns for the `postings`,
> `companies`, and related endpoints.

---

## S1 Offset vs Cursor Pagination

### Offset Pagination

Offset pagination uses `LIMIT` + `OFFSET` to skip rows. Simple to implement, supports
"jump to page N," and maps directly to SQL.

```sql
SELECT id, title_raw, first_seen_at
FROM postings
WHERE company_id = $1
ORDER BY first_seen_at DESC, id DESC
LIMIT 50 OFFSET 200;
```

**Drawbacks for CompGraph:**

- **Performance degrades with depth.** At offset 10,000 on a 50K-row `postings` table,
  Postgres must scan and discard 10,000 rows before returning the next 50. Cost is O(offset).
- **Unstable under concurrent writes.** If a new posting is scraped while a user pages
  through results, they see duplicates or miss rows. CompGraph scrapes run continuously,
  making this a real problem.
- **Total count is expensive.** `SELECT count(*)` on a filtered query hits the same
  table scan problem, and the count changes between requests.

**When offset is acceptable:** Small, bounded result sets (< 1,000 rows) where random
page access matters. Example: `GET /api/companies` (4 companies, no pagination needed)
or the aggregation tables which are rebuilt daily and have predictable sizes.

### Cursor (Keyset) Pagination

Cursor pagination uses a WHERE clause to seek past the last-seen row. The "cursor" is
an opaque token encoding the sort key values of the last row returned.

```sql
SELECT id, title_raw, first_seen_at
FROM postings
WHERE company_id = $1
  AND (first_seen_at, id) < ($2::timestamptz, $3::uuid)
ORDER BY first_seen_at DESC, id DESC
LIMIT 50;
```

**Advantages:**

- **Constant-time performance** regardless of depth. Uses an index seek, not a scan.
  At offset 100,000 on 1M rows: offset takes ~1,200ms, keyset maintains ~2-3ms.
- **Stable under writes.** New inserts do not shift existing pages. A user paging
  through postings sees every row exactly once, even while scrapers add new ones.
- **No total count needed.** Determine "has more" by fetching `limit + 1` rows.

**Drawbacks:**

- No "jump to page 7" -- only forward/backward traversal.
- Requires a deterministic, unique sort key. For CompGraph this is `(created_at DESC, id DESC)`
  or `(first_seen_at DESC, id DESC)`.
- Slightly more complex implementation (cursor encoding/decoding, tuple comparison).

### Recommendation for CompGraph

Use **keyset (cursor) pagination** for all list endpoints that return fact-tier data:

| Endpoint | Strategy | Rationale |
|----------|----------|-----------|
| `GET /api/postings` | Keyset cursor | 50K+ rows, continuous inserts from scrapers |
| `GET /api/postings/:id/history` | Keyset cursor | Append-only snapshots, natural time ordering |
| `GET /api/companies` | No pagination | 4 rows, always return all |
| `GET /api/companies/:id/summary` | No pagination | Single object with computed stats |
| Aggregation table endpoints | Offset (optional) | Bounded by date range, rebuilt daily |

**Sort key design:** Use `(created_at DESC, id DESC)` as the default cursor key.
Both columns are indexed and the combination is unique. `created_at` provides natural
chronological ordering; `id` (UUID v4) breaks ties deterministically. CompGraph's UUID
PKs are random, not time-ordered, so `created_at` must be the primary sort column.

**Required index:**

```sql
CREATE INDEX ix_postings_cursor ON postings (first_seen_at DESC, id DESC);
```

---

## S2 Pagination Response Schema

### Standard Envelope

Every paginated endpoint returns the same envelope structure. This makes it trivial
for the frontend to implement a generic pagination hook.

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Pagination metadata included in every paginated response."""

    next_cursor: str | None = Field(
        None,
        description="Opaque cursor for the next page. None means no more results.",
        examples=["eyJjIjoiMjAyNi0wMi0yMFQxMDowMDowMFoiLCJpIjoiYTFiMmMzZDQifQ=="],
    )
    has_more: bool = Field(
        description="Whether more results exist beyond this page."
    )
    page_size: int = Field(
        description="Number of items returned in this page."
    )


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper.

    Usage:
        PaginatedResponse[PostingSummary](data=[...], pagination=PaginationMeta(...))
    """

    data: list[T]
    pagination: PaginationMeta
```

### Why No `total` Field

Including a `total` count in every paginated response is tempting, but it requires
a separate `SELECT count(*)` that:

1. Doubles query cost on large, filtered result sets.
2. Is stale by the time the client reads it (scrapers insert continuously).
3. Is not needed for cursor-based "load more" UIs.

**Policy:** Omit `total` by default. If a specific UI needs it (e.g., "showing 1-50 of
~12,340 results"), add a separate `GET /api/postings/count` endpoint with aggressive
caching (30-60s TTL) rather than computing it on every list request.

### Cursor Encoding

Encode cursor values as a URL-safe base64 JSON object. This keeps the cursor opaque
to clients while being easy to debug server-side.

```python
import base64
import json
from datetime import datetime
from uuid import UUID


def encode_cursor(created_at: datetime, record_id: UUID) -> str:
    """Encode sort key values into an opaque cursor string."""
    payload = {
        "c": created_at.isoformat(),
        "i": str(record_id),
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode an opaque cursor back into sort key values.

    Raises ValueError on malformed cursors.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return (
            datetime.fromisoformat(payload["c"]),
            UUID(payload["i"]),
        )
    except (KeyError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid cursor: {cursor}") from exc
```

**Security note:** Do not HMAC-sign cursors for CompGraph. The API is read-only and
behind auth -- a tampered cursor at worst returns unexpected (but authorized) results.
If cursor tampering becomes a concern (e.g., public API), add HMAC signing later.

---

## S3 Filter Parameter Design

### Query Parameter Patterns

Use FastAPI's `Query()` with Pydantic models (available since FastAPI 0.115.0) to
group related filter parameters. This gives you centralized validation, automatic
OpenAPI documentation, and reusability across endpoints.

```python
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field


class PostingFilters(BaseModel):
    """Query parameters for filtering the postings list.

    All filters are optional. Multiple filters are AND-combined.
    """

    model_config = {"extra": "forbid"}  # Reject unknown query params

    company_id: UUID | None = Field(None, description="Filter by competitor company")
    is_active: bool | None = Field(None, description="Filter by active/closed status")
    role_archetype: str | None = Field(
        None,
        description="Filter by role type (e.g., 'brand_ambassador', 'merchandiser')",
    )
    enrichment_status: Literal["none", "pass1", "pass2"] | None = Field(
        None,
        description="Filter by enrichment completion level",
    )
    first_seen_after: date | None = Field(
        None,
        description="Only postings first seen on or after this date",
    )
    first_seen_before: date | None = Field(
        None,
        description="Only postings first seen on or before this date",
    )
    search: str | None = Field(
        None,
        min_length=2,
        max_length=200,
        description="Full-text search on posting title",
    )
```

### Composing Filters into SQLAlchemy Queries

Build a list of WHERE conditions and apply them all at once. This pattern is clean,
testable, and avoids deeply nested if/else chains.

```python
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import selectinload

from compgraph.db.models import Posting, PostingEnrichment, PostingSnapshot


def apply_posting_filters(
    stmt: Select[tuple[Posting]],
    filters: PostingFilters,
) -> Select[tuple[Posting]]:
    """Apply optional filters to a Posting SELECT statement.

    Each filter is AND-combined. Unset filters (None) are skipped.
    """
    conditions = []

    if filters.company_id is not None:
        conditions.append(Posting.company_id == filters.company_id)

    if filters.is_active is not None:
        conditions.append(Posting.is_active == filters.is_active)

    if filters.first_seen_after is not None:
        conditions.append(Posting.first_seen_at >= filters.first_seen_after)

    if filters.first_seen_before is not None:
        conditions.append(Posting.first_seen_at <= filters.first_seen_before)

    if filters.role_archetype is not None:
        # Requires a join to posting_enrichments
        stmt = stmt.join(Posting.enrichments)
        conditions.append(PostingEnrichment.role_archetype == filters.role_archetype)

    if filters.enrichment_status is not None:
        stmt = stmt.outerjoin(Posting.enrichments)
        if filters.enrichment_status == "none":
            conditions.append(PostingEnrichment.id.is_(None))
        elif filters.enrichment_status == "pass1":
            conditions.append(
                and_(
                    PostingEnrichment.id.is_not(None),
                    PostingEnrichment.enrichment_version.not_like("%pass2%"),
                )
            )
        elif filters.enrichment_status == "pass2":
            conditions.append(
                PostingEnrichment.enrichment_version.contains("pass2")
            )

    if filters.search is not None:
        # Join to latest snapshot for title search
        stmt = stmt.join(Posting.snapshots)
        conditions.append(
            PostingSnapshot.title_raw.ilike(f"%{filters.search}%")
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt
```

**Important:** The `enrichment_status` filter follows CompGraph's convention of checking
`enrichment_version` containing "pass2" rather than checking for `PostingBrandMention`
existence (see CLAUDE.md Common Pitfalls).

### Date Range Pattern

For date range filters, accept ISO 8601 date strings. FastAPI + Pydantic handle
the parsing automatically:

```
GET /api/postings?first_seen_after=2026-01-01&first_seen_before=2026-02-01&company_id=abc123
```

Use `date` (not `datetime`) for range boundaries -- it is more intuitive for users
and avoids timezone confusion. The comparison against `first_seen_at` (a `timestamptz`)
works correctly because Postgres casts `date` to `timestamp` at midnight UTC.

---

## S4 SQLAlchemy 2.0 Async Query Patterns

### Keyset Pagination Query

The core pattern: use tuple comparison in WHERE to seek past the cursor position,
fetch `limit + 1` rows to determine `has_more`, and return only `limit` rows.

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from compgraph.db.models import Posting, PostingEnrichment


async def get_postings_page(
    session: AsyncSession,
    *,
    filters: PostingFilters,
    cursor: tuple[datetime, UUID] | None = None,
    limit: int = 50,
) -> tuple[list[Posting], str | None]:
    """Fetch a page of postings with keyset pagination.

    Returns (postings, next_cursor). next_cursor is None when no more results.
    """
    stmt = (
        select(Posting)
        .options(
            selectinload(Posting.enrichments),
            selectinload(Posting.company),
        )
        .order_by(Posting.first_seen_at.desc(), Posting.id.desc())
    )

    # Apply filters
    stmt = apply_posting_filters(stmt, filters)

    # Apply cursor (keyset WHERE clause)
    if cursor is not None:
        cursor_ts, cursor_id = cursor
        stmt = stmt.where(
            or_(
                Posting.first_seen_at < cursor_ts,
                and_(
                    Posting.first_seen_at == cursor_ts,
                    Posting.id < cursor_id,
                ),
            )
        )

    # Fetch limit + 1 to detect "has more"
    stmt = stmt.limit(limit + 1)

    result = await session.execute(stmt)
    rows = list(result.scalars().unique())

    # Determine next cursor
    if len(rows) > limit:
        rows = rows[:limit]  # Trim the extra row
        last = rows[-1]
        next_cursor = encode_cursor(last.first_seen_at, last.id)
    else:
        next_cursor = None

    return rows, next_cursor
```

**Why `or_()` instead of `tuple_()`:** SQLAlchemy's `tuple_()` comparison works, but
the expanded `OR(a < x, AND(a = x, b < y))` form is easier to read and debug. Both
produce identical query plans. Use whichever is clearer.

The `tuple_()` alternative:

```python
# Equivalent, more compact:
from sqlalchemy import tuple_

stmt = stmt.where(
    tuple_(Posting.first_seen_at, Posting.id)
    < tuple_(cursor_ts, cursor_id)
)
```

Postgres handles tuple comparison natively and uses the composite index efficiently.
However, note that `tuple_()` comparison semantics in SQLAlchemy require the column
order and sort direction to match the index exactly.

### Avoiding N+1 Queries

CompGraph's posting detail requires data from 4 related tables. Use `selectinload()`
for collections (one-to-many) and `joinedload()` for single relations (many-to-one).

```python
from sqlalchemy.orm import joinedload, selectinload


async def get_posting_detail(
    session: AsyncSession,
    posting_id: UUID,
) -> Posting | None:
    """Fetch a single posting with all related data for the detail view."""
    stmt = (
        select(Posting)
        .where(Posting.id == posting_id)
        .options(
            # Many-to-one: single SQL JOIN, no extra query
            joinedload(Posting.company),
            # One-to-many: separate SELECT IN query (avoids row multiplication)
            selectinload(Posting.enrichments),
            selectinload(Posting.snapshots),
            selectinload(Posting.brand_mentions),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

**Why `selectinload` over `joinedload` for collections:** A `joinedload` on a
one-to-many creates a cartesian product in the SQL result. If a posting has 10
snapshots and 5 enrichments, `joinedload` returns 50 rows. `selectinload` issues
2 additional SELECT queries but returns only the rows that exist -- far more
efficient for collections.

**Async constraint:** Do not use `lazyload` (the default) in async sessions.
Lazy loading triggers a synchronous query that will raise
`MissingGreenlet` in an async context. Always specify an explicit loading strategy.

### Efficient Count Queries

When a count is truly needed (e.g., dashboard widgets), use a separate optimized query:

```python
from sqlalchemy import func, select


async def count_postings(
    session: AsyncSession,
    filters: PostingFilters,
) -> int:
    """Count postings matching filters. Use sparingly -- prefer has_more pattern."""
    stmt = select(func.count(Posting.id))

    # Reuse the same filter application function
    # (but on a count query, not a full select)
    count_stmt = select(func.count()).select_from(Posting)
    count_stmt = apply_posting_filters(count_stmt, filters)

    result = await session.execute(count_stmt)
    return result.scalar_one()
```

**Caching counts:** For the dashboard "total postings" widget, cache the count
result for 30-60 seconds rather than running it on every request. FastAPI does not
have built-in response caching, but a simple `lru_cache` with TTL or an in-memory
dict with expiry works fine for a single-process deployment.

### Snapshot Timeline Query

The history endpoint returns snapshots in chronological order. Since
`posting_snapshots` is append-only (per CompGraph convention), the data is naturally
ordered by `snapshot_date`.

```python
async def get_posting_history(
    session: AsyncSession,
    posting_id: UUID,
    *,
    cursor: tuple[datetime, UUID] | None = None,
    limit: int = 50,
) -> tuple[list[PostingSnapshot], str | None]:
    """Fetch snapshot timeline for a posting, newest first."""
    stmt = (
        select(PostingSnapshot)
        .where(PostingSnapshot.posting_id == posting_id)
        .order_by(PostingSnapshot.snapshot_date.desc(), PostingSnapshot.id.desc())
    )

    if cursor is not None:
        cursor_ts, cursor_id = cursor
        stmt = stmt.where(
            or_(
                PostingSnapshot.created_at < cursor_ts,
                and_(
                    PostingSnapshot.created_at == cursor_ts,
                    PostingSnapshot.id < cursor_id,
                ),
            )
        )

    stmt = stmt.limit(limit + 1)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    else:
        next_cursor = None

    return rows, next_cursor
```

---

## S5 FastAPI Dependency Pattern

### Reusable Pagination Dependency

Define pagination parameters as a dependency that can be injected into any endpoint.
Use `Annotated` for clean type hints.

```python
from typing import Annotated

from fastapi import Depends, HTTPException, Query


class PaginationParams:
    """Reusable pagination parameters for cursor-based endpoints."""

    def __init__(
        self,
        limit: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
        cursor: str | None = Query(None, description="Opaque cursor from previous page"),
    ):
        self.limit = limit
        self.cursor = cursor

    @property
    def decoded_cursor(self) -> tuple[datetime, UUID] | None:
        """Decode cursor or return None for first page."""
        if self.cursor is None:
            return None
        try:
            return decode_cursor(self.cursor)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid pagination cursor",
            )


# Type alias for dependency injection
Pagination = Annotated[PaginationParams, Depends()]
```

### Filter Dependencies per Endpoint

Each endpoint type gets its own filter model, injected via `Query()`:

```python
from typing import Annotated

from fastapi import Query

# Type aliases for clean endpoint signatures
PostingFilterDep = Annotated[PostingFilters, Query()]


class CompanyFilters(BaseModel):
    """Filters for the companies list (minimal -- only 4 companies)."""

    model_config = {"extra": "forbid"}

    ats_platform: str | None = Field(None, description="Filter by ATS type")


CompanyFilterDep = Annotated[CompanyFilters, Query()]
```

### Endpoint Wiring

The dependency pattern keeps endpoint functions thin -- they handle HTTP concerns
only, delegating query logic to service functions.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db

router = APIRouter(prefix="/api", tags=["postings"])


@router.get("/postings", response_model=PaginatedResponse[PostingSummary])
async def list_postings(
    pagination: Pagination,
    filters: PostingFilterDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[PostingSummary]:
    """List postings with cursor pagination and optional filters."""
    postings, next_cursor = await get_postings_page(
        db,
        filters=filters,
        cursor=pagination.decoded_cursor,
        limit=pagination.limit,
    )

    return PaginatedResponse(
        data=[PostingSummary.model_validate(p) for p in postings],
        pagination=PaginationMeta(
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            page_size=len(postings),
        ),
    )
```

---

## S6 CompGraph Endpoint Templates

### Template: `GET /api/postings` (Paginated + Filtered)

Full endpoint combining all patterns from S1--S5.

```python
"""Posting list endpoint with cursor pagination and filters.

File: src/compgraph/api/routes/postings.py
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from compgraph.api.deps import get_db
from compgraph.db.models import Posting, PostingEnrichment, PostingSnapshot

router = APIRouter(prefix="/api", tags=["postings"])


# --- Schemas ---


class PostingSummary(BaseModel):
    """Lightweight posting representation for list views."""

    model_config = {"from_attributes": True}

    id: UUID
    company_id: UUID
    company_name: str | None = None
    external_job_id: str | None
    title: str | None = None
    location: str | None = None
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime | None
    role_archetype: str | None = None
    enrichment_status: str | None = None


class PaginationMeta(BaseModel):
    next_cursor: str | None = None
    has_more: bool
    page_size: int


class PaginatedPostings(BaseModel):
    data: list[PostingSummary]
    pagination: PaginationMeta


# --- Filters ---


class PostingFilters(BaseModel):
    model_config = {"extra": "forbid"}

    company_id: UUID | None = None
    is_active: bool | None = None
    role_archetype: str | None = None
    enrichment_status: Literal["none", "pass1", "pass2"] | None = None
    first_seen_after: date | None = None
    first_seen_before: date | None = None
    search: str | None = Field(None, min_length=2, max_length=200)


# --- Pagination ---


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = Query(None),
    ):
        self.limit = limit
        self.raw_cursor = cursor

    @property
    def decoded_cursor(self) -> tuple[datetime, UUID] | None:
        if self.raw_cursor is None:
            return None
        try:
            payload = json.loads(
                base64.urlsafe_b64decode(self.raw_cursor.encode())
            )
            return (
                datetime.fromisoformat(payload["c"]),
                UUID(payload["i"]),
            )
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor") from exc


Pagination = Annotated[PaginationParams, Depends()]
PostingFilterDep = Annotated[PostingFilters, Query()]


# --- Endpoint ---


@router.get("/postings", response_model=PaginatedPostings)
async def list_postings(
    pagination: Pagination,
    filters: PostingFilterDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedPostings:
    stmt = (
        select(Posting)
        .options(
            joinedload(Posting.company),
            selectinload(Posting.enrichments),
        )
        .order_by(Posting.first_seen_at.desc(), Posting.id.desc())
    )

    # Apply filters
    conditions: list = []
    if filters.company_id is not None:
        conditions.append(Posting.company_id == filters.company_id)
    if filters.is_active is not None:
        conditions.append(Posting.is_active == filters.is_active)
    if filters.first_seen_after is not None:
        conditions.append(Posting.first_seen_at >= filters.first_seen_after)
    if filters.first_seen_before is not None:
        conditions.append(Posting.first_seen_at <= filters.first_seen_before)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Apply cursor
    if pagination.decoded_cursor is not None:
        cursor_ts, cursor_id = pagination.decoded_cursor
        stmt = stmt.where(
            or_(
                Posting.first_seen_at < cursor_ts,
                and_(
                    Posting.first_seen_at == cursor_ts,
                    Posting.id < cursor_id,
                ),
            )
        )

    stmt = stmt.limit(pagination.limit + 1)

    result = await db.execute(stmt)
    rows = list(result.scalars().unique())

    has_more = len(rows) > pagination.limit
    if has_more:
        rows = rows[: pagination.limit]

    last = rows[-1] if rows else None
    next_cursor = None
    if has_more and last is not None:
        payload = {
            "c": last.first_seen_at.isoformat(),
            "i": str(last.id),
        }
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).decode()

    # Map to response schema
    summaries = []
    for p in rows:
        enrichment = p.enrichments[0] if p.enrichments else None
        summaries.append(
            PostingSummary(
                id=p.id,
                company_id=p.company_id,
                company_name=p.company.name if p.company else None,
                external_job_id=p.external_job_id,
                title=(
                    enrichment.title_normalized
                    if enrichment and enrichment.title_normalized
                    else None
                ),
                is_active=p.is_active,
                first_seen_at=p.first_seen_at,
                last_seen_at=p.last_seen_at,
                role_archetype=enrichment.role_archetype if enrichment else None,
                enrichment_status=(
                    "pass2"
                    if enrichment and enrichment.enrichment_version
                    and "pass2" in enrichment.enrichment_version
                    else "pass1" if enrichment else "none"
                ),
            )
        )

    return PaginatedPostings(
        data=summaries,
        pagination=PaginationMeta(
            next_cursor=next_cursor,
            has_more=has_more,
            page_size=len(summaries),
        ),
    )
```

### Template: `GET /api/postings/:id` (Single with Joins)

```python
from fastapi import Path


class PostingDetail(BaseModel):
    """Full posting with enrichment data, snapshots, and brand mentions."""

    model_config = {"from_attributes": True}

    id: UUID
    company_id: UUID
    company_name: str | None = None
    external_job_id: str | None
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime | None
    times_reposted: int

    # Latest snapshot
    title_raw: str | None = None
    location_raw: str | None = None
    url: str | None = None

    # Enrichment
    title_normalized: str | None = None
    role_archetype: str | None = None
    role_level: str | None = None
    pay_type: str | None = None
    pay_min: float | None = None
    pay_max: float | None = None
    pay_frequency: str | None = None
    employment_type: str | None = None
    enrichment_version: str | None = None

    # Brand mentions
    brand_mentions: list[BrandMentionSummary] = []

    # Snapshot count (for history pagination)
    snapshot_count: int = 0


class BrandMentionSummary(BaseModel):
    model_config = {"from_attributes": True}

    entity_name: str
    entity_type: str
    confidence_score: float | None


@router.get("/postings/{posting_id}", response_model=PostingDetail)
async def get_posting(
    posting_id: Annotated[UUID, Path(description="Posting UUID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostingDetail:
    stmt = (
        select(Posting)
        .where(Posting.id == posting_id)
        .options(
            joinedload(Posting.company),
            selectinload(Posting.enrichments),
            selectinload(Posting.snapshots),
            selectinload(Posting.brand_mentions),
        )
    )

    result = await db.execute(stmt)
    posting = result.scalar_one_or_none()

    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    enrichment = posting.enrichments[0] if posting.enrichments else None
    latest_snapshot = (
        max(posting.snapshots, key=lambda s: s.snapshot_date)
        if posting.snapshots
        else None
    )

    return PostingDetail(
        id=posting.id,
        company_id=posting.company_id,
        company_name=posting.company.name if posting.company else None,
        external_job_id=posting.external_job_id,
        is_active=posting.is_active,
        first_seen_at=posting.first_seen_at,
        last_seen_at=posting.last_seen_at,
        times_reposted=posting.times_reposted,
        title_raw=latest_snapshot.title_raw if latest_snapshot else None,
        location_raw=latest_snapshot.location_raw if latest_snapshot else None,
        url=latest_snapshot.url if latest_snapshot else None,
        title_normalized=enrichment.title_normalized if enrichment else None,
        role_archetype=enrichment.role_archetype if enrichment else None,
        role_level=enrichment.role_level if enrichment else None,
        pay_type=enrichment.pay_type if enrichment else None,
        pay_min=enrichment.pay_min if enrichment else None,
        pay_max=enrichment.pay_max if enrichment else None,
        pay_frequency=enrichment.pay_frequency if enrichment else None,
        employment_type=enrichment.employment_type if enrichment else None,
        enrichment_version=enrichment.enrichment_version if enrichment else None,
        brand_mentions=[
            BrandMentionSummary.model_validate(bm)
            for bm in posting.brand_mentions
        ],
        snapshot_count=len(posting.snapshots),
    )
```

### Template: `GET /api/companies` (With Aggregated Stats)

```python
from sqlalchemy import func


class CompanySummary(BaseModel):
    """Company with live aggregate stats."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    ats_platform: str
    career_site_url: str
    last_scraped_at: datetime | None

    # Computed stats
    total_postings: int = 0
    active_postings: int = 0
    enriched_postings: int = 0


@router.get("/companies", response_model=list[CompanySummary])
async def list_companies(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CompanySummary]:
    """List all competitor companies with summary statistics.

    No pagination needed -- CompGraph tracks 4 companies.
    """
    # Subquery: total postings per company
    total_sq = (
        select(
            Posting.company_id,
            func.count(Posting.id).label("total_postings"),
        )
        .group_by(Posting.company_id)
        .subquery()
    )

    # Subquery: active postings per company
    active_sq = (
        select(
            Posting.company_id,
            func.count(Posting.id).label("active_postings"),
        )
        .where(Posting.is_active.is_(True))
        .group_by(Posting.company_id)
        .subquery()
    )

    # Subquery: enriched postings per company (has enrichment with pass2)
    enriched_sq = (
        select(
            Posting.company_id,
            func.count(func.distinct(Posting.id)).label("enriched_postings"),
        )
        .join(PostingEnrichment, PostingEnrichment.posting_id == Posting.id)
        .where(PostingEnrichment.enrichment_version.contains("pass2"))
        .group_by(Posting.company_id)
        .subquery()
    )

    from compgraph.db.models import Company

    stmt = (
        select(
            Company,
            func.coalesce(total_sq.c.total_postings, 0).label("total_postings"),
            func.coalesce(active_sq.c.active_postings, 0).label("active_postings"),
            func.coalesce(enriched_sq.c.enriched_postings, 0).label(
                "enriched_postings"
            ),
        )
        .outerjoin(total_sq, Company.id == total_sq.c.company_id)
        .outerjoin(active_sq, Company.id == active_sq.c.company_id)
        .outerjoin(enriched_sq, Company.id == enriched_sq.c.company_id)
        .order_by(Company.name)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        CompanySummary(
            id=row.Company.id,
            name=row.Company.name,
            slug=row.Company.slug,
            ats_platform=row.Company.ats_platform,
            career_site_url=row.Company.career_site_url,
            last_scraped_at=row.Company.last_scraped_at,
            total_postings=row.total_postings,
            active_postings=row.active_postings,
            enriched_postings=row.enriched_postings,
        )
        for row in rows
    ]
```

### Template: `GET /api/companies/:id/summary` (Competitor Dashboard)

```python
class CompanyDashboard(BaseModel):
    """Single competitor dashboard view with all key metrics."""

    id: UUID
    name: str
    slug: str
    ats_platform: str
    last_scraped_at: datetime | None

    # Posting stats
    total_postings: int
    active_postings: int
    closed_postings: int

    # Enrichment stats
    enriched_count: int
    enrichment_rate: float  # 0.0 - 1.0

    # Top brands (from agg_brand_timeline)
    top_brands: list[BrandActivity]

    # Recent velocity (from agg_daily_velocity, last 30 days)
    recent_velocity: list[DailyVelocityPoint]


class BrandActivity(BaseModel):
    brand_name: str
    current_active: int
    total_all_time: int
    is_currently_active: bool


class DailyVelocityPoint(BaseModel):
    date: date
    active_postings: int
    new_postings: int
    closed_postings: int
    net_change: int


@router.get("/companies/{company_id}/summary", response_model=CompanyDashboard)
async def get_company_summary(
    company_id: Annotated[UUID, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyDashboard:
    # Fetch company
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    # Posting stats
    stats_result = await db.execute(
        select(
            func.count(Posting.id).label("total"),
            func.count(Posting.id).filter(Posting.is_active.is_(True)).label("active"),
            func.count(Posting.id).filter(Posting.is_active.is_(False)).label("closed"),
        ).where(Posting.company_id == company_id)
    )
    stats = stats_result.one()

    # Enrichment stats
    enriched_result = await db.execute(
        select(func.count(func.distinct(PostingEnrichment.posting_id)))
        .join(Posting, Posting.id == PostingEnrichment.posting_id)
        .where(
            Posting.company_id == company_id,
            PostingEnrichment.enrichment_version.contains("pass2"),
        )
    )
    enriched_count = enriched_result.scalar_one()

    # Top brands from aggregation table
    from compgraph.db.models import AggBrandTimeline, Brand

    brand_result = await db.execute(
        select(AggBrandTimeline, Brand.name.label("brand_name"))
        .join(Brand, AggBrandTimeline.brand_id == Brand.id)
        .where(AggBrandTimeline.company_id == company_id)
        .order_by(AggBrandTimeline.current_active_postings.desc())
        .limit(10)
    )

    # Recent velocity (last 30 days)
    from compgraph.db.models import AggDailyVelocity

    velocity_result = await db.execute(
        select(AggDailyVelocity)
        .where(
            AggDailyVelocity.company_id == company_id,
            AggDailyVelocity.date >= func.current_date() - 30,
        )
        .order_by(AggDailyVelocity.date.desc())
    )

    return CompanyDashboard(
        id=company.id,
        name=company.name,
        slug=company.slug,
        ats_platform=company.ats_platform,
        last_scraped_at=company.last_scraped_at,
        total_postings=stats.total,
        active_postings=stats.active,
        closed_postings=stats.closed,
        enriched_count=enriched_count,
        enrichment_rate=enriched_count / stats.total if stats.total > 0 else 0.0,
        top_brands=[
            BrandActivity(
                brand_name=row.brand_name,
                current_active=row.AggBrandTimeline.current_active_postings,
                total_all_time=row.AggBrandTimeline.total_postings_all_time,
                is_currently_active=row.AggBrandTimeline.is_currently_active,
            )
            for row in brand_result.all()
        ],
        recent_velocity=[
            DailyVelocityPoint(
                date=v.date,
                active_postings=v.active_postings,
                new_postings=v.new_postings,
                closed_postings=v.closed_postings,
                net_change=v.net_change,
            )
            for v in velocity_result.scalars().all()
        ],
    )
```

---

## Sources

- [FastAPI Query Parameter Models](https://fastapi.tiangolo.com/tutorial/query-param-models/)
- [FastAPI Dependency Classes](https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/)
- [SQLAlchemy 2.0 Async ORM Extensions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy Relationship Loading: selectinload](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
- [Pagination That Scales: Offset vs Cursor vs Keyset](https://www.caduh.com/blog/pagination-that-scales-offset-cursor-keyset)
- [How to Implement Keyset Pagination for Large Datasets](https://oneuptime.com/blog/post/2026-02-02-keyset-pagination/view)
- [fastapi-pagination library (cursor support)](https://uriyyo-fastapi-pagination.netlify.app/)
- [FastSQLA: Async SQLAlchemy 2.0+ extension for FastAPI](https://github.com/hadrien/FastSQLA)
- [fastapi-filter: Declarative filtering for FastAPI](https://fastapi-filter.netlify.app/)
