# Data Quality & Aggregation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean data quality blockers and build 7 aggregation rebuild jobs (4 existing + 3 new) with truncate+insert pattern.

**Architecture:** Phase 1 fixes 3 critical data quality issues (brand dedup, title normalization, location normalization). Phase 2 adds the `location_mappings` table and 3 new aggregation table schemas. Phase 3 implements all 7 aggregation rebuild jobs in `src/compgraph/aggregation/`. Phase 4 wires aggregation into the scheduler pipeline and adds read-only API endpoints.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, Anthropic Haiku 4.5 (location seeding), FastAPI, pytest

**Design doc:** `docs/plans/2026-02-22-data-quality-aggregation-design.md`

---

## Tool Directives

### CodeSight-First Exploration

All agents MUST use CodeSight as the **default** exploration tool. Read/Grep/Glob are fallbacks, not defaults.

**Mandatory session start for every agent:**
```
index_codebase(project_path="/Users/vmud/Documents/dev/projects/compgraph", project_name="compgraph")
```

**Tool priority order:**

| Priority | Tool | When to Use |
|----------|------|-------------|
| 1st | `search_code(query, project="compgraph")` | Default for all exploration — find patterns, locate code, understand architecture |
| 2nd | `get_chunk_code(chunk_ids, include_context=True)` | Expand search results to see full implementation with surrounding context |
| 3rd | `Read` | Only for exact files CodeSight already pointed to, or when editing requires exact line numbers |
| 4th | `Grep/Glob` | Only for non-indexed files (`.env`, generated migrations, lock files) or when CodeSight is unavailable |

**Before writing any new code, agents MUST:**
1. `search_code` for existing patterns in the target area
2. `get_chunk_code` on the top results to understand conventions
3. Only then `Read` the specific file at the specific lines they need to edit

**Examples:**
- Before writing an aggregation job → `search_code("truncate insert aggregation base")`
- Before modifying scheduler → `search_code("pipeline_job scheduler phase enrich")`
- Before adding a model → `search_code("class Agg UUID mapped_column Base")`
- Anti-pattern scan → `search_code("session.execute UPDATE posting_snapshots")` to catch append-only violations

### Other MCP Tools

| Tool | Agent | Purpose |
|------|-------|---------|
| `claude-mem: search, get_observations` | All agents | Recall prior design decisions before implementing |
| `claude-mem: save_memory` | Implementation agents | Persist key decisions after each phase |
| `context7: resolve-library-id, get-library-docs` | Implementation agents | SQLAlchemy 2.0 async, FastAPI, Alembic API docs |
| `sequential-thinking` | database-optimizer | Reason through query plan optimization |

### Agent Team

| Agent | Role | Tasks |
|-------|------|-------|
| `python-backend-developer` | Primary builder | All 19 tasks |
| `database-optimizer` | SQL tuning | Review aggregation queries (Tasks 10-16) |
| `code-reviewer` | Quality gate | After Phase 1, 2, 3 |
| `pytest-validator` | Test audit | After Phase 3 |
| `spec-reviewer` | Scope gate | After Phase 4 |

### Parallelization

**Phase 1** — Tasks 1-4 independent, dispatch 2 agents in worktrees.
**Phase 3** — Tasks 10-16 independent after Task 9, dispatch 3 agents in worktrees.

### Review Gates

- After Phase 1: `code-reviewer` (migration safety, append-only compliance)
- After Phase 2: `code-reviewer` (schema correctness, market normalization)
- After Phase 3: `database-optimizer` → `code-reviewer` → `pytest-validator`
- After Phase 4: `spec-reviewer` (M4 goal achievement)

---

## Phase 1: Data Cleanup

### Task 1: Brand Deduplication Migration

**Files:**
- Create: `alembic/versions/xxxx_merge_duplicate_brands.py`
- Test: manual verification via `op run --env-file=.env -- uv run alembic upgrade head`

**Step 1: Generate the migration**

```bash
op run --env-file=.env -- uv run alembic revision -m "merge duplicate brands"
```

**Step 2: Write the migration**

The migration merges 3 duplicate brand pairs. Uses raw SQL for data migration (not ORM):

```python
"""merge duplicate brands

Revision ID: <auto>
Revises: <auto>
"""
from alembic import op

# 3 duplicate pairs: (duplicate_name, canonical_name)
MERGES = [
    ("Reliant", "Reliant Energy"),
    ("LG", "LG Electronics"),
    ("Virgin Mobile", "Virgin Plus"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for dup_name, canonical_name in MERGES:
        # Get IDs
        canonical = conn.execute(
            sa.text("SELECT id FROM brands WHERE name = :n"), {"n": canonical_name}
        ).fetchone()
        duplicate = conn.execute(
            sa.text("SELECT id FROM brands WHERE name = :n"), {"n": dup_name}
        ).fetchone()
        if not canonical or not duplicate:
            continue  # Skip if either doesn't exist

        # Reparent brand mentions
        conn.execute(
            sa.text(
                "UPDATE posting_brand_mentions SET resolved_brand_id = :canonical "
                "WHERE resolved_brand_id = :dup"
            ),
            {"canonical": canonical[0], "dup": duplicate[0]},
        )
        # Reparent enrichments
        conn.execute(
            sa.text(
                "UPDATE posting_enrichments SET brand_id = :canonical "
                "WHERE brand_id = :dup"
            ),
            {"canonical": canonical[0], "dup": duplicate[0]},
        )
        # Delete duplicate
        conn.execute(
            sa.text("DELETE FROM brands WHERE id = :dup"),
            {"dup": duplicate[0]},
        )


def downgrade() -> None:
    pass  # Data migration — not reversible
```

**Step 3: Run migration**

```bash
op run --env-file=.env -- uv run alembic upgrade head
```

**Step 4: Verify**

```bash
op run --env-file=.env -- uv run python -c "
import asyncio
from sqlalchemy import text
from compgraph.db.session import async_session_factory
async def check():
    async with async_session_factory() as s:
        r = await s.execute(text('SELECT name FROM brands ORDER BY name'))
        for row in r: print(row[0])
asyncio.run(check())
"
```
Expected: No "Reliant", "LG", or "Virgin Mobile" — only canonical names.

**Step 5: Commit**

```bash
git add alembic/versions/*merge_duplicate_brands*
git commit -m "fix: merge 3 duplicate brand pairs (Reliant/LG/Virgin)"
```

---

### Task 2: Title Normalization Function

**Files:**
- Create: `src/compgraph/enrichment/normalizers.py`
- Test: `tests/test_normalizers.py`

**Step 1: Write the failing tests**

```python
# tests/test_normalizers.py
import pytest
from compgraph.enrichment.normalizers import normalize_title_for_grouping


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Basic cleanup
        ("  Field Representative  ", "field representative"),
        ("BRAND AMBASSADOR", "brand ambassador"),
        # Strip trailing location
        ("Field Rep - Dallas, TX", "field rep"),
        ("Merchandiser | Houston, TX, US", "merchandiser"),
        ("Brand Ambassador (Orlando, FL)", "brand ambassador"),
        # Strip trailing company name
        ("Field Rep - 2020 Companies", "field rep"),
        ("Merchandiser | BDS Connected Solutions", "merchandiser"),
        # Strip both
        ("Field Representative - Samsung - Dallas, TX", "field representative - samsung"),
        # Collapse whitespace
        ("Field   Rep    Dallas", "field rep dallas"),
        # None/empty
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_title(raw, expected):
    assert normalize_title_for_grouping(raw) == expected
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_normalizers.py -v
```
Expected: FAIL — module not found.

**Step 3: Write implementation**

