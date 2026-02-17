# Bug Tracking Template for PR #84 Fixes

Copy these as individual GitHub issues to track fixes:

---

## Issue 1: Fix Migration Index Creation Syntax

**Title:** [BUG] Migration creates incorrect index in enrichment_runs table

**Labels:** bug, high-priority, database, migration

**Description:**

The migration in `alembic/versions/b52ab5ef6cf1_add_enrichment_runs_table.py` creates an index with incorrect syntax that will fail or create a broken index.

**Current Code (Line 54):**
```python
op.create_index(
    "ix_enrichment_runs_status_started",
    "enrichment_runs",
    ["status", sa.literal_column("started_at DESC")],
    unique=False,
)
```

**Issue:**
Using `sa.literal_column("started_at DESC")` treats "started_at DESC" as a literal SQL expression/column name instead of a descending index directive.

**Expected Behavior:**
Create a composite index on (status, started_at) with started_at in descending order.

**Fix:**
```python
op.create_index(
    "ix_enrichment_runs_status_started",
    "enrichment_runs",
    ["status", "started_at"],
    unique=False,
)
```

**Testing:**
- [ ] Run `alembic upgrade head` on test database
- [ ] Verify index is created successfully
- [ ] Check `\d enrichment_runs` in psql to verify index structure
- [ ] Run all tests

**Related:**
- PR #84
- Found in code review: PR84_CODE_REVIEW_FINDINGS.md

---

## Issue 2: Fix Counter Increment Logic in Enrichment Orchestrator

**Title:** [BUG] Counter increments fail due to incorrect SQLAlchemy values dict

**Labels:** bug, critical, enrichment, database

**Description:**

The `increment_enrichment_counter` function in `src/compgraph/enrichment/orchestrator.py` builds the update values dictionary incorrectly, causing counter increments to fail.

**Current Code (Lines 145-156):**
```python
values = {
    getattr(EnrichmentRunDB, k): getattr(EnrichmentRunDB, k) + v
    for k, v in counters.items()
    if v != 0
}
if not values:
    return
async with async_session_factory() as session:
    await session.execute(
        update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**values)
    )
    await session.commit()
```

**Issue:**
Using `getattr(EnrichmentRunDB, k)` as dict keys creates SQLAlchemy Column objects as keys, but `.values(**values)` expects string keys. This will cause:
- Counter updates to silently fail
- Or raise TypeError/SQLAlchemy errors
- Breaking enrichment run tracking

**Expected Behavior:**
Counter increments should atomically update the database counters (pass1_succeeded, pass1_failed, etc.)

**Fix:**
```python
values = {
    k: getattr(EnrichmentRunDB, k) + v  # Use string key, not Column object
    for k, v in counters.items()
    if v != 0
}
if not values:
    return
async with async_session_factory() as session:
    stmt = update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**values)
    await session.execute(stmt)
    await session.commit()
```

**Testing:**
- [ ] Create test that calls `increment_enrichment_counter`
- [ ] Verify database counters are actually incremented
- [ ] Test with multiple counter updates
- [ ] Verify atomic increment behavior
- [ ] Run integration tests for enrichment orchestrator

**Related:**
- PR #84
- Found in code review: PR84_CODE_REVIEW_FINDINGS.md

---

## Issue 3: Add updated_at Timestamp Handling to Counter Increments

**Title:** [BUG] updated_at timestamp not updated during counter increments

**Labels:** bug, medium-priority, database, enrichment

**Description:**

The `updated_at` column in `enrichment_runs` table is not updated when counters are incremented because raw UPDATE statements bypass SQLAlchemy's `onupdate` handling.

**Current Behavior:**
When `increment_enrichment_counter` is called:
1. Counter columns are updated (pass1_succeeded, etc.)
2. But `updated_at` timestamp remains unchanged
3. Makes it impossible to track when a run was last modified

**Root Cause:**
The model defines `onupdate=func.now()` in `src/compgraph/db/models.py:150-152`:
```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), 
    server_default=func.now(), 
    onupdate=func.now()  # Only works with ORM methods
)
```

But `onupdate` only works with ORM methods like `session.add()`, not with raw UPDATE statements.

**Expected Behavior:**
Every time counters are updated, `updated_at` should be set to the current timestamp.

**Fix:**
Add explicit timestamp update in `increment_enrichment_counter`:

```python
from datetime import UTC, datetime

async def increment_enrichment_counter(
    run_id: uuid.UUID,
    **counters: int,
) -> None:
    from sqlalchemy import update
    from compgraph.db.models import EnrichmentRunDB

    values = {
        k: getattr(EnrichmentRunDB, k) + v
        for k, v in counters.items()
        if v != 0
    }
    if not values:
        return
    
    # Always update the timestamp
    values["updated_at"] = datetime.now(UTC)  # ← Add this
    
    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**values)
        )
        await session.commit()
```

**Testing:**
- [ ] Create test that captures initial `updated_at` value
- [ ] Call `increment_enrichment_counter`
- [ ] Verify `updated_at` has changed to a later timestamp
- [ ] Ensure timestamp is in UTC
- [ ] Test with multiple increments

**Related:**
- PR #84
- Found in code review: PR84_CODE_REVIEW_FINDINGS.md

---

## All Fixes Checklist

Once all three issues are fixed:

- [ ] All 393 tests pass
- [ ] Migration runs successfully on clean database
- [ ] Counter increments work correctly
- [ ] Timestamps update properly
- [ ] Manual QA on dev server
- [ ] Monitor logs for SQLAlchemy errors
- [ ] Verify enrichment runs tracked end-to-end

**Then:** PR #84 is safe to merge
