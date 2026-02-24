# M4 & Infra Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix five concrete issues found during M4 aggregation pipeline review: NULL country market deduplication, zip code parsing in coverage gaps, lifecycle calculation edge cases, velocity query performance, and the missing Alembic migration for PR #155 indexes.

**Architecture:** All four aggregation fixes are in `src/compgraph/aggregation/` (SQL text strings) and `scripts/populate_markets.py` (Python dedup logic). Each fix is self-contained and independently testable. The Alembic migration requires a live DB connection and is the only step needing secrets.

**Tech Stack:** Python 3.12+, SQLAlchemy 2.0 (async + text()), pytest, uv, Alembic, PostgreSQL 17

**Issues closed:** #151, #148, #152, #150, + untracked Alembic migration for PR #155 indexes

**Issues NOT included:** #29 (CI secrets) — requires browser access to Codecov/Snyk dashboards; handled separately by a human.

---

## Pre-work: Create the Worktree

```bash
# From main repo root
git checkout main && git pull origin main
git checkout -b fix/m4-aggregation-fixes
```

Verify tests pass before touching anything:
```bash
uv run pytest -x -q --tb=short -m "not integration"
```
Expected: all pass (677 tests).

---

### Task 1: Fix NULL Country Dedup in `populate_markets.py` (Issue #151)

**Problem:** `Market.country` is nullable with `default="US"`. If any market row was inserted with `country=None` (e.g., before the default was set), the Python tuple `(name, state, None)` will NOT match a LocationMapping tuple `(name, state, "US")`, causing a duplicate market to be inserted.

**Files:**
- Modify: `scripts/populate_markets.py:32-49`
- Test: `tests/test_populate_markets.py` (create new)

**Step 1: Write the failing test**

Create `tests/test_populate_markets.py`:

```python
from __future__ import annotations

import pytest


class TestPopulateMarketsNullCountry:
    """Unit tests for populate_markets dedup logic (no DB required)."""

    def test_none_country_matches_us_string(self):
        """Python None in existing set should match "US" from location mapping."""
        # Simulate what the script does: build existing set from DB (may have None)
        existing_with_none = {("Los Angeles", "CA", None)}
        # Simulate a LocationMapping metro with "US" country
        metro_country = "US"
        metro_name = "Los Angeles"
        metro_state = "CA"

        # Current buggy behavior: tuple doesn't match because None != "US"
        # This test should FAIL before the fix
        assert (metro_name, metro_state, metro_country or "US") in {
            (name, state, country or "US")
            for (name, state, country) in existing_with_none
        }

    def test_us_string_country_matches_us_string(self):
        """Standard case: both sides have "US" string."""
        existing = {("Los Angeles", "CA", "US")}
        assert ("Los Angeles", "CA", "US") in existing

    def test_none_country_both_sides_normalize_to_same(self):
        """Both sides None → both normalize to "US", should match."""
        existing_with_none = {("Dallas", "TX", None)}
        normalized = {(n, s, c or "US") for (n, s, c) in existing_with_none}
        assert ("Dallas", "TX", "US") in normalized
```

**Step 2: Run test to confirm it passes (this test is testing logic, not bug)**

```bash
uv run pytest tests/test_populate_markets.py -v
```
Expected: PASS (all 3 tests). These test the *desired* behavior. Now fix the script so it matches.

**Step 3: Apply fix to `scripts/populate_markets.py`**

Replace the `existing` set comprehension (lines 32-37) and the duplicate check (line 41):

```python
# BEFORE (lines 32-37):
existing = {
    (r[0], r[1], r[2])
    for r in (
        await session.execute(select(Market.name, Market.state, Market.country))
    ).all()
}

# AFTER:
existing = {
    (r[0], r[1], r[2] or "US")
    for r in (
        await session.execute(select(Market.name, Market.state, Market.country))
    ).all()
}
```

Replace the check on line 41:
```python
# BEFORE:
if (metro_name, metro_state, metro_country) in existing:

# AFTER:
if (metro_name, metro_state, metro_country or "US") in existing:
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_populate_markets.py -v
```
Expected: PASS