```python
# src/compgraph/enrichment/normalizers.py
"""Deterministic normalization functions for aggregation grouping."""

from __future__ import annotations

import re

# Known company names to strip from titles
_COMPANY_NAMES = [
    "2020 companies",
    "bds connected solutions",
    "marketsource",
    "t-roc",
    "mosaic sales solutions",
    "advantage solutions",
    "acosta",
]

# Pattern: trailing " - City, ST" or " | City, ST, US" or " (City, ST)"
_LOCATION_SUFFIX = re.compile(
    r"\s*[-|]\s*[A-Za-z\s]+,\s*[A-Z]{2}(?:,\s*US)?\s*$"
    r"|\s*\([A-Za-z\s]+,\s*[A-Z]{2}(?:,\s*US)?\)\s*$"
)

# Pattern: trailing " - CompanyName" or " | CompanyName"
_COMPANY_SUFFIX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"\s*[-|]\s*{re.escape(name)}\s*$", re.IGNORECASE)
    for name in _COMPANY_NAMES
]


def normalize_title_for_grouping(title: str | None) -> str | None:
    """Normalize a job title for aggregation grouping.

    Deterministic, no LLM. Strips locations, company names, normalizes case/whitespace.
    """
    if not title or not title.strip():
        return None

    result = title.strip().lower()

    # Strip trailing location patterns
    result = _LOCATION_SUFFIX.sub("", result)

    # Strip trailing company names
    for pattern in _COMPANY_SUFFIX_PATTERNS:
        result = pattern.sub("", result)

    # Collapse whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result if result else None
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_normalizers.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/compgraph/enrichment/normalizers.py tests/test_normalizers.py
git commit -m "feat: add deterministic title normalization for aggregation grouping"
```

---

### Task 3: Title Normalization Backfill Script

**Files:**
- Create: `scripts/backfill_title_normalization.py`

**Step 1: Write the backfill script**

```python
# scripts/backfill_title_normalization.py
"""Backfill title_normalized for all posting_enrichments."""

import asyncio
import logging

from sqlalchemy import select, update

from compgraph.db.models import PostingEnrichment, PostingSnapshot
from compgraph.db.session import async_session_factory, engine
from compgraph.enrichment.normalizers import normalize_title_for_grouping

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def backfill() -> None:
    async with async_session_factory() as session:
        # Fetch enrichments missing title_normalized with their latest snapshot title
        stmt = (
            select(PostingEnrichment.id, PostingSnapshot.title_raw)
            .join(PostingSnapshot, PostingEnrichment.posting_id == PostingSnapshot.posting_id)
            .where(PostingEnrichment.title_normalized.is_(None))
            .distinct(PostingEnrichment.id)
            .order_by(PostingEnrichment.id, PostingSnapshot.snapshot_date.desc())
        )
        rows = (await session.execute(stmt)).all()
        logger.info("Found %d enrichments missing title_normalized", len(rows))

        updated = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            for enrichment_id, title_raw in batch:
                normalized = normalize_title_for_grouping(title_raw)
                if normalized:
                    await session.execute(
                        update(PostingEnrichment)
                        .where(PostingEnrichment.id == enrichment_id)
                        .values(title_normalized=normalized)
                    )
                    updated += 1
            await session.commit()
            logger.info("Batch %d: updated %d/%d", i // BATCH_SIZE + 1, updated, len(rows))

    logger.info("Backfill complete: %d titles normalized", updated)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(backfill())
```

**Step 2: Run the backfill**

```bash
op run --env-file=.env -- uv run python scripts/backfill_title_normalization.py
```

**Step 3: Verify fill rate**

```bash
op run --env-file=.env -- uv run python -c "
import asyncio
from sqlalchemy import text
from compgraph.db.session import async_session_factory, engine
async def check():
    async with async_session_factory() as s:
        r = await s.execute(text(
            'SELECT count(*) total, count(title_normalized) filled FROM posting_enrichments'
        ))
        row = r.fetchone()
        print(f'title_normalized: {row[1]}/{row[0]} ({row[1]*100//row[0]}%)')
    await engine.dispose()
asyncio.run(check())
"
```
Expected: ~99% fill rate (matching enrichment coverage).

**Step 4: Commit**

```bash
git add scripts/backfill_title_normalization.py
git commit -m "feat: backfill title_normalized across all enrichments"
```

---

### Task 4: Location Regex Normalizer

**Files:**
- Modify: `src/compgraph/enrichment/normalizers.py`
- Modify: `tests/test_normalizers.py`

**Step 1: Add failing tests**

```python
# Append to tests/test_normalizers.py
from compgraph.enrichment.normalizers import normalize_location_raw


@pytest.mark.parametrize(
    "raw,expected_city,expected_state,expected_country",
    [
        # Standard US: "City, ST, US" → strip ", US"
        ("Dallas, TX, US", "Dallas", "TX", "US"),
        ("ORLANDO, FL, US", "Orlando", "FL", "US"),
        # Without country suffix
        ("Dallas, TX", "Dallas", "TX", "US"),
        # Canadian
        ("Toronto, ON, CA", "Toronto", "ON", "CA"),
        ("Toronto, ON", "Toronto", "ON", "CA"),
        # With ZIP code
        ("Dallas, TX 75201, US", "Dallas", "TX", "US"),
        ("Orlando, FL 32801", "Orlando", "FL", "US"),
        # Extra whitespace
        ("  Dallas ,  TX  ", "Dallas", "TX", "US"),
        # None/empty
        (None, None, None, None),
        ("", None, None, None),
    ],
)
def test_normalize_location_raw(raw, expected_city, expected_state, expected_country):
    result = normalize_location_raw(raw)
    if expected_city is None:
        assert result is None
    else:
        assert result == (expected_city, expected_state, expected_country)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_normalizers.py::test_normalize_location_raw -v
```

**Step 3: Add implementation**

```python
# Append to src/compgraph/enrichment/normalizers.py

# Canadian provinces — used to detect Canadian locations
_CA_PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}

# ZIP code pattern
_ZIP_CODE = re.compile(r"\s+\d{5}(?:-\d{4})?")

# Country suffix
_COUNTRY_SUFFIX = re.compile(r",\s*(?:US|CA)\s*$", re.IGNORECASE)


def normalize_location_raw(location: str | None) -> tuple[str, str, str] | None:
    """Normalize a raw location string into (city, state, country).

    Layer 1 of market normalization:
    - Strips ", US" / ", CA" suffix
    - Removes embedded ZIP codes
    - Normalizes case to title case
    - Detects country from state/province code

    Returns (city, state, country) or None if unparseable.
    """
    if not location or not location.strip():
        return None

    loc = location.strip()

    # Extract country if present at end
    country_match = re.search(r",\s*(US|CA)\s*$", loc, re.IGNORECASE)
    explicit_country = country_match.group(1).upper() if country_match else None
    loc = _COUNTRY_SUFFIX.sub("", loc)

    # Remove ZIP codes
    loc = _ZIP_CODE.sub("", loc)

    # Split into parts
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if len(parts) < 2:
        return None

    city = parts[0].title()
    state = parts[1].strip().upper()

    # Determine country
    if explicit_country:
        country = explicit_country
    elif state in _CA_PROVINCES:
        country = "CA"
    else:
        country = "US"

    return (city, state, country)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_normalizers.py -v
```

**Step 5: Commit**

```bash
git add src/compgraph/enrichment/normalizers.py tests/test_normalizers.py
git commit -m "feat: add location regex normalizer (Layer 1 of market normalization)"
```

---

## Phase 2: Schema & Seeding

### Task 5: Location Mappings Table + Migration

