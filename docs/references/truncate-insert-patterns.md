# PostgreSQL Truncate+Insert Rebuild Patterns

Research reference for CompGraph aggregation table rebuilds. Covers lock behavior,
concurrent read safety, SQLAlchemy 2.0 async implementation, and error recovery.

**CompGraph context:** 4 aggregation tables (`agg_daily_velocity`, `agg_brand_timeline`,
`agg_pay_benchmarks`, `agg_posting_lifecycle`) are rebuilt from source data on a schedule
(APScheduler cron). Dashboard queries read these tables concurrently. Stack: SQLAlchemy 2.0
async + asyncpg on Supabase Postgres 17.

---

## §1 Lock Behavior

### TRUNCATE acquires ACCESS EXCLUSIVE

`TRUNCATE` acquires an **ACCESS EXCLUSIVE** lock on every table it touches. This is the
most restrictive lock mode in PostgreSQL — it conflicts with **all** other lock modes,
including `ACCESS SHARE` (the lock acquired by plain `SELECT`).

**What this means in practice:**

| Operation | Blocked by TRUNCATE? |
|-----------|---------------------|
| `SELECT` (dashboard reads) | Yes |
| `INSERT` / `UPDATE` / `DELETE` | Yes |
| `CREATE INDEX` | Yes |
| Other DDL (`ALTER TABLE`, etc.) | Yes |

### How long the lock is held

The ACCESS EXCLUSIVE lock is held **for the entire duration of the transaction** containing
the TRUNCATE. There is no `UNLOCK TABLE` command — locks are only released at transaction
end (COMMIT or ROLLBACK).

This means:
- **Short transaction** (TRUNCATE only): lock held for milliseconds (TRUNCATE itself is
  near-instant since it does not scan rows).
- **Long transaction** (TRUNCATE + bulk INSERT in same transaction): lock held for the
  **entire duration of the insert**, which could be seconds or minutes depending on data
  volume. All dashboard `SELECT` queries queue behind this lock.

### Impact on CompGraph dashboard

With ~4 aggregation tables at < 100K rows each, a TRUNCATE+INSERT cycle takes roughly
1–5 seconds per table. During that window, any Streamlit dashboard query hitting that
specific agg table will block until the transaction commits. Queries against *other* tables
are unaffected.

---

## §2 Transaction Isolation Strategies

### Option A: TRUNCATE + INSERT in single transaction (simple, blocks readers)

```sql
BEGIN;
TRUNCATE agg_daily_velocity;
INSERT INTO agg_daily_velocity (...) SELECT ... FROM postings ...;
COMMIT;
```

**Pros:**
- Simplest pattern. Atomic — readers see either all-old or all-new data, never partial.
- If INSERT fails, TRUNCATE is rolled back automatically. Table returns to previous state.
- No cleanup needed (no temp tables, no renames).

**Cons:**
- Blocks all readers for the duration of TRUNCATE + INSERT (seconds for small tables).
- Not MVCC-safe: concurrent transactions that started *before* the TRUNCATE will see an
  empty table if they access it *after* the TRUNCATE commits (within READ COMMITTED, each
  statement gets a fresh snapshot, so this mainly affects long-running transactions in
  REPEATABLE READ).

**When to use:** Table sizes < 100K rows, rebuild takes < 5 seconds, brief dashboard
interruptions are acceptable.

### Option B: Write to staging table, then swap via RENAME (zero-downtime)

```sql
BEGIN;
-- Build new data in a staging table
CREATE TABLE agg_daily_velocity_new (LIKE agg_daily_velocity INCLUDING ALL);
INSERT INTO agg_daily_velocity_new (...) SELECT ... FROM postings ...;

-- Atomic swap (still takes ACCESS EXCLUSIVE, but only for the instant of rename)
ALTER TABLE agg_daily_velocity RENAME TO agg_daily_velocity_old;
ALTER TABLE agg_daily_velocity_new RENAME TO agg_daily_velocity;
DROP TABLE agg_daily_velocity_old;
COMMIT;
```

