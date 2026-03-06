# Supabase PITR Disaster Recovery Runbook

## Overview

Point-in-Time Recovery (PITR) restores the Supabase Postgres database to any moment within the retention window by replaying Write-Ahead Log (WAL) segments. Use PITR when a destructive operation (accidental truncate, bad migration, bulk delete) corrupts or destroys data that cannot be rebuilt from source.

**Supabase project ref:** `tkvxyxwfosworwqxesnz`
**Who can initiate:** Supabase dashboard admin (Organization Owner or Project Owner role)
**Requires:** Supabase Pro plan or higher with PITR add-on enabled

## Table Tier Safety Matrix

| Tier | Tables | Safe to truncate? | Recovery priority | Rationale |
|------|--------|--------------------|-------------------|-----------|
| Dimension | `companies`, `brands`, `retailers`, `markets`, `location_mappings` | NO | P0 | Slowly changing reference data, hard to rebuild without re-scraping and re-enriching |
| Fact | `postings`, `posting_snapshots`, `posting_enrichments`, `posting_brand_mentions` | NEVER | P0 | Append-only event data, irreplaceable historical record |
| Auth | `users` | NO | P0 | Managed by Supabase Auth, loss breaks all authentication |
| Operational | `scrape_runs`, `enrichment_runs`, `alerts` | NO | P1 | Pipeline audit trail, needed for debugging and alert history |
| Aggregation | `agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle`, `agg_brand_churn_signals`, `agg_market_coverage_gaps`, `agg_brand_agency_overlap` | YES | P2 | Rebuilt from source data via truncate+insert aggregation |
| Eval | `eval_corpus`, `eval_runs`, `eval_results`, `eval_comparisons`, `eval_field_reviews` | Tolerable loss | P3 | Can re-generate corpus and re-run evaluations |

**Decision rule:** If only aggregation tables (P2) were affected, do NOT use PITR. Run the aggregation rebuild instead (see "When NOT to Use PITR" below).

## RTO/RPO Targets

| Metric | Target | Basis |
|--------|--------|-------|
| **RPO** (Recovery Point Objective) | Continuous | PITR captures every WAL transaction, loss limited to in-flight transactions at crash time |
| **RTO** (Recovery Time Objective) | < 30 minutes | Dashboard-initiated restore, includes WAL replay and DNS switchover |

## PITR Restore Procedure

### 1. Confirm PITR is necessary

- Identify which tables were affected and their tier (see matrix above).
- If only aggregation tables: skip PITR, run aggregation rebuild.
- If dimension, fact, auth, or operational tables: proceed with PITR.

### 2. Stop the application

Prevent further writes that would conflict with the restored state.

```bash
ssh compgraph-do "sudo systemctl stop compgraph"
```

Verify the Vercel frontend will gracefully degrade (API calls return errors, no destructive client-side behavior).

### 3. Determine the restore point

- Find the timestamp of the last known-good state (before the bad operation).
- Check pipeline logs for the exact time:
  ```bash
  ssh compgraph-do "journalctl -u compgraph --since '1 hour ago' --no-pager | head -100"
  ```
- If a bad migration was the cause, check Alembic history:
  ```bash
  ssh compgraph-do "cd /opt/compgraph && op run --env-file=.env -- uv run alembic history -v"
  ```
- Use the timestamp from BEFORE the destructive operation. Add a 1-minute safety margin.

### 4. Initiate PITR restore

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/tkvxyxwfosworwqxesnz/settings/infrastructure).
2. Navigate to **Project Settings > Infrastructure > Point in Time Recovery**.
3. Select the restore timestamp identified in step 3.
4. Confirm the restore.

**What happens during restore:**
- Supabase provisions a new Postgres instance and replays WAL up to the chosen point.
- The project URL (`tkvxyxwfosworwqxesnz.supabase.co`) switches to the restored instance.
- Existing connections are terminated. The pooler (Supavisor) reconnects automatically.
- Auth sessions remain valid (JWT tokens are stateless; the `users` table is restored).
- Storage objects are NOT affected by PITR (stored separately).
- The restore is irreversible from the dashboard. The pre-restore state is lost.