**Files:**
- Modify: `src/compgraph/db/models.py` (add `LocationMapping` class)
- Modify: `src/compgraph/db/models.py` (add `country` column to `Market`)
- Create: `alembic/versions/xxxx_add_location_mappings.py`

**Step 1: Add the model**

Add after the `Market` class in `src/compgraph/db/models.py`:

```python
class LocationMapping(Base):
    __tablename__ = "location_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    city_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    metro_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metro_state: Mapped[str] = mapped_column(String(10), nullable=False)
    metro_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("city_normalized", "state", "country", name="uq_location_mapping"),
    )
```

Also add `country` column to the `Market` model:

```python
country: Mapped[str] = mapped_column(String(2), nullable=True, default="US")
```

**Step 2: Write a unit test for the model**

```python
# tests/test_location_mapping_model.py
from compgraph.db.models import LocationMapping


class TestLocationMappingModel:
    def test_table_exists(self):
        table = LocationMapping.__table__
        assert table.name == "location_mappings"

    def test_required_columns(self):
        cols = LocationMapping.__table__.c
        assert "city_normalized" in cols
        assert "state" in cols
        assert "country" in cols
        assert "metro_name" in cols
        assert "metro_state" in cols
        assert "metro_country" in cols

    def test_unique_constraint(self):
        constraints = [c.name for c in LocationMapping.__table__.constraints if hasattr(c, "name")]
        assert "uq_location_mapping" in constraints
```

**Step 3: Run test**

```bash
uv run pytest tests/test_location_mapping_model.py -v
```

**Step 4: Generate and run migration**

```bash
op run --env-file=.env -- uv run alembic revision --autogenerate -m "add location_mappings table and market country"
op run --env-file=.env -- uv run alembic upgrade head
```

**Step 5: Commit**

```bash
git add src/compgraph/db/models.py tests/test_location_mapping_model.py alembic/versions/*location_mappings*
git commit -m "feat: add location_mappings table for market normalization"
```

---

### Task 6: LLM Location Seeding Script

**Files:**
- Create: `scripts/seed_location_mappings.py`

This script extracts all distinct (city, state, country) triples from `posting_snapshots`, batches them to Haiku 4.5 for metro area mapping, and inserts into `location_mappings`.

**Step 1: Write the seeding script**

```python
# scripts/seed_location_mappings.py
"""Seed location_mappings table using LLM metro area classification.

Usage:
    op run --env-file=.env -- uv run python scripts/seed_location_mappings.py
    op run --env-file=.env -- uv run python scripts/seed_location_mappings.py --dry-run
"""

import asyncio
import json
import logging
import sys

import anthropic
from sqlalchemy import select, text

from compgraph.db.models import LocationMapping
from compgraph.db.session import async_session_factory, engine
from compgraph.enrichment.normalizers import normalize_location_raw

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 50
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a geography expert. Given a list of (city, state, country) tuples,
map each to its US Census Metropolitan Statistical Area (MSA) name or Canadian Census
Metropolitan Area (CMA) name.

Respond with a JSON array where each element has:
- city: the input city name
- state: the input state/province code
- country: "US" or "CA"
- metro_name: the MSA/CMA name (e.g., "Dallas-Fort Worth-Arlington")
- metro_state: primary state of the metro (e.g., "TX")
- metro_country: "US" or "CA"

For cities not in any MSA/CMA, use the city name itself as metro_name.
Return ONLY the JSON array, no other text."""


async def extract_distinct_locations() -> list[tuple[str, str, str]]:
    """Get all distinct normalized locations from posting_snapshots."""
    async with async_session_factory() as session:
        rows = (await session.execute(
            text("SELECT DISTINCT location_raw FROM posting_snapshots WHERE location_raw IS NOT NULL")
        )).all()

    locations: set[tuple[str, str, str]] = set()
    for (raw,) in rows:
        result = normalize_location_raw(raw)
        if result:
            locations.add(result)

    return sorted(locations)


async def get_existing_mappings() -> set[tuple[str, str, str]]:
    """Get already-seeded (city, state, country) tuples."""
    async with async_session_factory() as session:
        rows = (await session.execute(
            select(LocationMapping.city_normalized, LocationMapping.state, LocationMapping.country)
        )).all()
    return {(r[0], r[1], r[2]) for r in rows}


async def classify_batch(
    client: anthropic.AsyncAnthropic,
    batch: list[tuple[str, str, str]],
) -> list[dict]:
    """Send a batch of locations to Haiku for metro classification."""
    input_text = json.dumps([
        {"city": city, "state": state, "country": country}
        for city, state, country in batch
    ])

    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": input_text}],
    )

    return json.loads(response.content[0].text)


async def seed(dry_run: bool = False) -> None:
    all_locations = await extract_distinct_locations()
    existing = await get_existing_mappings()
    new_locations = [loc for loc in all_locations if loc not in existing]

    logger.info(
        "Total distinct locations: %d, already seeded: %d, new: %d",
        len(all_locations), len(existing), len(new_locations),
    )

    if dry_run:
        logger.info("Dry run — would seed %d locations in %d batches",
                     len(new_locations), (len(new_locations) + BATCH_SIZE - 1) // BATCH_SIZE)
        await engine.dispose()
        return

    if not new_locations:
        logger.info("Nothing to seed")
        await engine.dispose()
        return

    client = anthropic.AsyncAnthropic()
    total_inserted = 0

    for i in range(0, len(new_locations), BATCH_SIZE):
        batch = new_locations[i : i + BATCH_SIZE]
        logger.info("Batch %d: classifying %d locations...", i // BATCH_SIZE + 1, len(batch))

        try:
            results = await classify_batch(client, batch)
        except Exception:
            logger.exception("Batch %d failed — skipping", i // BATCH_SIZE + 1)
            continue

        async with async_session_factory() as session:
            for item in results:
                mapping = LocationMapping(
                    city_normalized=item["city"],
                    state=item["state"],
                    country=item["country"],
                    metro_name=item["metro_name"],
                    metro_state=item["metro_state"],
                    metro_country=item["metro_country"],
                )
                session.add(mapping)
            await session.commit()
            total_inserted += len(results)
            logger.info("Batch %d: inserted %d mappings (total: %d)",
                         i // BATCH_SIZE + 1, len(results), total_inserted)

    logger.info("Seeding complete: %d mappings inserted", total_inserted)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed(dry_run="--dry-run" in sys.argv))
```

**Step 2: Dry run to verify location extraction**

```bash
op run --env-file=.env -- uv run python scripts/seed_location_mappings.py --dry-run
```

**Step 3: Run seeding**

```bash
op run --env-file=.env -- uv run python scripts/seed_location_mappings.py
```

**Step 4: Verify**

```bash
op run --env-file=.env -- uv run python -c "
import asyncio
from sqlalchemy import text
from compgraph.db.session import async_session_factory, engine
async def check():
    async with async_session_factory() as s:
        r = await s.execute(text('SELECT count(*), count(distinct metro_name) FROM location_mappings'))
        row = r.fetchone()
        print(f'Mappings: {row[0]} cities → {row[1]} metros')
    await engine.dispose()
asyncio.run(check())
"
```

**Step 5: Commit**

```bash
git add scripts/seed_location_mappings.py
git commit -m "feat: add LLM-seeded location mapping script for market normalization"
```

---

### Task 7: Populate Markets Table

**Files:**
- Create: `scripts/populate_markets.py`

**Step 1: Write the population script**