**Pros:**
- Readers are blocked only for the duration of the RENAME (microseconds), not the INSERT.
- INSERT happens against a staging table that no one is reading.

**Cons:**
- More complex: must replicate all indexes, constraints, grants, and foreign keys on the
  staging table. `LIKE ... INCLUDING ALL` handles indexes and constraints but **not**
  foreign keys from other tables pointing *to* this table, nor grants.
- Alembic migrations that reference the table by OID may break if the table is swapped
  mid-migration.
- Sequences (`RESTART IDENTITY`) need careful handling.
- Foreign keys from other tables referencing the agg table would need to be dropped and
  recreated.

**When to use:** Large tables (> 1M rows), rebuilds taking > 30 seconds, zero-downtime
requirements.

### Option C: DELETE + INSERT (row-level locks, less blocking)

```sql
BEGIN;
DELETE FROM agg_daily_velocity;
INSERT INTO agg_daily_velocity (...) SELECT ... FROM postings ...;
COMMIT;
```

**Pros:**
- DELETE acquires `ROW EXCLUSIVE` lock, which does **not** block concurrent `SELECT`.
  Readers see the old data until COMMIT (MVCC-safe).
- No table-level exclusive lock — dashboard reads continue uninterrupted.

**Cons:**
- Slower than TRUNCATE: DELETE scans and marks each row individually. For 100K rows this
  is still fast (< 1 second), but for millions of rows it becomes significant.