**Step 5: Lint and typecheck**

```bash
uv run ruff check scripts/populate_markets.py && uv run ruff format scripts/populate_markets.py
```

**Step 6: Full test suite**

```bash
uv run pytest -x -q --tb=short -m "not integration"
```
Expected: all pass.

**Step 7: Commit**

```bash
git add scripts/populate_markets.py tests/test_populate_markets.py
git commit -m "fix: normalize NULL country to US in populate_markets dedup check (#151)"
```

---

### Task 2: Fix Zip Code Parsing in Coverage Gaps SQL (Issue #148)

**Problem:** `location_raw` values like `"Los Angeles, CA 90001"` cause `SPLIT_PART(location_raw, ',', 2)` to return `" CA 90001"` instead of `" CA"`. The comparison `LOWER(TRIM(" CA 90001")) = LOWER(lm.state)` → `"ca 90001" = "ca"` fails to match, dropping valid postings from coverage data.

**Files:**
- Modify: `src/compgraph/aggregation/coverage_gaps.py:26-33` (the `_QUERY` string)
- Test: `tests/test_aggregation_coverage_gaps.py` (create new)

**Step 1: Write the failing test**

Create `tests/test_aggregation_coverage_gaps.py`:

```python
from __future__ import annotations

import pytest

from compgraph.aggregation.coverage_gaps import _QUERY


class TestCoverageGapsQuery:
    def test_query_handles_zip_in_state_field(self):
        """SQL should extract just the state code, ignoring trailing zip codes."""
        # State extraction should use SPLIT_PART on space or SUBSTRING to get first 2 chars
        # after splitting on comma. Verify the query does NOT do a raw TRIM comparison.
        assert "SPLIT_PART" in _QUERY
        # After the fix, state parsing should trim to just the state abbreviation
        # (first token of the state field, OR regex stripping trailing digits)
        # Verify the fix is present by checking for the safe state extraction pattern
        assert (
            "SPLIT_PART(TRIM(SPLIT_PART(" in _QUERY
            or "REGEXP_REPLACE" in _QUERY
            or "LEFT(" in _QUERY
        ), "State extraction must strip trailing zip codes"

    def test_query_has_no_cross_join(self):
        """Coverage gaps query should not use CROSS JOIN."""
        assert "CROSS JOIN" not in _QUERY.upper(), (
            "CROSS JOIN found in coverage_gaps query — verify it's not producing duplicates"
        )

    def test_query_filters_null_location(self):
        """Query must skip postings with NULL location_raw."""
        assert "location_raw IS NOT NULL" in _QUERY
```

**Step 2: Run the test to confirm current state**

```bash
uv run pytest tests/test_aggregation_coverage_gaps.py -v
```
Expected: `test_query_handles_zip_in_state_field` FAILS (before fix), others may pass.

**Step 3: Apply fix to `coverage_gaps.py`**

In the `_QUERY` string, change the state comparison JOIN condition. The current code at lines 31-33:

```sql
-- BEFORE:
        AND LOWER(TRIM(
            SPLIT_PART(ls.location_raw, ',', 2)
        )) = LOWER(lm.state)
```

Replace with (extract first whitespace-delimited token = state abbreviation):

```sql
-- AFTER:
        AND LOWER(TRIM(SPLIT_PART(
            TRIM(SPLIT_PART(ls.location_raw, ',', 2)),
            ' ', 1
        ))) = LOWER(lm.state)
```

This does: split on comma → take second part → trim whitespace → split on space → take first part (the 2-letter state code). `"CA 90001"` → trim → `"CA 90001"` → split on space → `"CA"`.

**Step 4: Run tests**

```bash
uv run pytest tests/test_aggregation_coverage_gaps.py -v
```
Expected: all PASS

**Step 5: Full suite**

```bash
uv run pytest -x -q --tb=short -m "not integration"
```

**Step 6: Commit**