```python
# scripts/populate_markets.py
"""Populate markets table from seeded location_mappings."""

import asyncio
import logging

from sqlalchemy import select, text

from compgraph.db.models import LocationMapping, Market
from compgraph.db.session import async_session_factory, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def populate() -> None:
    async with async_session_factory() as session:
        # Get distinct metros from location_mappings
        stmt = select(
            LocationMapping.metro_name,
            LocationMapping.metro_state,
            LocationMapping.metro_country,
        ).distinct()
        metros = (await session.execute(stmt)).all()

        # Get existing markets
        existing = {
            (r[0], r[1])
            for r in (await session.execute(select(Market.name, Market.state))).all()
        }

        inserted = 0
        for metro_name, metro_state, metro_country in metros:
            if (metro_name, metro_state) in existing:
                continue
            market = Market(
                name=metro_name,
                state=metro_state,
                country=metro_country,
            )
            session.add(market)
            inserted += 1

        await session.commit()
        logger.info("Inserted %d new markets (skipped %d existing)", inserted, len(existing))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(populate())
```

**Step 2: Run it**

```bash
op run --env-file=.env -- uv run python scripts/populate_markets.py
```

**Step 3: Verify**

```bash
op run --env-file=.env -- uv run python -c "
import asyncio
from sqlalchemy import text
from compgraph.db.session import async_session_factory, engine
async def check():
    async with async_session_factory() as s:
        r = await s.execute(text('SELECT count(*) FROM markets'))
        print(f'Markets: {r.scalar_one()}')
        r = await s.execute(text('SELECT name, state, country FROM markets ORDER BY name LIMIT 10'))
        for row in r: print(f'  {row[0]}, {row[1]} ({row[2]})')
    await engine.dispose()
asyncio.run(check())
"
```

**Step 4: Commit**

```bash
git add scripts/populate_markets.py
git commit -m "feat: populate markets table from location mappings"
```

---

### Task 8: New Aggregation Table Models + Migration

**Files:**
- Modify: `src/compgraph/db/models.py` (add 3 new Agg classes)
- Create: `alembic/versions/xxxx_add_new_agg_tables.py`
- Create: `tests/test_agg_models.py`

**Step 1: Write unit tests for new models**

```python
# tests/test_agg_models.py
import pytest
from compgraph.db.models import AggBrandChurnSignals, AggMarketCoverageGaps, AggBrandAgencyOverlap


class TestAggBrandChurnSignals:
    def test_table_name(self):
        assert AggBrandChurnSignals.__tablename__ == "agg_brand_churn_signals"

    def test_required_columns(self):
        cols = AggBrandChurnSignals.__table__.c
        for col_name in ("company_id", "brand_id", "period", "active_posting_count",
                         "velocity_delta", "repost_rate", "churn_signal_score"):
            assert col_name in cols, f"Missing column: {col_name}"


class TestAggMarketCoverageGaps:
    def test_table_name(self):
        assert AggMarketCoverageGaps.__tablename__ == "agg_market_coverage_gaps"

    def test_required_columns(self):
        cols = AggMarketCoverageGaps.__table__.c
        for col_name in ("company_id", "market_id", "total_active_postings",
                         "brand_count", "brand_names"):
            assert col_name in cols, f"Missing column: {col_name}"


class TestAggBrandAgencyOverlap:
    def test_table_name(self):
        assert AggBrandAgencyOverlap.__tablename__ == "agg_brand_agency_overlap"

    def test_required_columns(self):
        cols = AggBrandAgencyOverlap.__table__.c
        for col_name in ("brand_id", "agency_count", "primary_company_id",
                         "primary_share", "is_exclusive", "is_contested"):
            assert col_name in cols, f"Missing column: {col_name}"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_agg_models.py -v
```

**Step 3: Add model classes to `src/compgraph/db/models.py`**

Add after the existing `AggPostingLifecycle` class:

```python
class AggBrandChurnSignals(Base):
    __tablename__ = "agg_brand_churn_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    active_posting_count: Mapped[int] = mapped_column(Integer, default=0)
    prior_period_count: Mapped[int] = mapped_column(Integer, default=0)
    velocity_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_days_active: Mapped[float | None] = mapped_column(Float, nullable=True)
    repost_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    churn_signal_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_churn_signals_company_brand", "company_id", "brand_id"),
    )


class AggMarketCoverageGaps(Base):
    __tablename__ = "agg_market_coverage_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"), nullable=False)
    total_active_postings: Mapped[int] = mapped_column(Integer, default=0)
    brand_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    period: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_coverage_gaps_company_market", "company_id", "market_id"),
    )


class AggBrandAgencyOverlap(Base):
    __tablename__ = "agg_brand_agency_overlap"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False)
    agency_count: Mapped[int] = mapped_column(Integer, default=0)
    agency_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    primary_company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    primary_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_contested: Mapped[bool] = mapped_column(Boolean, default=False)
    total_postings: Mapped[int] = mapped_column(Integer, default=0)
    period: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_brand_agency_overlap_brand", "brand_id"),
    )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_agg_models.py -v
```

**Step 5: Generate and run migration**

```bash
op run --env-file=.env -- uv run alembic revision --autogenerate -m "add brand churn, coverage gaps, and agency overlap agg tables"
op run --env-file=.env -- uv run alembic upgrade head
```

**Step 6: Commit**

```bash
git add src/compgraph/db/models.py tests/test_agg_models.py alembic/versions/*brand_churn*
git commit -m "feat: add 3 new aggregation table schemas for BD intelligence"
```

---

## Phase 3: Aggregation Jobs

### Task 9: Base Aggregation Framework

**Files:**
- Create: `src/compgraph/aggregation/__init__.py` (may already exist as empty)
- Create: `src/compgraph/aggregation/base.py`
- Create: `tests/test_aggregation_base.py`

All 7 aggregation jobs share the same truncate+insert pattern. Define a base class.

**Step 1: Write failing tests**

```python
# tests/test_aggregation_base.py
import pytest
from unittest.mock import AsyncMock, patch
from compgraph.aggregation.base import AggregationJob


class FakeJob(AggregationJob):
    table_name = "agg_test"

    async def compute_rows(self, session):
        return [{"id": "test", "value": 1}]


class TestAggregationJobBase:
    def test_subclass_requires_table_name(self):
        with pytest.raises(TypeError):
            class BadJob(AggregationJob):
                pass
            BadJob()

    def test_subclass_with_table_name(self):
        job = FakeJob()
        assert job.table_name == "agg_test"

    @pytest.mark.asyncio
    async def test_run_calls_truncate_and_insert(self):
        job = FakeJob()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch.object(job, "compute_rows", return_value=[{"v": 1}]):
            result = await job.run(mock_session)

        # Should have called execute for TRUNCATE + INSERT
        assert mock_session.execute.call_count >= 1
        assert result == 1  # 1 row inserted
```

**Step 2: Run test to verify failure**

```bash
uv run pytest tests/test_aggregation_base.py -v
```

**Step 3: Implement base class**

```python
# src/compgraph/aggregation/base.py
"""Base class for truncate+insert aggregation jobs."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AggregationJob(ABC):
    """Base for all aggregation rebuild jobs.

    Subclasses define table_name and compute_rows().
    The run() method handles truncate+insert in a transaction.
    """

    table_name: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "table_name", None) and not getattr(cls, "__abstractmethods__", None):
            raise TypeError(f"{cls.__name__} must define table_name")

    @abstractmethod
    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        """Compute aggregated rows from source tables. Returns list of dicts."""
        ...

    async def run(self, session: AsyncSession) -> int:
        """Truncate the target table and insert freshly computed rows."""
        logger.info("[AGG] Starting rebuild of %s", self.table_name)

        # Truncate
        await session.execute(text(f"TRUNCATE TABLE {self.table_name}"))  # noqa: S608

        # Compute
        rows = await self.compute_rows(session)
        if not rows:
            logger.warning("[AGG] %s: compute_rows returned 0 rows", self.table_name)
            await session.commit()
            return 0

        # Bulk insert
        columns = rows[0].keys()
        col_list = ", ".join(columns)
        val_list = ", ".join(f":{c}" for c in columns)
        stmt = text(f"INSERT INTO {self.table_name} ({col_list}) VALUES ({val_list})")  # noqa: S608

        await session.execute(stmt, rows)
        await session.commit()

        logger.info("[AGG] %s: inserted %d rows", self.table_name, len(rows))
        return len(rows)
```