- Dead tuples accumulate — requires `VACUUM` to reclaim space (autovacuum handles this,
  but there's a lag).
- During the transaction, the table contains both dead (deleted) and new (inserted) rows,
  consuming more disk temporarily.

**When to use:** When concurrent read availability is critical and table sizes are moderate.

### Option D: DELETE + INSERT per-company (narrowest locks, incremental)

```sql
BEGIN;
DELETE FROM agg_daily_velocity WHERE company_id = :company_id;
INSERT INTO agg_daily_velocity (...) SELECT ... FROM postings WHERE company_id = :company_id;
COMMIT;
```

**Pros:**
- Only locks rows for one company at a time. Queries for other companies are unaffected.
- Smallest possible transaction window.
- Can be parallelized across companies.

**Cons:**
- More complex orchestration. Must handle partial failures (some companies rebuilt, others
  not).
- Still accumulates dead tuples.

### Recommendation for CompGraph

**Use Option A (TRUNCATE + INSERT in single transaction)** for the initial implementation.

Rationale:
1. Table sizes are small (< 100K rows). Rebuild takes 1–5 seconds.
2. Dashboard is internal-only (Mosaic staff), not customer-facing. Brief blocking is
   acceptable.
3. Atomic rollback on failure is critical — we must never leave an agg table empty.
4. Simplicity matches the team's capacity and the project's maturity.
5. Pre-commitment in `docs/design.md`: "Aggregation = truncate+insert."

**Upgrade path:** If table sizes grow past 500K rows or dashboard becomes customer-facing,
migrate to Option C (DELETE + INSERT) for MVCC-safe concurrent reads, or Option B (table
swap) for zero-downtime.

---

## §3 SQLAlchemy 2.0 Async Implementation

### Core pattern: TRUNCATE + bulk INSERT with async session

```python
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import AggDailyVelocity


async def rebuild_daily_velocity(session: AsyncSession) -> int:
    """Rebuild agg_daily_velocity from source data.

    Runs TRUNCATE + INSERT in a single transaction.
    Returns the number of rows inserted.
    """
    # TRUNCATE via raw SQL — no ORM equivalent exists
    await session.execute(text("TRUNCATE agg_daily_velocity"))

    # Build aggregation query (example — real query would join postings + companies)
    agg_query = text("""
        SELECT
            gen_random_uuid() AS id,
            p.scraped_at::date AS date,
            p.company_id,
            COUNT(*) AS new_postings,
            COUNT(*) FILTER (WHERE ps.status = 'closed') AS closed_postings,
            COUNT(*) AS net_change
        FROM postings p
        JOIN posting_snapshots ps ON ps.posting_id = p.id
        GROUP BY p.scraped_at::date, p.company_id
    """)

    # INSERT ... SELECT in one round-trip (most efficient)
    await session.execute(text(f"""
        INSERT INTO agg_daily_velocity (id, date, company_id, new_postings, closed_postings, net_change)
        {agg_query.text}
    """))

    # Get row count
    result = await session.execute(text("SELECT COUNT(*) FROM agg_daily_velocity"))
    count = result.scalar_one()

    return count
```

### Transaction boundaries

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def run_aggregation(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Run all 4 aggregation rebuilds in separate transactions."""

    # Each table gets its own transaction — failure in one doesn't affect others
    for rebuild_fn in [
        rebuild_daily_velocity,
        rebuild_brand_timeline,
        rebuild_pay_benchmarks,
        rebuild_posting_lifecycle,
    ]:
        async with session_factory() as session:
            async with session.begin():
                count = await rebuild_fn(session)
                # session.begin() auto-commits on exit, auto-rolls-back on exception
                logger.info(f"{rebuild_fn.__name__}: {count} rows")
```

### Using `session.execute(text(...))` vs ORM operations

**Use raw SQL `text()` for TRUNCATE** — there is no ORM-level TRUNCATE command in
SQLAlchemy. The ORM's `delete()` construct maps to SQL DELETE, not TRUNCATE.

```python
# TRUNCATE — must use text()
await session.execute(text("TRUNCATE agg_daily_velocity"))

# DELETE — can use ORM construct (but slower for full-table wipe)
from sqlalchemy import delete
await session.execute(delete(AggDailyVelocity))
```

**Use `INSERT ... SELECT` via `text()` for best performance** — avoids round-tripping
data through Python. The database does all the work server-side.

```python
# Best: INSERT ... SELECT (server-side, one round-trip)
await session.execute(text("""
    INSERT INTO agg_daily_velocity (id, date, company_id, ...)
    SELECT gen_random_uuid(), ...
    FROM postings ...
"""))

# Acceptable: bulk insert from Python dicts (when data needs Python processing)
from sqlalchemy import insert
rows = [{"id": uuid4(), "date": d, "company_id": cid, ...} for ...]
await session.execute(insert(AggDailyVelocity), rows)

# Avoid: session.add_all() for bulk operations (issues individual INSERTs pre-2.0,
# batched in 2.0 but still slower than execute(insert(...), rows))
```

### Bulk insert with dictionaries

When aggregation logic requires Python processing (not pure SQL), use the `insert()`
construct with a list of dictionaries:

```python
from uuid import uuid4
from sqlalchemy import insert
from compgraph.db.models import AggPayBenchmarks


async def rebuild_pay_benchmarks(session: AsyncSession) -> int:
    await session.execute(text("TRUNCATE agg_pay_benchmarks"))

    # Fetch source data
    result = await session.execute(text("""
        SELECT company_id, role_category, pay_type,
               pay_min, pay_max
        FROM posting_enrichments
        WHERE pay_min IS NOT NULL
    """))
    rows = result.fetchall()

    # Process in Python (e.g., statistical aggregation)
    benchmarks = compute_benchmarks(rows)  # returns list of dicts

    # Bulk insert — SQLAlchemy 2.0 batches this efficiently
    if benchmarks:
        await session.execute(insert(AggPayBenchmarks), benchmarks)

    return len(benchmarks)
```

### Batch sizing for very large inserts

For tables with > 100K rows, batch the insert to avoid memory pressure:

```python
BATCH_SIZE = 5000

async def bulk_insert_batched(
    session: AsyncSession,
    model: type,
    rows: list[dict],
) -> None:
    """Insert rows in batches to limit memory usage."""
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        await session.execute(insert(model), batch)
    # All batches are in the same transaction — commit happens at session.begin() exit
```

---

## §4 Concurrent Read Safety

### How PostgreSQL MVCC handles reads during rebuild

PostgreSQL uses **Multi-Version Concurrency Control (MVCC)**: each transaction sees a
consistent snapshot of the database. Readers never block writers, and writers never block
readers — *except* when ACCESS EXCLUSIVE locks are involved.

**TRUNCATE breaks the MVCC contract.** The PostgreSQL docs explicitly state:

> TRUNCATE is not MVCC-safe. After truncation, the table will appear empty to concurrent
> transactions, if they are using a snapshot taken before the truncation occurred.

This means TRUNCATE operates at the physical storage level (it replaces the table's file
node), bypassing the normal row-versioning mechanism.

### READ COMMITTED (Supabase default) implications

In READ COMMITTED (PostgreSQL's and Supabase's default isolation level):

- Each **statement** (not transaction) gets a fresh snapshot.
- A `SELECT` that starts *after* TRUNCATE+INSERT commits will see the new data.
- A `SELECT` that starts *during* the TRUNCATE+INSERT transaction will **block** (wait for
  the ACCESS EXCLUSIVE lock to release), then see the new data.
- A `SELECT` already in progress when TRUNCATE starts will **also block** on the next
  statement if it touches the truncated table.

**Bottom line for CompGraph:** Dashboard queries will briefly queue (1–5 seconds) during
rebuild, then see fresh data. They will **never** see an empty table or partial results.

### REPEATABLE READ implications

If a dashboard session used REPEATABLE READ:

- The snapshot is taken at the start of the *transaction*, not each statement.
- A long-running REPEATABLE READ transaction that started before the rebuild would see
  stale data — but this is expected behavior, not a bug.
- CompGraph uses READ COMMITTED (the default), so this is not a concern.

### Will dashboard queries see partial results?

**No.** Because TRUNCATE + INSERT runs in a single transaction:

1. The ACCESS EXCLUSIVE lock prevents any `SELECT` from reading the table until the
   transaction commits.
2. When the lock releases (on COMMIT), all rows from the INSERT are visible atomically.
3. If the INSERT fails and the transaction rolls back, the old data is preserved (TRUNCATE
   is transaction-safe).

This is the strongest guarantee: **all-old or all-new, never partial.**

---

## §5 Error Recovery

### Transaction rollback on INSERT failure

If the INSERT fails after TRUNCATE within the same transaction, PostgreSQL **automatically
rolls back the entire transaction**, including the TRUNCATE. The table returns to its
pre-TRUNCATE state with all original data intact.

```python
async with session_factory() as session:
    async with session.begin():
        await session.execute(text("TRUNCATE agg_daily_velocity"))
        # If this raises, session.begin() context manager catches it
        # and issues ROLLBACK — the TRUNCATE is undone.
        await session.execute(text("""
            INSERT INTO agg_daily_velocity (...)
            SELECT ... FROM postings ...
        """))
    # Reaching here means COMMIT succeeded
```

**Key guarantee:** TRUNCATE is transaction-safe. If the transaction does not commit, the
truncation has no effect. The old data remains.

### What CAN go wrong

| Failure | Impact | Recovery |
|---------|--------|----------|
| INSERT syntax error | Transaction rolls back, old data preserved | Fix query, re-run |
| Connection drop mid-transaction | PostgreSQL auto-rollbacks, old data preserved | Re-run |
| Out of disk space during INSERT | Transaction rolls back, old data preserved | Free space, re-run |
| Application crash after COMMIT | New data is committed and durable | No action needed |
| Partial INSERT (e.g., batch 3 of 5 fails) | Entire transaction rolls back (all batches) | Fix issue, re-run |

### Idempotency

TRUNCATE+INSERT is **inherently idempotent**: running it twice produces the same result
(the table contains the current aggregation of source data). This makes it safe to retry
on failure without any deduplication logic.

### Monitoring pattern

```python
import time
import logging

logger = logging.getLogger(__name__)


async def rebuild_with_monitoring(
    session_factory: async_sessionmaker[AsyncSession],
    name: str,
    rebuild_fn,
) -> None:
    """Rebuild an agg table with timing and error logging."""
    start = time.monotonic()
    try:
        async with session_factory() as session:
            async with session.begin():
                count = await rebuild_fn(session)
        elapsed = time.monotonic() - start
        logger.info(
            "Aggregation %s completed: %d rows in %.2fs",
            name, count, elapsed,
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.exception(
            "Aggregation %s failed after %.2fs",
            name, elapsed,
        )
        raise  # Let the scheduler handle retry policy
```

---

## §6 Performance Considerations

### TRUNCATE vs DELETE for table sizes < 100K rows

| Metric | TRUNCATE | DELETE (full table) |
|--------|----------|-------------------|
| Speed (100K rows) | ~1 ms | ~100–500 ms |
| Lock type | ACCESS EXCLUSIVE (blocks all) | ROW EXCLUSIVE (readers OK) |
| Dead tuples | None | 100K dead tuples (needs VACUUM) |
| Disk space | Reclaimed immediately | Reclaimed after VACUUM |
| MVCC-safe | No | Yes |
| Fires triggers | ON TRUNCATE only | ON DELETE per row |

**For CompGraph's table sizes (< 100K rows), TRUNCATE is the right choice.** The 1–5
second blocking window is acceptable, and avoiding dead tuple accumulation means no
VACUUM pressure on the Supabase instance.

### INSERT ... SELECT vs Python round-trip

| Method | Round-trips | Memory | Speed |
|--------|------------|--------|-------|
| `INSERT INTO ... SELECT ...` (server-side) | 1 | Server-only | Fastest |
| `execute(insert(Model), list_of_dicts)` | 1 (batched) | Python holds all rows | Fast |
| `session.add_all(objects)` | 1 (batched in 2.0) | Python holds ORM objects | Moderate |
| Loop of `session.add(obj)` | N | N objects in session | Slowest |

**Prefer `INSERT ... SELECT`** when the aggregation can be expressed in pure SQL.
Fall back to `execute(insert(Model), rows)` when Python processing is needed.

### Index maintenance

PostgreSQL maintains indexes during INSERT. For bulk inserts into an empty table (after
TRUNCATE), this is efficient because:

1. The B-tree is built incrementally as rows arrive.
2. No existing index entries need updating.
3. For < 100K rows, index maintenance overhead is negligible.

**Do not drop/recreate indexes** for CompGraph's table sizes. That optimization only
matters for millions of rows.

### Connection pool considerations

Each aggregation rebuild holds a connection for the duration of the transaction. With
CompGraph's pool settings (`pool_size=5`, `max_overflow=10`), running 4 sequential
rebuilds uses 1 connection at a time — no pool pressure. If rebuilds were parallelized,
they would use 4 connections simultaneously, which is still well within limits.

---

## §7 CompGraph Implementation Pattern

### Recommended pattern for the 4 agg table rebuilds

```python
"""
compgraph/aggregation/rebuild.py

Truncate+insert rebuild for all 4 aggregation tables.
Each table rebuilt in its own transaction — failure in one does not affect others.
"""

import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# Type alias for rebuild functions
RebuildFn = Callable[[AsyncSession], Awaitable[int]]


async def _rebuild_daily_velocity(session: AsyncSession) -> int:
    """Rebuild agg_daily_velocity from postings + snapshots."""
    await session.execute(text("TRUNCATE agg_daily_velocity"))
    result = await session.execute(text("""
        INSERT INTO agg_daily_velocity (id, date, company_id, new_postings, closed_postings, net_change)
        SELECT
            gen_random_uuid(),
            p.scraped_at::date,
            p.company_id,
            COUNT(*) FILTER (WHERE ps.first_seen = ps.snapshot_date),
            COUNT(*) FILTER (WHERE ps.status = 'closed'),
            COUNT(*) FILTER (WHERE ps.first_seen = ps.snapshot_date)
                - COUNT(*) FILTER (WHERE ps.status = 'closed')
        FROM postings p
        JOIN posting_snapshots ps ON ps.posting_id = p.id
        GROUP BY p.scraped_at::date, p.company_id
    """))
    return result.rowcount


async def _rebuild_with_monitoring(
    session_factory: async_sessionmaker[AsyncSession],
    name: str,
    rebuild_fn: RebuildFn,
) -> int:
    """Execute a rebuild function with timing, logging, and error handling."""
    start = time.monotonic()
    try:
        async with session_factory() as session:
            async with session.begin():
                count = await rebuild_fn(session)
        elapsed = time.monotonic() - start
        logger.info("Rebuilt %s: %d rows in %.2fs", name, count, elapsed)
        return count
    except Exception:
        elapsed = time.monotonic() - start
        logger.exception("Failed to rebuild %s after %.2fs", name, elapsed)
        raise


async def rebuild_all_aggregations(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, int]:
    """Rebuild all 4 aggregation tables sequentially.

    Each table is rebuilt in its own transaction. If one fails, the others
    still run (or have already run). Returns a dict of {table_name: row_count}.

    Called by the APScheduler cron job after scrape+enrich completes.
    """
    rebuilds: list[tuple[str, RebuildFn]] = [
        ("agg_daily_velocity", _rebuild_daily_velocity),
        ("agg_brand_timeline", _rebuild_brand_timeline),
        ("agg_pay_benchmarks", _rebuild_pay_benchmarks),
        ("agg_posting_lifecycle", _rebuild_posting_lifecycle),
    ]

    results: dict[str, int] = {}
    errors: list[str] = []

    for name, fn in rebuilds:
        try:
            count = await _rebuild_with_monitoring(session_factory, name, fn)
            results[name] = count
        except Exception:
            errors.append(name)
            # Continue to next table — don't let one failure block others

    if errors:
        logger.error(
            "Aggregation completed with errors in: %s", ", ".join(errors)
        )

    return results
```

### Key design decisions in this pattern

1. **One transaction per table.** If `agg_pay_benchmarks` fails, the other 3 tables still
   get rebuilt. Matches the scraper pattern (per-company isolation).

2. **Sequential execution.** No parallelism between table rebuilds. Keeps connection usage
   predictable (1 at a time) and avoids lock contention.

3. **`session.begin()` context manager** handles commit/rollback automatically. No manual
   `session.commit()` or `session.rollback()` calls.

4. **`INSERT ... SELECT` server-side** when possible. Avoids round-tripping aggregation
   data through Python. The database engine is much faster at this.

5. **`gen_random_uuid()` in SQL** for UUID primary keys. Avoids generating UUIDs in Python
   and passing them through parameters.

6. **Error logging, not error swallowing.** Failed rebuilds raise after logging. The
   scheduler decides retry policy.

### Scheduler integration

```python
# In src/compgraph/scheduler/jobs.py
from compgraph.aggregation.rebuild import rebuild_all_aggregations
from compgraph.db.session import async_session_factory


async def aggregation_job() -> None:
    """APScheduler job: rebuild all aggregation tables."""
    results = await rebuild_all_aggregations(async_session_factory)
    # results is logged inside rebuild_all_aggregations
```

---

## Sources

- [PostgreSQL 17: TRUNCATE](https://www.postgresql.org/docs/17/sql-truncate.html)
- [PostgreSQL 17: Explicit Locking](https://www.postgresql.org/docs/17/explicit-locking.html)
- [PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL 18: MVCC Caveats](https://www.postgresql.org/docs/current/mvcc-caveats.html)
- [PostgreSQL: DELETE vs. TRUNCATE (CYBERTEC)](https://www.cybertec-postgresql.com/en/postgresql-delete-vs-truncate/)
- [Pros & Cons of TRUNCATE vs DELETE (Medium)](https://gxara.medium.com/pros-cons-of-truncate-vs-delete-postgresql-68ecbc3c2505)
- [SQLAlchemy 2.0: AsyncIO Extension](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy 2.0: DBAPI Transactions](https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html)
- [Postgres Table Rename for Zero Downtime (brandur.org)](https://brandur.org/fragments/postgres-table-rename)
- [PostgreSQL REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html)
- [Postgres Locks Deep Dive (Medium)](https://medium.com/@hnasr/postgres-locks-a-deep-dive-9fc158a5641c)
- [Transaction Isolation in Postgres (thenile.dev)](https://www.thenile.dev/blog/transaction-isolation-postgres)