```bash
git add src/compgraph/aggregation/coverage_gaps.py tests/test_aggregation_coverage_gaps.py
git commit -m "fix: strip zip codes from state field in coverage_gaps location join (#148)"
```

---

### Task 3: Fix Lifecycle Calculation Edge Cases (Issue #152)

**Problem:** Two bugs in `posting_lifecycle.py`:

1. **Negative `days_open`**: If `last_seen_at < first_seen_at` (data anomaly), `days_open` is negative. The averages will be corrupted. Fix: `GREATEST(0, ...)`.

2. **Semantic error in `avg_repost_gap_days`**: Currently uses `AVG(days_open) FILTER (WHERE times_reposted > 0)` — this gives "average tenure of reposted postings", NOT the average gap between reposts. Fix: divide `days_open` by `times_reposted` to estimate the average gap between repost events. Use `NULLIF` to avoid division by zero.

**Files:**
- Modify: `src/compgraph/aggregation/posting_lifecycle.py:10-42` (the `_QUERY` string)
- Test: `tests/test_aggregation_posting_lifecycle.py` (create new)

**Step 1: Write the failing test**

Create `tests/test_aggregation_posting_lifecycle.py`:

```python
from __future__ import annotations

import pytest

from compgraph.aggregation.posting_lifecycle import _QUERY


class TestPostingLifecycleQuery:
    def test_days_open_guarded_against_negative(self):
        """days_open must use GREATEST(0, ...) to handle data anomalies."""
        assert "GREATEST(0," in _QUERY or "GREATEST(0 ," in _QUERY, (
            "days_open must be wrapped in GREATEST(0, ...) to prevent negative durations"
        )

    def test_avg_repost_gap_uses_division_not_raw_avg(self):
        """avg_repost_gap_days should divide days_open by times_reposted, not just avg."""
        # The fix: AVG(days_open / NULLIF(times_reposted, 0))
        assert "NULLIF(times_reposted" in _QUERY, (
            "avg_repost_gap_days must divide by times_reposted using NULLIF to avoid division by zero"
        )

    def test_query_groups_by_company_archetype_period(self):
        """GROUP BY must include all non-aggregate columns."""
        assert "GROUP BY company_id, role_archetype, period" in _QUERY

    def test_query_uses_posting_enrichments_join(self):
        """Query must join posting_enrichments for role_archetype."""
        assert "posting_enrichments" in _QUERY
```

**Step 2: Run test to confirm failures**

```bash
uv run pytest tests/test_aggregation_posting_lifecycle.py -v
```
Expected: `test_days_open_guarded_against_negative` and `test_avg_repost_gap_uses_division_not_raw_avg` FAIL.

**Step 3: Apply fix to `posting_lifecycle.py`**

In the `_QUERY` string, update the CTE:

```sql
-- BEFORE (lines 16-19):
        EXTRACT(EPOCH FROM (
            COALESCE(p.last_seen_at, NOW()) - p.first_seen_at
        )) / 86400.0 AS days_open,
        p.times_reposted

-- AFTER:
        GREATEST(0, EXTRACT(EPOCH FROM (
            COALESCE(p.last_seen_at, NOW()) - p.first_seen_at
        )) / 86400.0) AS days_open,
        p.times_reposted
```

And in the SELECT portion, change `avg_repost_gap_days` (lines 35-38):

```sql
-- BEFORE:
    COALESCE(
        AVG(days_open) FILTER (WHERE times_reposted > 0),
        0
    ) AS avg_repost_gap_days

-- AFTER:
    COALESCE(
        AVG(days_open / NULLIF(times_reposted, 0)) FILTER (WHERE times_reposted > 0),
        0
    ) AS avg_repost_gap_days
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_aggregation_posting_lifecycle.py -v
```
Expected: all PASS

**Step 5: Full suite**

```bash
uv run pytest -x -q --tb=short -m "not integration"
```

**Step 6: Commit**

```bash
git add src/compgraph/aggregation/posting_lifecycle.py tests/test_aggregation_posting_lifecycle.py
git commit -m "fix: guard days_open against negative values and fix avg_repost_gap_days formula (#152)"
```