**Step 4: Update `__init__.py`**

```python
# src/compgraph/aggregation/__init__.py
"""Aggregation rebuild jobs — truncate+insert pattern."""
```

**Step 5: Run tests**

```bash
uv run pytest tests/test_aggregation_base.py -v
```

**Step 6: Commit**

```bash
git add src/compgraph/aggregation/ tests/test_aggregation_base.py
git commit -m "feat: add base aggregation job framework with truncate+insert pattern"
```

---

### Task 10: Daily Velocity Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/daily_velocity.py`
- Create: `tests/test_agg_daily_velocity.py`

**Step 1: Write failing test**

```python
# tests/test_agg_daily_velocity.py
import pytest
from compgraph.aggregation.daily_velocity import DailyVelocityJob


class TestDailyVelocityJob:
    def test_table_name(self):
        job = DailyVelocityJob()
        assert job.table_name == "agg_daily_velocity"

    def test_is_aggregation_job(self):
        from compgraph.aggregation.base import AggregationJob
        assert issubclass(DailyVelocityJob, AggregationJob)
```

**Step 2: Implement**

```python
# src/compgraph/aggregation/daily_velocity.py
"""Daily velocity aggregation: new/closed/active postings per company per day."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH dates AS (
    SELECT DISTINCT snapshot_date AS date FROM posting_snapshots
),
daily AS (
    SELECT
        d.date,
        p.company_id,
        count(*) FILTER (WHERE p.first_seen_at::date = d.date) AS new_postings,
        count(*) FILTER (WHERE NOT p.is_active AND p.last_seen_at::date = d.date) AS closed_postings,
        count(*) FILTER (WHERE p.is_active OR p.last_seen_at::date >= d.date) AS active_postings
    FROM dates d
    CROSS JOIN postings p
    WHERE p.first_seen_at::date <= d.date
    GROUP BY d.date, p.company_id
)
SELECT
    date, company_id, new_postings, closed_postings, active_postings,
    new_postings - closed_postings AS net_change
FROM daily
ORDER BY date, company_id
"""


class DailyVelocityJob(AggregationJob):
    table_name = "agg_daily_velocity"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "date": row.date,
                "company_id": str(row.company_id),
                "new_postings": row.new_postings,
                "closed_postings": row.closed_postings,
                "active_postings": row.active_postings,
                "net_change": row.net_change,
            }
            for row in result
        ]
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_agg_daily_velocity.py -v
```

**Step 4: Commit**

```bash
git add src/compgraph/aggregation/daily_velocity.py tests/test_agg_daily_velocity.py
git commit -m "feat: add daily velocity aggregation job"
```

---

### Task 11: Brand Timeline Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/brand_timeline.py`
- Create: `tests/test_agg_brand_timeline.py`

**Step 1: Write failing test**

```python
# tests/test_agg_brand_timeline.py
from compgraph.aggregation.brand_timeline import BrandTimelineJob
from compgraph.aggregation.base import AggregationJob


class TestBrandTimelineJob:
    def test_table_name(self):
        assert BrandTimelineJob().table_name == "agg_brand_timeline"

    def test_is_aggregation_job(self):
        assert issubclass(BrandTimelineJob, AggregationJob)
```

**Step 2: Implement**

```python
# src/compgraph/aggregation/brand_timeline.py
"""Brand timeline aggregation: brand-company relationship metrics over time."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
SELECT
    p.company_id,
    pbm.resolved_brand_id AS brand_id,
    min(p.first_seen_at) AS first_seen_at,
    max(p.last_seen_at) AS last_seen_at,
    bool_or(p.is_active) AS is_currently_active,
    count(*) AS total_postings_all_time,
    count(*) FILTER (WHERE p.is_active) AS current_active_postings
FROM posting_brand_mentions pbm
JOIN postings p ON p.id = pbm.posting_id
WHERE pbm.resolved_brand_id IS NOT NULL
GROUP BY p.company_id, pbm.resolved_brand_id
"""


class BrandTimelineJob(AggregationJob):
    table_name = "agg_brand_timeline"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "company_id": str(row.company_id),
                "brand_id": str(row.brand_id),
                "first_seen_at": row.first_seen_at,
                "last_seen_at": row.last_seen_at,
                "is_currently_active": row.is_currently_active,
                "total_postings_all_time": row.total_postings_all_time,
                "current_active_postings": row.current_active_postings,
                "peak_active_postings": row.current_active_postings,  # Will improve with time-series data
                "peak_date": None,
            }
            for row in result
        ]
```

**Step 3: Run tests, commit**

```bash
uv run pytest tests/test_agg_brand_timeline.py -v
git add src/compgraph/aggregation/brand_timeline.py tests/test_agg_brand_timeline.py
git commit -m "feat: add brand timeline aggregation job"
```

---

### Task 12: Posting Lifecycle Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/posting_lifecycle.py`
- Create: `tests/test_agg_posting_lifecycle.py`

**Step 1: Write test + implement**

```python
# tests/test_agg_posting_lifecycle.py
from compgraph.aggregation.posting_lifecycle import PostingLifecycleJob
from compgraph.aggregation.base import AggregationJob


class TestPostingLifecycleJob:
    def test_table_name(self):
        assert PostingLifecycleJob().table_name == "agg_posting_lifecycle"

    def test_is_aggregation_job(self):
        assert issubclass(PostingLifecycleJob, AggregationJob)
```

```python
# src/compgraph/aggregation/posting_lifecycle.py
"""Posting lifecycle aggregation: avg days open, repost rate, churn per company."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH lifecycle AS (
    SELECT
        p.company_id,
        pe.role_archetype,
        EXTRACT(EPOCH FROM (COALESCE(p.last_seen_at, now()) - p.first_seen_at)) / 86400.0 AS days_open,
        p.times_reposted
    FROM postings p
    LEFT JOIN posting_enrichments pe ON pe.posting_id = p.id
),
stats AS (
    SELECT
        company_id,
        role_archetype,
        current_date AS period,
        avg(days_open) AS avg_days_open,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY days_open) AS median_days_open,
        avg(CASE WHEN times_reposted > 0 THEN 1.0 ELSE 0.0 END) AS repost_rate,
        avg(NULLIF(times_reposted, 0)::float) AS avg_repost_gap_days
    FROM lifecycle
    GROUP BY company_id, role_archetype
)
SELECT * FROM stats
"""


class PostingLifecycleJob(AggregationJob):
    table_name = "agg_posting_lifecycle"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "company_id": str(row.company_id),
                "role_archetype": row.role_archetype,
                "period": row.period,
                "avg_days_open": row.avg_days_open,
                "median_days_open": row.median_days_open,
                "repost_rate": row.repost_rate,
                "avg_repost_gap_days": row.avg_repost_gap_days,
            }
            for row in result
        ]
```

**Step 2: Run tests, commit**

```bash
uv run pytest tests/test_agg_posting_lifecycle.py -v
git add src/compgraph/aggregation/posting_lifecycle.py tests/test_agg_posting_lifecycle.py
git commit -m "feat: add posting lifecycle aggregation job"
```