### 5. Post-restore validation

Run these checks immediately after the restore completes:

```bash
# Verify database connectivity
ssh compgraph-do "cd /opt/compgraph && op run --env-file=.env -- uv run python -c \"
from compgraph.db.session import get_engine
from sqlalchemy import text
import asyncio
async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('DB connection OK')
    await engine.dispose()
asyncio.run(check())
\""
```

Validate row counts for critical tables:

```sql
SELECT 'postings' AS tbl, count(*) FROM postings
UNION ALL SELECT 'posting_snapshots', count(*) FROM posting_snapshots
UNION ALL SELECT 'posting_enrichments', count(*) FROM posting_enrichments
UNION ALL SELECT 'posting_brand_mentions', count(*) FROM posting_brand_mentions
UNION ALL SELECT 'companies', count(*) FROM companies
UNION ALL SELECT 'brands', count(*) FROM brands
UNION ALL SELECT 'scrape_runs', count(*) FROM scrape_runs
UNION ALL SELECT 'enrichment_runs', count(*) FROM enrichment_runs
ORDER BY tbl;
```

Compare against the last known counts (maintain a record after each successful pipeline run).

### 6. Verify Alembic migration state

```bash
ssh compgraph-do "cd /opt/compgraph && op run --env-file=.env -- uv run alembic current"
```

If the restore point predates a migration, re-apply:

```bash
ssh compgraph-do "cd /opt/compgraph && op run --env-file=.env -- uv run alembic upgrade head"
```

### 7. Rebuild aggregation tables

Aggregation tables may be stale after restore. Trigger a full rebuild:

```bash
ssh compgraph-do "sudo systemctl start compgraph"
# Wait for startup, then trigger aggregation via the scheduler
# or manually via the API if an endpoint exists
```

### 8. Verify application health

```bash
curl -sf https://dev.compgraph.io/health && echo "Backend OK"
curl -sf https://compgraph.app && echo "Frontend OK"
```

Check Sentry for new errors in the 15 minutes after restore.

## Dry-Run Drill Checklist

Perform this drill quarterly to validate the recovery process.

- [ ] **Create a Supabase branch database** via dashboard or CLI:
  ```bash
  supabase branches create --project-ref tkvxyxwfosworwqxesnz pitr-drill-$(date +%Y%m%d)
  ```
- [ ] **Record pre-truncate row counts** on the branch for all P0/P1 tables.
- [ ] **Simulate a destructive operation** on the branch:
  ```sql
  -- On branch DB only, NEVER on production
  TRUNCATE posting_snapshots CASCADE;
  ```
- [ ] **Verify data is gone** (row count = 0 for truncated table).
- [ ] **Restore the branch** to a point before the truncate using the dashboard.
- [ ] **Verify row counts match** pre-truncate values.
- [ ] **Document results** in `docs/runbooks/drill-logs/` with date, participants, duration, and any issues encountered.
- [ ] **Delete the branch** after the drill to avoid cost accumulation.

## When NOT to Use PITR

**Use aggregation rebuild instead** when only these tables are affected:
- `agg_daily_velocity`
- `agg_brand_timeline`
- `agg_pay_benchmarks`
- `agg_posting_lifecycle`
- `agg_brand_churn_signals`
- `agg_market_coverage_gaps`
- `agg_brand_agency_overlap`

These tables are rebuilt from source data via truncate+insert during every aggregation run. A bad aggregation output is fixed by re-running aggregation, not by restoring the entire database.

**Use selective re-enrichment** when only eval tables are affected (`eval_corpus`, `eval_runs`, `eval_results`, `eval_comparisons`, `eval_field_reviews`). Re-generate the corpus and re-run evaluations rather than restoring the full database.

**Do NOT use PITR for:**
- Schema rollback (use `alembic downgrade` instead)
- Removing a few bad rows (use targeted DELETE with a WHERE clause)
- Testing (use branch databases)