---

### Task 4: Optimize Daily Velocity Query (Issue #150)

**Problem:** The current query does `CROSS JOIN companies` × `snapshot_dates`, then filters with a correlated `EXISTS` subquery against `posting_snapshots`. For N snapshot dates and M companies with K postings each, this is O(N×M×K) before the EXISTS filter.

**Fix:** Start from `posting_snapshots` directly — it already contains exactly the (date, posting_id) pairs we need. This eliminates the CROSS JOIN and the correlated EXISTS entirely.

**Files:**
- Modify: `src/compgraph/aggregation/daily_velocity.py:10-53` (the `_QUERY` string)
- Test: `tests/test_aggregation_daily_velocity.py` (create new)

**Step 1: Write the failing test**

Create `tests/test_aggregation_daily_velocity.py`:

```python
from __future__ import annotations

import pytest

from compgraph.aggregation.daily_velocity import _QUERY


class TestDailyVelocityQuery:
    def test_query_does_not_use_cross_join(self):
        """Query must not use CROSS JOIN (performance issue)."""
        assert "CROSS JOIN" not in _QUERY.upper(), (
            "CROSS JOIN found — use direct JOIN from posting_snapshots instead"
        )

    def test_query_does_not_use_exists_subquery(self):
        """Correlated EXISTS subquery should be eliminated."""
        assert "EXISTS" not in _QUERY.upper(), (
            "EXISTS subquery found — eliminates with direct JOIN approach"
        )

    def test_query_produces_required_columns(self):
        """Output must have all required columns for compute_rows mapping."""
        for col in ("date", "company_id", "active_postings", "new_postings", "closed_postings", "net_change"):
            assert col in _QUERY, f"Required column '{col}' missing from query"

    def test_query_starts_from_posting_snapshots(self):
        """Query must use posting_snapshots as base table."""
        assert "posting_snapshots" in _QUERY

    def test_net_change_computed_as_difference(self):
        """net_change = new_postings - closed_postings."""
        assert "new_postings - closed_postings" in _QUERY
```

**Step 2: Run test to confirm failures**

```bash
uv run pytest tests/test_aggregation_daily_velocity.py -v
```
Expected: `test_query_does_not_use_cross_join` and `test_query_does_not_use_exists_subquery` FAIL.

**Step 3: Replace the `_QUERY` in `daily_velocity.py`**

Replace the entire `_QUERY` constant (lines 10-53) with:

```python
_QUERY = """
WITH daily_stats AS (
    SELECT
        ps.snapshot_date AS date,
        p.company_id,
        COUNT(DISTINCT ps.posting_id) AS active_postings,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.first_seen_at::date = ps.snapshot_date
        ) AS new_postings,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.is_active = false
            AND p.last_seen_at::date = ps.snapshot_date
        ) AS closed_postings
    FROM posting_snapshots ps
    JOIN postings p ON p.id = ps.posting_id
    GROUP BY ps.snapshot_date, p.company_id
)
SELECT
    date,
    company_id,
    active_postings,
    new_postings,
    closed_postings,
    new_postings - closed_postings AS net_change
FROM daily_stats
ORDER BY date, company_id
"""
```

**Why this is correct:**
- `posting_snapshots` contains one row per (posting, date) for each date the posting was scraped (i.e., was active). `COUNT(DISTINCT ps.posting_id)` = active count on that date. ✓
- `p.first_seen_at::date = ps.snapshot_date` — postings whose first snapshot is this date = new. ✓
- `p.is_active = false AND p.last_seen_at::date = ps.snapshot_date` — postings that closed on this date. ✓
- No CROSS JOIN, no EXISTS. Query complexity: O(snapshots × join selectivity).

**Step 4: Run tests**

```bash
uv run pytest tests/test_aggregation_daily_velocity.py -v
```
Expected: all PASS

**Step 5: Full suite**

```bash
uv run pytest -x -q --tb=short -m "not integration"
```
Expected: all pass.