---

### Task 13: Pay Benchmarks Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/pay_benchmarks.py`
- Create: `tests/test_agg_pay_benchmarks.py`

Depends on market normalization (location_mappings + markets populated).

**Step 1: Write test + implement**

```python
# tests/test_agg_pay_benchmarks.py
from compgraph.aggregation.pay_benchmarks import PayBenchmarksJob
from compgraph.aggregation.base import AggregationJob


class TestPayBenchmarksJob:
    def test_table_name(self):
        assert PayBenchmarksJob().table_name == "agg_pay_benchmarks"

    def test_is_aggregation_job(self):
        assert issubclass(PayBenchmarksJob, AggregationJob)
```

```python
# src/compgraph/aggregation/pay_benchmarks.py
"""Pay benchmarks aggregation: compensation stats by role, market, company."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH latest_location AS (
    SELECT DISTINCT ON (posting_id) posting_id, location_raw
    FROM posting_snapshots
    ORDER BY posting_id, snapshot_date DESC
),
pay_data AS (
    SELECT
        p.company_id,
        pe.role_archetype,
        lm.metro_name,
        m.id AS market_id,
        pbm.resolved_brand_id AS brand_id,
        pe.pay_min,
        pe.pay_max,
        pe.pay_frequency
    FROM posting_enrichments pe
    JOIN postings p ON p.id = pe.posting_id
    LEFT JOIN latest_location ll ON ll.posting_id = p.id
    LEFT JOIN location_mappings lm ON (
        lm.city_normalized = split_part(ll.location_raw, ',', 1)
    )
    LEFT JOIN markets m ON m.name = lm.metro_name AND m.state = lm.metro_state
    LEFT JOIN posting_brand_mentions pbm ON (
        pbm.posting_id = p.id AND pbm.resolved_brand_id IS NOT NULL
    )
    WHERE pe.pay_min IS NOT NULL
)
SELECT
    company_id,
    role_archetype,
    market_id,
    brand_id,
    current_date AS period,
    avg(pay_min) AS avg_pay_min,
    avg(pay_max) AS avg_pay_max,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY pay_min) AS median_pay_min,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY pay_max) AS median_pay_max,
    count(*) AS sample_size
FROM pay_data
GROUP BY company_id, role_archetype, market_id, brand_id
HAVING count(*) >= 3
"""


class PayBenchmarksJob(AggregationJob):
    table_name = "agg_pay_benchmarks"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "company_id": str(row.company_id),
                "role_archetype": row.role_archetype,
                "market_id": str(row.market_id) if row.market_id else None,
                "brand_id": str(row.brand_id) if row.brand_id else None,
                "period": row.period,
                "avg_pay_min": row.avg_pay_min,
                "avg_pay_max": row.avg_pay_max,
                "median_pay_min": row.median_pay_min,
                "median_pay_max": row.median_pay_max,
                "sample_size": row.sample_size,
            }
            for row in result
        ]
```

**Step 2: Run tests, commit**

```bash
uv run pytest tests/test_agg_pay_benchmarks.py -v
git add src/compgraph/aggregation/pay_benchmarks.py tests/test_agg_pay_benchmarks.py
git commit -m "feat: add pay benchmarks aggregation job with market dimension"
```

---

### Task 14: Brand Churn Signals Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/brand_churn.py`
- Create: `tests/test_agg_brand_churn.py`

**Step 1: Write test + implement**

```python
# tests/test_agg_brand_churn.py
from compgraph.aggregation.brand_churn import BrandChurnSignalsJob
from compgraph.aggregation.base import AggregationJob


class TestBrandChurnSignalsJob:
    def test_table_name(self):
        assert BrandChurnSignalsJob().table_name == "agg_brand_churn_signals"

    def test_is_aggregation_job(self):
        assert issubclass(BrandChurnSignalsJob, AggregationJob)
```

```python
# src/compgraph/aggregation/brand_churn.py
"""Brand churn signals: detect deteriorating competitor-brand relationships."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH brand_activity AS (
    SELECT
        p.company_id,
        pbm.resolved_brand_id AS brand_id,
        count(*) FILTER (WHERE p.is_active) AS active_posting_count,
        count(*) FILTER (
            WHERE p.first_seen_at >= current_date - interval '7 days'
        ) AS new_last_7d,
        count(*) FILTER (
            WHERE p.first_seen_at >= current_date - interval '14 days'
              AND p.first_seen_at < current_date - interval '7 days'
        ) AS new_prior_7d,
        avg(
            EXTRACT(EPOCH FROM (COALESCE(p.last_seen_at, now()) - p.first_seen_at)) / 86400.0
        ) FILTER (WHERE p.is_active) AS avg_days_active,
        avg(CASE WHEN p.times_reposted > 0 THEN 1.0 ELSE 0.0 END) AS repost_rate
    FROM posting_brand_mentions pbm
    JOIN postings p ON p.id = pbm.posting_id
    WHERE pbm.resolved_brand_id IS NOT NULL
    GROUP BY p.company_id, pbm.resolved_brand_id
)
SELECT
    company_id,
    brand_id,
    current_date AS period,
    active_posting_count,
    new_prior_7d AS prior_period_count,
    CASE
        WHEN new_prior_7d > 0
        THEN (new_last_7d - new_prior_7d)::float / new_prior_7d
        ELSE 0
    END AS velocity_delta,
    avg_days_active,
    repost_rate,
    -- Churn score: higher = more likely churning
    -- Components: declining velocity (40%), aging postings (30%), high reposts (30%)
    (
        CASE WHEN new_prior_7d > 0 AND new_last_7d < new_prior_7d
             THEN 0.4 * least((new_prior_7d - new_last_7d)::float / new_prior_7d, 1.0)
             ELSE 0 END
        + CASE WHEN avg_days_active > 14 THEN 0.3 * least(avg_days_active / 30.0, 1.0)
               ELSE 0 END
        + CASE WHEN repost_rate > 0.3 THEN 0.3 * least(repost_rate, 1.0)
               ELSE 0 END
    ) AS churn_signal_score
FROM brand_activity
WHERE active_posting_count > 0
"""


class BrandChurnSignalsJob(AggregationJob):
    table_name = "agg_brand_churn_signals"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "company_id": str(row.company_id),
                "brand_id": str(row.brand_id),
                "period": row.period,
                "active_posting_count": row.active_posting_count,
                "prior_period_count": row.prior_period_count,
                "velocity_delta": row.velocity_delta,
                "avg_days_active": row.avg_days_active,
                "repost_rate": row.repost_rate,
                "churn_signal_score": row.churn_signal_score,
            }
            for row in result
        ]
```

**Step 2: Run tests, commit**

```bash
uv run pytest tests/test_agg_brand_churn.py -v
git add src/compgraph/aggregation/brand_churn.py tests/test_agg_brand_churn.py
git commit -m "feat: add brand churn signals aggregation job"
```

---

### Task 15: Market Coverage Gaps Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/coverage_gaps.py`
- Create: `tests/test_agg_coverage_gaps.py`

**Step 1: Write test + implement**

```python
# tests/test_agg_coverage_gaps.py
from compgraph.aggregation.coverage_gaps import MarketCoverageGapsJob
from compgraph.aggregation.base import AggregationJob


class TestMarketCoverageGapsJob:
    def test_table_name(self):
        assert MarketCoverageGapsJob().table_name == "agg_market_coverage_gaps"

    def test_is_aggregation_job(self):
        assert issubclass(MarketCoverageGapsJob, AggregationJob)
```

