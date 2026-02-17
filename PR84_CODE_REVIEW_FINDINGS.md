# Code Review Findings for PR #84

**Pull Request:** https://github.com/vaughnmakesthings/compgraph/pull/84  
**Title:** feat: unified pipeline monitoring + dashboard fixes (#68, #81-#83)  
**Reviewed:** 2026-02-17  
**Status:** ⚠️ **3 CRITICAL BUGS FOUND**

---

## Summary

I performed a comprehensive code review of PR #84 which adds:
- EnrichmentRunDB model + migration for persistent enrichment run tracking
- Enrichment orchestrator DB wiring with atomic counter increments
- Dashboard improvements and fixes
- Composite `/api/pipeline/status` endpoint

**Result:** Found 3 critical bugs that must be fixed before merging.

---

## 🐛 BUG 1: Incorrect Index Creation Syntax (HIGH SEVERITY)

### Location
`alembic/versions/b52ab5ef6cf1_add_enrichment_runs_table.py:52-56`

### Issue
The migration creates an index with incorrect syntax:

```python
op.create_index(
    "ix_enrichment_runs_status_started",
    "enrichment_runs",
    ["status", sa.literal_column("started_at DESC")],  # ❌ WRONG
    unique=False,
)
```

### Problem
Using `sa.literal_column("started_at DESC")` creates a **literal SQL expression as a column**, not a descending index on `started_at`. This will:
1. Likely **fail at migration time** with a SQL error
2. If it doesn't fail, create an incorrect/non-functional index
3. Not provide the intended performance optimization

The index will have:
- Column 1: `status`
- Column 2: A literal expression `started_at DESC` (treated as a column name, not a sort directive)

### Fix
Use standard column names and let PostgreSQL handle the sort order:

```python
op.create_index(
    "ix_enrichment_runs_status_started",
    "enrichment_runs",
    ["status", "started_at"],  # ✅ CORRECT
    unique=False,
)
```

Or if descending order is critical, use `postgresql_ops`:

```python
op.create_index(
    "ix_enrichment_runs_status_started",
    "enrichment_runs",
    ["status", "started_at"],
    postgresql_ops={"started_at": "DESC"}
)
```

### Testing
Run `alembic upgrade head` on a test database to verify the migration doesn't fail.

---

## 🐛 BUG 2: Incorrect Update Values Construction (HIGH SEVERITY)

### Location
`src/compgraph/enrichment/orchestrator.py:145-156`

### Issue
The `increment_enrichment_counter` function builds update values incorrectly:

```python
values = {
    getattr(EnrichmentRunDB, k): getattr(EnrichmentRunDB, k) + v  # ❌ WRONG
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

### Problem
This creates a dictionary with **SQLAlchemy Column objects as keys**:
```python
{
    <Column 'pass1_succeeded'>: <BinaryExpression pass1_succeeded + 1>,
    <Column 'pass1_failed'>: <BinaryExpression pass1_failed + 1>,
}
```

But SQLAlchemy's `.values(**values)` with the `**` operator expects **string keys**, not Column objects.

This will result in:
1. **Counter increments silently failing** (no updates to DB)
2. Or raising a `TypeError` or SQLAlchemy error
3. Breaking core enrichment run tracking functionality

### Fix
Use string keys instead of Column objects:

```python
values = {
    k: getattr(EnrichmentRunDB, k) + v  # ✅ CORRECT - k is already a string
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

### Testing
Test counter increments:
```python
await increment_enrichment_counter(run_id, pass1_succeeded=5, pass1_failed=2)
# Then verify the DB row was actually updated
```

---

## 🐛 BUG 3: Missing updated_at Handling (MEDIUM SEVERITY)

### Location
- Model: `src/compgraph/db/models.py:150-152`
- Usage: `src/compgraph/enrichment/orchestrator.py:137-172`

### Issue
The `EnrichmentRunDB` model defines automatic update timestamp:

```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), 
    server_default=func.now(), 
    onupdate=func.now()  # ⚠️ Only works with ORM methods
)
```

However, `onupdate=func.now()` **only works when**:
1. Using ORM methods like `session.add()` or `session.merge()`
2. Or when the column is explicitly included in UPDATE statements

### Problem
The `increment_enrichment_counter` function uses raw UPDATE statements:

```python
update(EnrichmentRunDB).where(...).values(**values)
```

This bypasses the ORM's `onupdate` handling, so `updated_at` will:
- **Never be updated** during counter increments
- Remain at the initial `created_at` value
- Make it impossible to track when a run was last modified

### Fix

**Option 1** (Recommended): Explicitly include `updated_at` in updates:

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
    values["updated_at"] = datetime.now(UTC)  # ✅ Add this
    
    async with async_session_factory() as session:
        await session.execute(
            update(EnrichmentRunDB).where(EnrichmentRunDB.id == run_id).values(**values)
        )
        await session.commit()
```

**Option 2**: Create a PostgreSQL trigger (more complex):

Add to migration:
```python
op.execute("""
    CREATE OR REPLACE FUNCTION update_enrichment_runs_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER enrichment_runs_updated_at_trigger
    BEFORE UPDATE ON enrichment_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_enrichment_runs_updated_at();
""")
```

### Testing
```python
# Before fix: updated_at stays the same
run_created_at = get_run_updated_at(run_id)
await increment_enrichment_counter(run_id, pass1_succeeded=1)
run_updated_at = get_run_updated_at(run_id)
assert run_updated_at > run_created_at  # Will FAIL without fix
```

---

## Additional Observations

### Minor Issues (Non-blocking)

1. **Line 154 in models.py**: The `__table_args__` index definition also uses `.desc()` but this is correct in the model definition context.

2. **Dashboard error handling**: The dashboard pages have good error handling with try-except blocks and user-friendly error messages.

3. **Code organization**: The separation of concerns between in-memory state (`_runs`) and DB persistence is clear and well-documented.

### Good Practices Observed

✅ Proper use of `async with` for session management  
✅ Good error logging in orchestrator  
✅ Consistent use of UUID for primary keys  
✅ Atomic counter increments (intent is correct, just implementation bug)  
✅ Comprehensive test coverage mentioned (393 tests)  
✅ Good docstrings explaining complex logic  

---

## Recommended Action Plan

### Before Merging
1. ✅ Fix BUG 1: Update migration index creation
2. ✅ Fix BUG 2: Fix `increment_enrichment_counter` values dict
3. ✅ Fix BUG 3: Add `updated_at` handling to counter increments
4. ✅ Test migration: `alembic upgrade head` on clean DB
5. ✅ Test counter increments with actual DB
6. ✅ Verify enrichment runs are tracked correctly end-to-end

### After Fixes
1. Re-run all 393 tests
2. Manual QA on dev server
3. Verify dashboard shows correct run metrics
4. Monitor logs for any SQLAlchemy errors

---

## Severity Summary

| Bug | Severity | Impact | Likelihood |
|-----|----------|--------|------------|
| BUG 1 | **HIGH** | Migration failure or broken index | Very High |
| BUG 2 | **HIGH** | Counter tracking completely broken | Very High |
| BUG 3 | **MEDIUM** | Timestamp tracking inconsistent | High |

**Overall Risk:** **HIGH** - Two high-severity bugs will prevent core functionality from working.

---

## Conclusion

This PR adds valuable monitoring and observability features, but has **3 critical bugs** that must be fixed before merging. The bugs are straightforward to fix and the fixes are clearly documented above.

Once fixed, this will be a solid addition to the codebase. The architecture is sound, the code is well-organized, and the test coverage is good.

**Recommendation:** ❌ **DO NOT MERGE** until bugs are fixed and verified.

---

*Review conducted by: Claude (Copilot Code Review Agent)*  
*Date: 2026-02-17*