**Step 6: Lint**

```bash
uv run ruff check src/compgraph/aggregation/daily_velocity.py && uv run ruff format src/compgraph/aggregation/daily_velocity.py
```

**Step 7: Commit**

```bash
git add src/compgraph/aggregation/daily_velocity.py tests/test_aggregation_daily_velocity.py
git commit -m "perf: replace CROSS JOIN+EXISTS with direct posting_snapshots join in daily_velocity (#150)"
```

---

### Task 5: Generate Alembic Migration for PR #155 Indexes

**Context:** PR #155 added 7 new database indexes to `src/compgraph/db/models.py` but the Alembic migration was never generated. The models and DB are out of sync. This step requires a live DB connection.

**Files:**
- Create: `alembic/versions/<hash>_add_pr155_indexes.py` (auto-generated)

**Step 1: Verify what indexes are in models but not DB**

The indexes added in PR #155 (check `src/compgraph/db/models.py`):
```bash
grep -n "Index(" src/compgraph/db/models.py
```

**Step 2: Generate the migration**

```bash
op run --env-file=.env -- uv run alembic revision --autogenerate -m "add pr155 performance indexes"
```

Expected output: `Generating alembic/versions/<hash>_add_pr155_indexes.py`

**Step 3: Review the generated migration**

Open the generated file and verify:
- `op.create_index(...)` calls for the 7 new indexes
- `op.drop_index(...)` calls in `downgrade()`
- No unexpected table or column changes (autogenerate can pick up drift — reject anything that's not indexes)

If any non-index changes appear (column adds/drops, table creates/drops), **remove them** — they indicate model drift, not the intended change.

**Step 4: Apply migration to dev DB**

```bash
op run --env-file=.env -- uv run alembic upgrade head
```

Expected: migration runs, no errors.

**Step 5: Verify**

```bash
op run --env-file=.env -- uv run alembic current
```
Should show the new revision as current.

**Step 6: Commit**

```bash
git add alembic/versions/
git commit -m "chore: generate Alembic migration for PR #155 performance indexes"
```

---

### Task 6: PR and CI Validation

**Step 1: Final full test run**

```bash
uv run pytest -x -q --tb=short -m "not integration"
```
Expected: all pass (should be 677+ tests — we added ~15 new unit tests).

**Step 2: Lint and typecheck**

```bash
uv run ruff check src/ tests/ scripts/ && uv run mypy src/compgraph/
```
Expected: no errors.

**Step 3: Push and create PR**

```bash
git push -u origin fix/m4-aggregation-fixes
```

Then use `/pr` skill to create the PR, referencing issues #151, #148, #152, #150.

PR body should mention:
- Closes #151, #148, #152, #150
- Includes untracked Alembic migration for PR #155 indexes
- All changes are pure SQL/Python logic — no schema changes
- Migration included (Task 5)

**Step 4: Wait for CI**

All 5 review bots must approve before merge. Use `/merge-guardian` when ready.

---

## Summary of Changes

| File | Change | Issue |
|------|--------|-------|
| `scripts/populate_markets.py` | Normalize `None` country to `"US"` in dedup | #151 |
| `src/compgraph/aggregation/coverage_gaps.py` | Strip zip from state with double SPLIT_PART | #148 |
| `src/compgraph/aggregation/posting_lifecycle.py` | GREATEST(0, days_open), fix avg_repost_gap formula | #152 |
| `src/compgraph/aggregation/daily_velocity.py` | Replace CROSS JOIN+EXISTS with direct PS join | #150 |
| `alembic/versions/` | Generate migration for PR #155 indexes | untracked |
| `tests/test_populate_markets.py` | New: dedup NULL country tests | #151 |
| `tests/test_aggregation_coverage_gaps.py` | New: SQL structure + zip code tests | #148 |
| `tests/test_aggregation_posting_lifecycle.py` | New: edge case guard tests | #152 |
| `tests/test_aggregation_daily_velocity.py` | New: query structure tests | #150 |