```python
# src/compgraph/aggregation/coverage_gaps.py
"""Market coverage gaps: where are competitors absent or thin?"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH latest_location AS (
    SELECT DISTINCT ON (posting_id) posting_id, location_raw
    FROM posting_snapshots
    ORDER BY posting_id, snapshot_date DESC
),
posting_market AS (
    SELECT
        p.id AS posting_id,
        p.company_id,
        m.id AS market_id
    FROM postings p
    JOIN latest_location ll ON ll.posting_id = p.id
    JOIN location_mappings lm ON (
        lm.city_normalized = split_part(ll.location_raw, ',', 1)
    )
    JOIN markets m ON m.name = lm.metro_name AND m.state = lm.metro_state
    WHERE p.is_active
)
SELECT
    pm.company_id,
    pm.market_id,
    current_date AS period,
    count(DISTINCT pm.posting_id) AS total_active_postings,
    count(DISTINCT pbm.resolved_brand_id) AS brand_count,
    array_agg(DISTINCT b.name ORDER BY b.name) FILTER (WHERE b.name IS NOT NULL) AS brand_names
FROM posting_market pm
LEFT JOIN posting_brand_mentions pbm ON pbm.posting_id = pm.posting_id
LEFT JOIN brands b ON b.id = pbm.resolved_brand_id
GROUP BY pm.company_id, pm.market_id
"""


class MarketCoverageGapsJob(AggregationJob):
    table_name = "agg_market_coverage_gaps"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "company_id": str(row.company_id),
                "market_id": str(row.market_id),
                "period": row.period,
                "total_active_postings": row.total_active_postings,
                "brand_count": row.brand_count,
                "brand_names": row.brand_names,
            }
            for row in result
        ]
```

**Step 2: Run tests, commit**

```bash
uv run pytest tests/test_agg_coverage_gaps.py -v
git add src/compgraph/aggregation/coverage_gaps.py tests/test_agg_coverage_gaps.py
git commit -m "feat: add market coverage gaps aggregation job"
```

---

### Task 16: Brand Agency Overlap Aggregation Job

**Files:**
- Create: `src/compgraph/aggregation/agency_overlap.py`
- Create: `tests/test_agg_agency_overlap.py`

**Step 1: Write test + implement**

```python
# tests/test_agg_agency_overlap.py
from compgraph.aggregation.agency_overlap import BrandAgencyOverlapJob
from compgraph.aggregation.base import AggregationJob


class TestBrandAgencyOverlapJob:
    def test_table_name(self):
        assert BrandAgencyOverlapJob().table_name == "agg_brand_agency_overlap"

    def test_is_aggregation_job(self):
        assert issubclass(BrandAgencyOverlapJob, AggregationJob)
```

```python
# src/compgraph/aggregation/agency_overlap.py
"""Brand-agency overlap: which brands use multiple competing agencies?"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.base import AggregationJob

_QUERY = """\
WITH brand_agencies AS (
    SELECT
        pbm.resolved_brand_id AS brand_id,
        p.company_id,
        c.name AS company_name,
        count(*) AS posting_count
    FROM posting_brand_mentions pbm
    JOIN postings p ON p.id = pbm.posting_id
    JOIN companies c ON c.id = p.company_id
    WHERE pbm.resolved_brand_id IS NOT NULL AND p.is_active
    GROUP BY pbm.resolved_brand_id, p.company_id, c.name
),
brand_totals AS (
    SELECT
        brand_id,
        sum(posting_count) AS total_postings,
        count(DISTINCT company_id) AS agency_count,
        array_agg(company_name ORDER BY posting_count DESC) AS agency_names
    FROM brand_agencies
    GROUP BY brand_id
),
brand_primary AS (
    SELECT DISTINCT ON (brand_id)
        brand_id,
        company_id AS primary_company_id,
        posting_count::float / NULLIF(
            (SELECT sum(ba2.posting_count) FROM brand_agencies ba2 WHERE ba2.brand_id = ba.brand_id), 0
        ) AS primary_share
    FROM brand_agencies ba
    ORDER BY brand_id, posting_count DESC
)
SELECT
    bt.brand_id,
    current_date AS period,
    bt.agency_count,
    bt.agency_names,
    bp.primary_company_id,
    bp.primary_share,
    bt.agency_count = 1 AS is_exclusive,
    bt.agency_count >= 2 AND bp.primary_share <= 0.6 AS is_contested,
    bt.total_postings
FROM brand_totals bt
JOIN brand_primary bp ON bp.brand_id = bt.brand_id
"""


class BrandAgencyOverlapJob(AggregationJob):
    table_name = "agg_brand_agency_overlap"

    async def compute_rows(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(text(_QUERY))
        return [
            {
                "id": str(uuid.uuid4()),
                "brand_id": str(row.brand_id),
                "period": row.period,
                "agency_count": row.agency_count,
                "agency_names": row.agency_names,
                "primary_company_id": str(row.primary_company_id) if row.primary_company_id else None,
                "primary_share": row.primary_share,
                "is_exclusive": row.is_exclusive,
                "is_contested": row.is_contested,
                "total_postings": row.total_postings,
            }
            for row in result
        ]
```

**Step 2: Run tests, commit**

```bash
uv run pytest tests/test_agg_agency_overlap.py -v
git add src/compgraph/aggregation/agency_overlap.py tests/test_agg_agency_overlap.py
git commit -m "feat: add brand-agency overlap aggregation job"
```

---

## Phase 4: Integration

### Task 17: Aggregation Orchestrator

**Files:**
- Create: `src/compgraph/aggregation/orchestrator.py`
- Create: `tests/test_aggregation_orchestrator.py`

Runs all 7 jobs in the correct order with error isolation.

**Step 1: Write failing test**

```python
# tests/test_aggregation_orchestrator.py
import pytest
from compgraph.aggregation.orchestrator import AggregationOrchestrator


class TestAggregationOrchestrator:
    def test_job_count(self):
        orch = AggregationOrchestrator()
        assert len(orch.jobs) == 7

    def test_job_order(self):
        """Pay benchmarks and coverage gaps must come after velocity/timeline/lifecycle."""
        orch = AggregationOrchestrator()
        names = [j.table_name for j in orch.jobs]
        assert names.index("agg_daily_velocity") < names.index("agg_pay_benchmarks")
        assert names.index("agg_daily_velocity") < names.index("agg_market_coverage_gaps")
```

**Step 2: Implement**

```python
# src/compgraph/aggregation/orchestrator.py
"""Orchestrator that runs all aggregation jobs in order."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.aggregation.agency_overlap import BrandAgencyOverlapJob
from compgraph.aggregation.base import AggregationJob
from compgraph.aggregation.brand_churn import BrandChurnSignalsJob
from compgraph.aggregation.brand_timeline import BrandTimelineJob
from compgraph.aggregation.coverage_gaps import MarketCoverageGapsJob
from compgraph.aggregation.daily_velocity import DailyVelocityJob
from compgraph.aggregation.pay_benchmarks import PayBenchmarksJob
from compgraph.aggregation.posting_lifecycle import PostingLifecycleJob
from compgraph.db.session import async_session_factory

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    """Summary of a full aggregation run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    succeeded: dict[str, int] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


class AggregationOrchestrator:
    """Runs all aggregation jobs in dependency order."""

    def __init__(self) -> None:
        # Order matters: independent jobs first, then those needing market data
        self.jobs: list[AggregationJob] = [
            DailyVelocityJob(),
            BrandTimelineJob(),
            PostingLifecycleJob(),
            BrandChurnSignalsJob(),
            BrandAgencyOverlapJob(),
            PayBenchmarksJob(),          # Depends on markets
            MarketCoverageGapsJob(),     # Depends on markets
        ]

    async def run(self) -> AggregationResult:
        """Run all aggregation jobs. Each job is isolated — one failure doesn't block others."""
        result = AggregationResult()
        logger.info("[AGG] Starting aggregation run (%d jobs)", len(self.jobs))

        for job in self.jobs:
            try:
                async with async_session_factory() as session:
                    count = await job.run(session)
                result.succeeded[job.table_name] = count
                logger.info("[AGG] %s: OK (%d rows)", job.table_name, count)
            except Exception as exc:
                result.failed[job.table_name] = str(exc)
                logger.exception("[AGG] %s: FAILED", job.table_name)

        result.finished_at = datetime.now(UTC)
        logger.info(
            "[AGG] Run complete: %d succeeded, %d failed",
            len(result.succeeded), len(result.failed),
        )
        return result
```

