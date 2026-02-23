# logo.dev Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add logo.dev CDN logo support to CompGraph — brand and company logos surfaced via two new API catalog endpoints, with domain resolution wired into enrichment and a backfill script for existing brands.

**Architecture:** Add `domain` column to `brands` and `companies` tables. A pure helper function generates logo CDN URLs at response time (never stored). Two new catalog endpoints (`/api/brands`, `/api/companies`) serve as the logo source of truth; aggregation routes stay unchanged. Enrichment Pass 2 resolves brand domain via Logo.dev Brand Search API on new brand creation.

**Tech Stack:** SQLAlchemy 2.0 async, FastAPI, Pydantic v2, httpx (already installed), logo.dev REST API, Alembic manual migration

**Design doc:** `docs/plans/2026-02-23-logo-dev-integration-design.md`
**API research:** `docs/references/logo-dev-api.md`

---

## Task 1: Alembic Migration — Add `domain` to `brands` and `companies`

**Files:**
- Create: `alembic/versions/d4e5f6a7b8c9_add_domain_to_brands_and_companies.py`
- Modify: `src/compgraph/db/models.py:49-57` (Brand) and `:33-46` (Company)

### Step 1: Write the migration file

```python
"""add domain to brands and companies

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-02-23 00:00:00.000000

Adds nullable domain column to brands and companies tables.
Seeds known company domains for the 4 scraped agencies.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("brands", sa.Column("domain", sa.String(253), nullable=True))
    op.create_index("ix_brands_domain", "brands", ["domain"])

    op.add_column("companies", sa.Column("domain", sa.String(253), nullable=True))

    # Seed known public domains for the 4 scraped agencies
    op.execute("""
        UPDATE companies SET domain = 't-roc.com'
        WHERE slug = 't-roc'
    """)
    op.execute("""
        UPDATE companies SET domain = '2020companies.com'
        WHERE slug = '2020-companies'
    """)
    op.execute("""
        UPDATE companies SET domain = 'bdssolutions.com'
        WHERE slug = 'bds'
    """)
    op.execute("""
        UPDATE companies SET domain = 'marketsource.com'
        WHERE slug = 'marketsource'
    """)


def downgrade() -> None:
    op.drop_index("ix_brands_domain", table_name="brands")
    op.drop_column("brands", "domain")
    op.drop_column("companies", "domain")
```

### Step 2: Update SQLAlchemy models

In `src/compgraph/db/models.py`, add `domain` to both `Brand` and `Company`:

```python
# Brand class (line ~49)
class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(253), nullable=True)  # ADD THIS
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# Company class (line ~33)
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ats_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    career_site_url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(253), nullable=True)  # ADD THIS
    scraper_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postings: Mapped[list["Posting"]] = relationship(back_populates="company")
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="company")
```

### Step 3: Verify migration file parses cleanly

```bash
uv run python -c "import alembic.versions.d4e5f6a7b8c9_add_domain_to_brands_and_companies"
```

Expected: no import errors.

### Step 4: Run lint and typecheck

```bash
uv run ruff check src/compgraph/db/models.py && uv run mypy src/compgraph/db/models.py
```

Expected: no errors.

### Step 5: Commit

```bash
git add alembic/versions/d4e5f6a7b8c9_add_domain_to_brands_and_companies.py src/compgraph/db/models.py
git commit -m "feat: add domain column to brands and companies tables"
```

> **Note:** Do not run `alembic upgrade head` locally — DNS fails. The CD pipeline runs it automatically on merge, or run manually on the droplet: `ssh compgraph-do 'cd /opt/compgraph && op run --env-file=.env -- uv run alembic upgrade head'`

---

## Task 2: Config Keys

**Files:**
- Modify: `src/compgraph/config.py`
- Modify: `.env.example` (if it exists) or create it with placeholders

### Step 1: Add keys to config

In `src/compgraph/config.py`, add after `ANTHROPIC_API_KEY`:

```python
# Logo.dev
LOGO_DEV_PUBLISHABLE_KEY: str = ""   # pk_... — safe for frontend exposure
LOGO_DEV_SECRET_KEY: str = ""        # sk_... — server-side only (Brand Search API)
```

### Step 2: Check for .env.example and add placeholders

```bash
ls .env.example 2>/dev/null && echo "exists" || echo "missing"
```