**Step 3: Run tests, commit**

```bash
uv run pytest tests/test_aggregation_orchestrator.py -v
git add src/compgraph/aggregation/orchestrator.py tests/test_aggregation_orchestrator.py
git commit -m "feat: add aggregation orchestrator with all 7 jobs"
```

---

### Task 18: Wire Aggregation into Pipeline Scheduler

**Files:**
- Modify: `src/compgraph/scheduler/jobs.py` (add aggregate phase after enrich)

**Step 1: Read current `jobs.py` to understand exact insertion point**

```bash
uv run pytest tests/test_scheduler.py -v  # Baseline
```

**Step 2: Add aggregation phase after enrichment completes**

In `src/compgraph/scheduler/jobs.py`, after the enrichment phase completes successfully, add:

```python
# --- Phase 3: Aggregate ---
if enrich_succeeded:
    logger.info("[AGGREGATE] Starting aggregation phase")
    try:
        from compgraph.aggregation.orchestrator import AggregationOrchestrator
        agg_orchestrator = AggregationOrchestrator()
        agg_result = await agg_orchestrator.run()
        agg_succeeded = agg_result.ok
        if agg_result.failed:
            logger.warning("[AGGREGATE] Partial failure: %s", agg_result.failed)
    except Exception:
        logger.exception("[AGGREGATE] Aggregation phase failed")
        agg_succeeded = False
else:
    logger.warning("[AGGREGATE] Skipping aggregation — enrichment failed")
    agg_succeeded = False
```

**Step 3: Run scheduler tests**

```bash
uv run pytest tests/test_scheduler.py -v
```

**Step 4: Commit**

```bash
git add src/compgraph/scheduler/jobs.py
git commit -m "feat: wire aggregation phase into pipeline scheduler"
```

---

### Task 19: API Endpoints for Aggregation Data

**Files:**
- Create: `src/compgraph/api/routes/aggregation.py`
- Modify: `src/compgraph/main.py` (register router)
- Create: `tests/test_api_aggregation.py`

**Step 1: Write failing tests**

```python
# tests/test_api_aggregation.py
import pytest


class TestAggregationEndpoints:
    def test_velocity_endpoint_exists(self, client):
        r = client.get("/api/aggregation/velocity")
        assert r.status_code != 404

    def test_brand_timeline_endpoint_exists(self, client):
        r = client.get("/api/aggregation/brand-timeline")
        assert r.status_code != 404

    def test_pay_benchmarks_endpoint_exists(self, client):
        r = client.get("/api/aggregation/pay-benchmarks")
        assert r.status_code != 404

    def test_lifecycle_endpoint_exists(self, client):
        r = client.get("/api/aggregation/lifecycle")
        assert r.status_code != 404

    def test_churn_signals_endpoint_exists(self, client):
        r = client.get("/api/aggregation/churn-signals")
        assert r.status_code != 404

    def test_coverage_gaps_endpoint_exists(self, client):
        r = client.get("/api/aggregation/coverage-gaps")
        assert r.status_code != 404

    def test_agency_overlap_endpoint_exists(self, client):
        r = client.get("/api/aggregation/agency-overlap")
        assert r.status_code != 404

    def test_trigger_endpoint_exists(self, client):
        r = client.post("/api/aggregation/trigger")
        assert r.status_code != 404
```

**Step 2: Implement endpoints**

```python
# src/compgraph/api/routes/aggregation.py
"""Read-only API endpoints for aggregation data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import (
    AggBrandAgencyOverlap,
    AggBrandChurnSignals,
    AggBrandTimeline,
    AggDailyVelocity,
    AggMarketCoverageGaps,
    AggPayBenchmarks,
    AggPostingLifecycle,
)

router = APIRouter(prefix="/api/aggregation", tags=["aggregation"])


class TriggerResponse(BaseModel):
    message: str


@router.get("/velocity")
async def get_velocity(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AggDailyVelocity).order_by(AggDailyVelocity.date.desc()).limit(500))
    return [row._mapping for row in result]


@router.get("/brand-timeline")
async def get_brand_timeline(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AggBrandTimeline).limit(500))
    return [row._mapping for row in result]


@router.get("/pay-benchmarks")
async def get_pay_benchmarks(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AggPayBenchmarks).limit(500))
    return [row._mapping for row in result]


@router.get("/lifecycle")
async def get_lifecycle(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AggPostingLifecycle).limit(500))
    return [row._mapping for row in result]


@router.get("/churn-signals")
async def get_churn_signals(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(AggBrandChurnSignals).order_by(AggBrandChurnSignals.churn_signal_score.desc()).limit(100)
    )
    return [row._mapping for row in result]


@router.get("/coverage-gaps")
async def get_coverage_gaps(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(AggMarketCoverageGaps).limit(500))
    return [row._mapping for row in result]


@router.get("/agency-overlap")
async def get_agency_overlap(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(AggBrandAgencyOverlap).order_by(AggBrandAgencyOverlap.agency_count.desc()).limit(100)
    )
    return [row._mapping for row in result]


@router.post("/trigger")
async def trigger_aggregation():
    """Trigger a full aggregation rebuild. Runs in background."""
    import asyncio
    from compgraph.aggregation.orchestrator import AggregationOrchestrator

    orchestrator = AggregationOrchestrator()
    asyncio.create_task(orchestrator.run())
    return TriggerResponse(message="Aggregation rebuild started")
```

**Step 3: Register router in `src/compgraph/main.py`**

Add after existing router includes:
```python
from compgraph.api.routes.aggregation import router as aggregation_router
app.include_router(aggregation_router)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_api_aggregation.py -v
```

**Step 5: Commit**

```bash
git add src/compgraph/api/routes/aggregation.py src/compgraph/main.py tests/test_api_aggregation.py
git commit -m "feat: add read-only API endpoints for all 7 aggregation tables"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Phase 1** | 1-4 | Data cleanup: brand dedup, title normalization, location regex |
| **Phase 2** | 5-8 | Schema + seeding: location_mappings, markets, 3 new agg tables |
| **Phase 3** | 9-16 | Aggregation jobs: base framework + 7 rebuild jobs |
| **Phase 4** | 17-19 | Integration: orchestrator, scheduler wiring, API endpoints |

**Total: 19 tasks** across 4 phases. Phase 1 tasks are independent and can run in parallel. Phase 2 has dependencies (5 → 6 → 7). Phase 3 task 9 (base) blocks 10-16. Phase 4 task 17 blocks 18-19.

**Review gates:**
- After Phase 1: run `code-reviewer` to validate data cleanup approach
- After Phase 2: run integration test against live DB to verify market normalization
- After Phase 3: run `code-reviewer` + `pytest-validator` on all aggregation jobs
- After Phase 4: run `spec-reviewer` to validate M4 goal achievement