If it exists, add:
```
LOGO_DEV_PUBLISHABLE_KEY=pk_your_key_here
LOGO_DEV_SECRET_KEY=sk_your_key_here
```

If missing, do NOT create it — just move on.

### Step 3: Add keys to 1Password DEV vault

Store actual keys in 1Password DEV vault as:
- `LOGO_DEV_PUBLISHABLE_KEY` = `pk_cH_8zaDFQayMFUWdVihtEA`
- `LOGO_DEV_SECRET_KEY` = `sk_CjE5FqxHQpeyG6Euy9PuGw`

Then add to local `.env` file (not committed):
```
LOGO_DEV_PUBLISHABLE_KEY=pk_cH_8zaDFQayMFUWdVihtEA
LOGO_DEV_SECRET_KEY=sk_CjE5FqxHQpeyG6Euy9PuGw
```

### Step 4: Verify settings loads cleanly

```bash
uv run python -c "from compgraph.config import settings; print(settings.LOGO_DEV_PUBLISHABLE_KEY[:5])"
```

Expected: prints `pk_cH` (or empty string if .env not set — that's fine for CI).

### Step 5: Lint + commit

```bash
uv run ruff check src/compgraph/config.py
git add src/compgraph/config.py
git commit -m "feat: add LOGO_DEV_PUBLISHABLE_KEY and LOGO_DEV_SECRET_KEY to config"
```

---

## Task 3: Logo URL Helper Module

**Files:**
- Create: `src/compgraph/logos.py`
- Create: `tests/test_logos.py`

### Step 1: Write the failing tests

```python
# tests/test_logos.py
from unittest.mock import patch

from compgraph.logos import logo_url


def test_logo_url_returns_cdn_url():
    with patch("compgraph.logos.settings") as mock_settings:
        mock_settings.LOGO_DEV_PUBLISHABLE_KEY = "pk_test123"
        result = logo_url("walmart.com", size=64, fmt="webp")
    assert result == "https://img.logo.dev/walmart.com?token=pk_test123&size=64&format=webp"


def test_logo_url_none_domain_returns_none():
    assert logo_url(None) is None


def test_logo_url_empty_domain_returns_none():
    assert logo_url("") is None


def test_logo_url_custom_size_and_format():
    with patch("compgraph.logos.settings") as mock_settings:
        mock_settings.LOGO_DEV_PUBLISHABLE_KEY = "pk_test123"
        result = logo_url("target.com", size=128, fmt="png")
    assert result == "https://img.logo.dev/target.com?token=pk_test123&size=128&format=png"
```

### Step 2: Run tests to confirm they fail

```bash
uv run pytest tests/test_logos.py -v --no-cov
```

Expected: `ModuleNotFoundError: No module named 'compgraph.logos'`

### Step 3: Write the implementation

```python
# src/compgraph/logos.py
"""Logo.dev CDN URL helper.

Generates logo CDN URLs from company/brand domains. No HTTP calls —
URLs are deterministic from the domain and are resolved by logo.dev's CDN.
"""
from __future__ import annotations

from compgraph.config import settings


def logo_url(domain: str | None, size: int = 64, fmt: str = "webp") -> str | None:
    """Return a logo.dev CDN URL for the given domain, or None if domain is unknown.

    Args:
        domain: Public company domain, e.g. "walmart.com". None/empty → None.
        size: Image size in pixels (max 2048). Default 64.
        fmt: Image format — "webp", "png", or "jpg". Default "webp".

    Returns:
        CDN URL string, or None if domain is falsy.
    """
    if not domain:
        return None
    pk = settings.LOGO_DEV_PUBLISHABLE_KEY
    return f"https://img.logo.dev/{domain}?token={pk}&size={size}&format={fmt}"
```

### Step 4: Run tests to confirm they pass

```bash
uv run pytest tests/test_logos.py -v --no-cov
```

Expected: 4 passed.

### Step 5: Full lint + typecheck + commit

```bash
uv run ruff check src/compgraph/logos.py tests/test_logos.py
uv run mypy src/compgraph/logos.py
git add src/compgraph/logos.py tests/test_logos.py
git commit -m "feat: add logo_url helper for logo.dev CDN URL generation"
```

---

## Task 4: `/api/brands` Endpoint

**Files:**
- Create: `src/compgraph/api/routes/brands.py`
- Modify: `src/compgraph/main.py`
- Create: `tests/test_brands_router.py`

### Step 1: Write the failing tests

```python
# tests/test_brands_router.py
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from compgraph.main import app
from compgraph.api.deps import get_db


def make_brand(name: str, slug: str, domain: str | None = None):
    brand = MagicMock()
    brand.id = uuid.uuid4()
    brand.name = name
    brand.slug = slug
    brand.category = "retail"
    brand.domain = domain
    return brand


@pytest.fixture
def client_with_brands(settings_override):
    walmart = make_brand("Walmart", "walmart", "walmart.com")
    unknown = make_brand("Niche Brand", "niche-brand", None)

    async def mock_db():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [walmart, unknown]
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_db] = mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_brands_returns_list(client_with_brands):
    response = client_with_brands.get("/api/brands")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_brands_includes_logo_url_when_domain_known(client_with_brands):
    with patch("compgraph.api.routes.brands.logo_url") as mock_logo:
        mock_logo.side_effect = lambda d, **kw: f"https://img.logo.dev/{d}" if d else None
        response = client_with_brands.get("/api/brands")
    data = response.json()
    walmart = next(b for b in data if b["slug"] == "walmart")
    assert walmart["logo_url"] == "https://img.logo.dev/walmart.com"
    assert walmart["domain"] == "walmart.com"


def test_brands_logo_url_null_when_no_domain(client_with_brands):
    with patch("compgraph.api.routes.brands.logo_url") as mock_logo:
        mock_logo.side_effect = lambda d, **kw: f"https://img.logo.dev/{d}" if d else None
        response = client_with_brands.get("/api/brands")
    data = response.json()
    niche = next(b for b in data if b["slug"] == "niche-brand")
    assert niche["logo_url"] is None
    assert niche["domain"] is None
```

### Step 2: Run tests to confirm they fail

```bash
uv run pytest tests/test_brands_router.py -v --no-cov
```

Expected: import error or 404 for `/api/brands`.

### Step 3: Write the route

```python
# src/compgraph/api/routes/brands.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import Brand
from compgraph.logos import logo_url

router = APIRouter(prefix="/api/brands", tags=["brands"])


class BrandResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    category: str | None
    domain: str | None
    logo_url: str | None


@router.get("", response_model=list[BrandResponse])
async def list_brands(db: AsyncSession = Depends(get_db)) -> list[BrandResponse]:  # noqa: B008
    result = await db.execute(select(Brand).order_by(Brand.name))
    brands = result.scalars().all()
    return [
        BrandResponse(
            id=b.id,
            name=b.name,
            slug=b.slug,
            category=b.category,
            domain=b.domain,
            logo_url=logo_url(b.domain),
        )
        for b in brands
    ]
```

### Step 4: Register router in main.py

In `src/compgraph/main.py`, add:

```python
from compgraph.api.routes.brands import router as brands_router
```

And after the existing `app.include_router` calls:

```python
app.include_router(brands_router)
```

### Step 5: Run tests to confirm they pass

```bash
uv run pytest tests/test_brands_router.py -v --no-cov
```

Expected: 3 passed.

### Step 6: Lint + typecheck + commit

```bash
uv run ruff check src/compgraph/api/routes/brands.py tests/test_brands_router.py
uv run mypy src/compgraph/api/routes/brands.py
git add src/compgraph/api/routes/brands.py tests/test_brands_router.py src/compgraph/main.py
git commit -m "feat: add /api/brands endpoint with logo_url"
```

---

## Task 5: `/api/companies` Endpoint

**Files:**
- Create: `src/compgraph/api/routes/companies.py`
- Modify: `src/compgraph/main.py`
- Create: `tests/test_companies_router.py`

### Step 1: Write the failing tests

```python
# tests/test_companies_router.py
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi.testclient import TestClient

from compgraph.main import app
from compgraph.api.deps import get_db


def make_company(name: str, slug: str, domain: str | None):
    co = MagicMock()
    co.id = uuid.uuid4()
    co.name = name
    co.slug = slug
    co.domain = domain
    return co


@pytest.fixture
def client_with_companies(settings_override):
    troc = make_company("T-ROC", "t-roc", "t-roc.com")

    async def mock_db():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [troc]
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_db] = mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_companies_returns_list(client_with_companies):
    response = client_with_companies.get("/api/companies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "T-ROC"


def test_companies_includes_logo_url(client_with_companies):
    response = client_with_companies.get("/api/companies")
    data = response.json()
    assert data[0]["logo_url"] is not None
    assert "t-roc.com" in data[0]["logo_url"]
    assert data[0]["domain"] == "t-roc.com"
```

### Step 2: Run tests to confirm they fail

```bash
uv run pytest tests/test_companies_router.py -v --no-cov
```

Expected: import error or 404 for `/api/companies`.

### Step 3: Write the route

```python
# src/compgraph/api/routes/companies.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import Company
from compgraph.logos import logo_url

router = APIRouter(prefix="/api/companies", tags=["companies"])


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    domain: str | None
    logo_url: str | None


@router.get("", response_model=list[CompanyResponse])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyResponse]:  # noqa: B008
    result = await db.execute(select(Company).order_by(Company.name))
    companies = result.scalars().all()
    return [
        CompanyResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            domain=c.domain,
            logo_url=logo_url(c.domain),
        )
        for c in companies
    ]
```

### Step 4: Register router in main.py

```python
from compgraph.api.routes.companies import router as companies_router
# ...
app.include_router(companies_router)
```

### Step 5: Run tests to confirm they pass

```bash
uv run pytest tests/test_companies_router.py -v --no-cov
```

Expected: 2 passed.

### Step 6: Full test suite check

```bash
uv run pytest -x -q --no-cov -m "not integration"
```

Expected: all passing.

### Step 7: Lint + typecheck + commit

```bash
uv run ruff check src/compgraph/api/routes/companies.py tests/test_companies_router.py
uv run mypy src/compgraph/api/routes/companies.py
git add src/compgraph/api/routes/companies.py tests/test_companies_router.py src/compgraph/main.py
git commit -m "feat: add /api/companies endpoint with logo_url"
```

---

## Task 6: Backfill Script

**Files:**
- Create: `scripts/backfill_brand_domains.py`

> No unit tests for this script — it's a one-shot operational tool. Dry-run mode provides safety.

### Step 1: Write the script

```python
#!/usr/bin/env python
"""Backfill brand domains using logo.dev Brand Search API.

Usage:
    op run --env-file=.env -- uv run python scripts/backfill_brand_domains.py
    op run --env-file=.env -- uv run python scripts/backfill_brand_domains.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging

import httpx
from sqlalchemy import select, update

from compgraph.config import settings
from compgraph.db.models import Brand
from compgraph.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LOGO_DEV_SEARCH_URL = "https://api.logo.dev/search"


async def resolve_domain(client: httpx.AsyncClient, brand_name: str) -> str | None:
    """Call logo.dev Brand Search API and return first result domain, or None."""
    try:
        r = await client.get(
            LOGO_DEV_SEARCH_URL,
            params={"q": brand_name},
            headers={"Authorization": f"Bearer {settings.LOGO_DEV_SECRET_KEY}"},
            timeout=5.0,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            return results[0].get("domain")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Brand Search failed for %r: %s", brand_name, exc)
    return None


async def main(dry_run: bool) -> None:
    resolved = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Brand).where(Brand.domain.is_(None)).order_by(Brand.name)
        )
        brands = result.scalars().all()
        logger.info("Found %d brands with no domain", len(brands))

        async with httpx.AsyncClient() as client:
            for brand in brands:
                domain = await resolve_domain(client, brand.name)
                if domain:
                    logger.info("  %s → %s", brand.name, domain)
                    if not dry_run:
                        await session.execute(
                            update(Brand).where(Brand.id == brand.id).values(domain=domain)
                        )
                    resolved += 1
                else:
                    logger.info("  %s → (no result)", brand.name)
                    skipped += 1

        if not dry_run:
            await session.commit()

    mode = "[DRY RUN] " if dry_run else ""
    logger.info(
        "%sDone — resolved: %d, skipped: %d, failed: %d",
        mode, resolved, skipped, failed,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
```

### Step 2: Verify it imports cleanly

```bash
uv run python -c "import scripts.backfill_brand_domains"
```

If that fails due to path issues, run directly:
```bash
uv run python scripts/backfill_brand_domains.py --help
```

Expected: shows help text with `--dry-run` flag.

### Step 3: Check for AsyncSessionLocal in session module

```bash
grep -n "AsyncSessionLocal" src/compgraph/db/session.py
```

If `AsyncSessionLocal` doesn't exist, check what the session factory is named and update the import accordingly. Common alternatives: `async_session_maker`, `get_async_session`.

### Step 4: Commit

```bash
git add scripts/backfill_brand_domains.py
git commit -m "feat: add backfill_brand_domains script for logo.dev Brand Search"
```

---

## Task 7: Enrichment Pass 2 — Brand Domain Resolution

**Files:**
- Modify: `src/compgraph/enrichment/resolver.py`
- Modify: `tests/test_resolver.py` (if it exists) or create it

### Step 1: Find the existing resolver test file

```bash
ls tests/test_resolver* 2>/dev/null || echo "no test file"
```

### Step 2: Write a failing test for domain resolution

Add to the resolver test file (or create `tests/test_resolver_domain.py`):

```python
# tests/test_resolver_domain.py
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from compgraph.enrichment.resolver import _resolve_brand_domain


@pytest.mark.asyncio
async def test_resolve_brand_domain_sets_domain_on_success():
    brand_id = uuid.uuid4()
    session = AsyncMock()

    with patch("compgraph.enrichment.resolver.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.json.return_value = [{"domain": "walmart.com"}]
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        await _resolve_brand_domain(session, brand_id, "Walmart")

    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_brand_domain_skips_on_empty_results():
    brand_id = uuid.uuid4()
    session = AsyncMock()

    with patch("compgraph.enrichment.resolver.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        await _resolve_brand_domain(session, brand_id, "Niche Brand")

    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_brand_domain_swallows_http_errors():
    """API failures must not crash enrichment."""
    import httpx

    brand_id = uuid.uuid4()
    session = AsyncMock()

    with patch("compgraph.enrichment.resolver.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        # Must not raise
        await _resolve_brand_domain(session, brand_id, "SomeBrand")

    session.execute.assert_not_called()
```

### Step 3: Run tests to confirm they fail

```bash
uv run pytest tests/test_resolver_domain.py -v --no-cov
```

Expected: `ImportError` — `_resolve_brand_domain` doesn't exist yet.

### Step 4: Implement `_resolve_brand_domain` in resolver.py

Add at the top of `src/compgraph/enrichment/resolver.py` after existing imports:

```python
import httpx
from sqlalchemy import update
```

Add the new function before `resolve_entity`:

```python
async def _resolve_brand_domain(
    session: AsyncSession, brand_id: uuid.UUID, brand_name: str
) -> None:
    """Look up brand domain via logo.dev Brand Search API and persist it.

    Failure is non-fatal — enrichment must not be interrupted by logo resolution.
    """
    from compgraph.config import settings

    if not settings.LOGO_DEV_SECRET_KEY:
        return

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.logo.dev/search",
                params={"q": brand_name},
                headers={"Authorization": f"Bearer {settings.LOGO_DEV_SECRET_KEY}"},
                timeout=5.0,
            )
            r.raise_for_status()
            results = r.json()
            if not results:
                return
            domain = results[0].get("domain")
            if domain:
                await session.execute(
                    update(Brand).where(Brand.id == brand_id).values(domain=domain)
                )
    except Exception:
        logger.warning("Failed to resolve logo.dev domain for brand %r", brand_name, exc_info=True)
```

### Step 5: Call `_resolve_brand_domain` when a new Brand is created

In `resolve_entity`, after the `_create_entity` calls for brands, add the domain resolution call. Three locations (lines ~180, ~206, and the ambiguous branch):

```python
# client_brand branch (~line 176)
if entity_type == "client_brand":
    brand_id, _score = await _find_entity(session, entity_name, Brand)
    if brand_id:
        return brand_id, None, False
    new_id = await _create_entity(session, entity_name, Brand)
    await _resolve_brand_domain(session, new_id, entity_name)  # NEW
    return new_id, None, True

# ambiguous → default to brand branch (~line 205)
new_id = await _create_entity(session, entity_name, Brand)
await _resolve_brand_domain(session, new_id, entity_name)  # NEW
return new_id, None, True
```

### Step 6: Run tests to confirm they pass

```bash
uv run pytest tests/test_resolver_domain.py -v --no-cov
```

Expected: 3 passed.

### Step 7: Full test suite check

```bash
uv run pytest -x -q --no-cov -m "not integration"
```

Expected: all passing.

### Step 8: Lint + typecheck + commit

```bash
uv run ruff check src/compgraph/enrichment/resolver.py tests/test_resolver_domain.py
uv run mypy src/compgraph/enrichment/resolver.py
git add src/compgraph/enrichment/resolver.py tests/test_resolver_domain.py
git commit -m "feat: resolve brand domain via logo.dev on new brand creation in Pass 2"
```

---

## Task 8: Frontend — Env Var + Attribution Footer

**Files:**
- Modify: `web/src/components/layout/shell.tsx`
- Create/modify: `web/.env.example` or `web/.env.local`

> This task is frontend-only. Run frontend checks with `npm run lint && npm run typecheck` from `web/`.

### Step 1: Add env var to Next.js

In `web/` directory, check for `.env.local` or `.env.example`:

```bash
ls web/.env* 2>/dev/null
```

Add to whichever env file exists (`.env.local` for local dev, `.env.example` for docs):

```
NEXT_PUBLIC_LOGO_DEV_KEY=pk_cH_8zaDFQayMFUWdVihtEA
```

If neither exists, create `web/.env.example`:
```
NEXT_PUBLIC_LOGO_DEV_KEY=pk_your_publishable_key_here
```

And `web/.env.local` (not committed) with the real key.

### Step 2: Read the Shell component

```bash
cat web/src/components/layout/shell.tsx
```

Find the footer area or the bottom of the layout wrapper.

### Step 3: Add attribution to Shell footer

In `web/src/components/layout/shell.tsx`, locate the closing of the main content area and add a footer with attribution. The exact placement depends on the component structure — put it as the last element before the closing tag of the right-side column:

```tsx
{/* Logo.dev attribution — required for Free tier */}
<footer className="px-6 py-3 border-t border-border">
  <p className="text-xs text-muted-foreground">
    Logos by{" "}
    <a
      href="https://logo.dev"
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2 hover:text-foreground transition-colors"
    >
      Logo.dev
    </a>
  </p>
</footer>
```

### Step 4: Lint and typecheck

```bash
cd web && npm run lint && npm run typecheck
```

Expected: no errors.

### Step 5: Commit

```bash
git add web/src/components/layout/shell.tsx web/.env.example
git commit -m "feat: add logo.dev attribution footer and NEXT_PUBLIC_LOGO_DEV_KEY env var"
```

---

## Task 9: Final Validation

### Step 1: Full backend test suite

```bash
uv run pytest -x -q --no-cov -m "not integration"
```

Expected: all passing.

### Step 2: Full lint + typecheck

```bash
uv run ruff check src/ tests/ && uv run mypy src/compgraph/
```

Expected: no errors.

### Step 3: Full frontend checks

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Expected: all passing.

### Step 4: Push and open PR

```bash
git push origin HEAD
gh pr create --title "feat: logo.dev integration — brand/company logos via CDN" \
  --body "$(cat <<'EOF'
## Summary

- Adds `domain` column to `brands` and `companies` tables (Alembic migration `d4e5f6a7b8c9`)
- Seeds known domains for 4 scraped agencies (T-ROC, 2020 Companies, BDS, MarketSource)
- Adds `LOGO_DEV_PUBLISHABLE_KEY` + `LOGO_DEV_SECRET_KEY` to config
- New `src/compgraph/logos.py` helper — pure URL generation, no HTTP calls
- New `/api/brands` endpoint — brand catalog with `logo_url` computed field
- New `/api/companies` endpoint — agency catalog with `logo_url` computed field
- Enrichment Pass 2 resolves brand domain via Brand Search API on new brand creation
- Backfill script for existing brands: `scripts/backfill_brand_domains.py`
- Frontend Shell footer attribution ("Logos by Logo.dev") — Free tier compliance

## Test plan

- [ ] `uv run pytest -x -q --no-cov -m "not integration"` — all pass
- [ ] `GET /api/brands` returns list with `logo_url` populated for brands with domains
- [ ] `GET /api/companies` returns 4 companies with `logo_url` populated
- [ ] Run backfill script in dry-run mode against dev DB
- [ ] After merge, run `alembic upgrade head` on droplet

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Running the Backfill (Post-Merge)

After the PR merges and CD deploys:

```bash
# Dry run first — see what would be resolved
ssh compgraph-do 'cd /opt/compgraph && op run --env-file=.env -- uv run python scripts/backfill_brand_domains.py --dry-run'

# If output looks right, run for real
ssh compgraph-do 'cd /opt/compgraph && op run --env-file=.env -- uv run python scripts/backfill_brand_domains.py'
```
