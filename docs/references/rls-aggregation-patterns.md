# RLS & Aggregation Tables: Information Leak Patterns

Reference for securing pre-computed aggregation tables when fact tables are RLS-protected. Covers Supabase-specific patterns, CompGraph table analysis, and performance implications.

**CompGraph context:** 4 agg tables (`agg_daily_velocity`, `agg_brand_timeline`, `agg_pay_benchmarks`, `agg_posting_lifecycle`) are rebuilt via `service_role` (truncate+insert). 2 roles: Admin (full access) and Viewer (read-only dashboards). All data is about competitors, not about the user's own company. Supabase Postgres 17, FastAPI backend.

---

## Quick Reference

| CompGraph Table | Sensitive? | Recommended Pattern | Rationale |
|----------------|-----------|-------------------|-----------|
| `agg_daily_velocity` | No | Pattern B (Global-Only) | Company-level hiring trends are the product |
| `agg_brand_timeline` | No | Pattern B (Global-Only) | Brand-company relationships are the product |
| `agg_pay_benchmarks` | Low | Pattern B (Global-Only) | Pay ranges are aggregated, not individual |
| `agg_posting_lifecycle` | No | Pattern B (Global-Only) | Posting age/status is public data |
| `postings` (fact) | No | RLS: `authenticated` can SELECT | All postings are public job listings |
| `users` | Yes | RLS: own row only | `auth.uid() = id` policy |

**Verdict for CompGraph:** Pattern B (Global-Only) for all agg tables. No per-viewer filtering needed. Both Admin and Viewer see the same competitive intelligence data. RLS on agg tables adds cost with zero security benefit.

---

## S1 The Aggregation Leak Problem

When fact tables have RLS (e.g., `tenant_id = auth.uid()`) but agg tables are built by `service_role` (which bypasses RLS), aggregations can leak data:

```
fact_table (RLS: tenant_id = auth.uid())
    |
    v  service_role builds agg (no RLS filter applied)
    |
agg_table (contains ALL tenants' data in global totals)
    |
    v  user queries agg_table
    |
User sees competitor data they shouldn't → LEAK
```

**This is a real problem for multi-tenant SaaS** where tenants must not see each other's data. It is **NOT a problem for CompGraph** because all data is competitor intelligence -- the whole point is seeing all companies' data.

---

## S2 Three Patterns

### Pattern A: Filtered Aggregation

Add tenant/role columns to agg tables. Apply RLS on agg tables themselves.

```sql
-- Agg table includes a visibility column
CREATE TABLE agg_daily_velocity (
    id UUID PRIMARY KEY,
    date DATE,
    company_id UUID,
    new_postings INT,
    visible_to_role TEXT DEFAULT 'viewer'  -- 'admin' or 'viewer'
);

-- RLS policy
ALTER TABLE agg_daily_velocity ENABLE ROW LEVEL SECURITY;
CREATE POLICY "viewers_see_viewer_rows" ON agg_daily_velocity
    FOR SELECT USING (
        visible_to_role = 'viewer'
        OR (SELECT raw_user_meta_data->>'role' FROM auth.users WHERE id = auth.uid()) = 'admin'
    );
```

**Pros:** Fine-grained per-row control. Standard RLS tooling.
**Cons:** Agg rebuild must populate visibility columns. Subquery in policy runs per-row. Complex for small teams.

### Pattern B: Global-Only (Recommended for CompGraph)

All agg data is global. No RLS on agg tables. Access control at API layer.

```sql
-- No RLS on agg tables -- all authenticated users see everything
ALTER TABLE agg_daily_velocity ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read" ON agg_daily_velocity
    FOR SELECT TO authenticated USING (true);
```

```python
# FastAPI enforces role checks, not RLS
@router.get("/api/velocity")
async def get_velocity(
    current_user: User = Depends(get_current_user),  # auth check
    db: AsyncSession = Depends(get_db),
):
    # Both admin and viewer hit the same query
    result = await db.execute(select(AggDailyVelocity))
    return result.scalars().all()
```

**Pros:** Simplest. No RLS overhead on pre-computed tables. Backend controls access.
**Cons:** Can't restrict specific rows per user. All-or-nothing access.

### Pattern C: Security-Invoker Views

Create views with `security_invoker = true` (Postgres 15+) that JOIN agg data with user permissions.

```sql
CREATE VIEW v_agg_velocity
WITH (security_invoker = true) AS
SELECT adv.*
FROM agg_daily_velocity adv
WHERE EXISTS (
    SELECT 1 FROM user_permissions up
    WHERE up.user_id = (SELECT auth.uid())
    AND up.company_id = adv.company_id
);
```

**Pros:** RLS on underlying tables applies through the view. No duplicate data.
**Cons:** Views bypass RLS by default (must set `security_invoker`). Materialized views do NOT support RLS in Postgres 17. Performance overhead from per-row permission check.

---

## S3 Why CompGraph Uses Pattern B

| Question | Answer |
|----------|--------|
| Is data multi-tenant? | **No.** All data is about 4 competitor companies. |
| Do users own different data? | **No.** All users see the same competitive landscape. |
| Should Viewer see less than Admin? | **Not for agg data.** Admin may have extra features (user mgmt, scheduler control) but same dashboard data. |
| Is there PII in agg tables? | **No.** Aggregated counts, averages, timelines. Individual posting text stays in fact tables. |
| Is there a paid-tier upsell on data access? | **No.** Single product for Mosaic internal use. |

If requirements change (e.g., external client access with company-specific restrictions), migrate to Pattern A by adding a `visible_companies UUID[]` column and RLS policy.

---

## S4 RLS Performance on Aggregation Tables

| Factor | Impact | Mitigation |
|--------|--------|------------|
| `auth.uid()` per-row evaluation | ~0.1ms overhead per policy check | Wrap in subquery: `(SELECT auth.uid()) = col` for initplan caching |
| Complex JWT extraction (`raw_user_meta_data->>'role'`) | JSON parse per row | Extract once via `(SELECT ...)` subquery pattern |
| Missing indexes on policy columns | 100x+ slowdown on large tables | Always index columns referenced in RLS policies |
| RLS on materialized views | **Not reliably supported** in Postgres 17 | Use regular views with `security_invoker = true` or skip RLS entirely |
| Subqueries in policies | Execute per-row | Keep policies simple; move complex logic to `SECURITY DEFINER` functions |

**For CompGraph's agg tables (< 100K rows):** RLS overhead is negligible even with naive policies. But since it adds no security value (Pattern B), skip it entirely.

---

## S5 Supabase-Specific Notes

| Topic | Detail |
|-------|--------|
| `service_role` key | Bypasses ALL RLS. Used by backend for agg rebuilds. Never expose to frontend. |
| `anon` / `authenticated` roles | Subject to RLS policies. Frontend (via Supabase client) uses these. |
| `auth.uid()` | Returns NULL for `anon` role. Returns user UUID for `authenticated`. |
| `auth.jwt()` | Access full JWT claims including `role`, `email`, custom metadata. |
| Default view behavior | Views bypass RLS (created as `security_definer` by postgres role). Must explicitly set `security_invoker = true` on Postgres 15+. |
| Materialized views + RLS | Policies can be defined but enforcement is unreliable. Supabase UI doesn't show mat-view policies. Avoid relying on this. |
| `EXPLAIN ANALYZE` with RLS | Supabase SQL Editor runs as `postgres` (bypasses RLS). Test RLS performance by setting role: `SET ROLE authenticated; SET request.jwt.claims = '{"sub":"..."}';` |

---

## S6 Gotchas & Limitations

| Issue | Impact | Source |
|-------|--------|--------|
| Views bypass RLS by default | Data leak if view used in PostgREST/Supabase API without `security_invoker` | [Supabase Discussion #1501](https://github.com/orgs/supabase/discussions/1501) |
| Mat views have no reliable RLS | Policies defined but may not enforce | [Supabase Discussion #17790](https://github.com/orgs/supabase/discussions/17790) |
| Non-LEAKPROOF functions block index use | RLS policy with custom function forces seq scan | [PostgreSQL 18 Docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) |
| FK constraints bypass RLS | Can infer existence of restricted rows via FK errors | [PostgreSQL 18 Docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) |
| `auth.uid()` without subquery wrapper | Re-evaluated per row instead of cached as initplan | [Supabase RLS Performance](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv) |
| Race conditions in policy subqueries | Concurrent writes can cause policy to see stale data | [Bytebase RLS Footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns/) |

---

## S7 Implementation Checklist for CompGraph

- [ ] Enable RLS on all agg tables (required by Supabase for API exposure)
- [ ] Add permissive `authenticated` SELECT policy: `USING (true)`
- [ ] Do NOT add tenant/user columns to agg tables (Pattern B)
- [ ] Backend uses `service_role` for agg rebuilds (bypasses RLS)
- [ ] Frontend Supabase client uses `authenticated` role (RLS applies, but policy is `true`)
- [ ] FastAPI endpoints enforce Admin-vs-Viewer at app layer (route guards, not RLS)
- [ ] Fact tables (`postings`, `posting_enrichments`): same `USING (true)` for now; tighten if external access added
- [ ] `users` table: `USING (auth.uid() = id)` -- users see only their own profile

---

## Sources

- [Supabase RLS Docs](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase RLS Performance Best Practices](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv)
- [Supabase Discussion #17790: Mat Views + RLS](https://github.com/orgs/supabase/discussions/17790)
- [Supabase Discussion #1501: RLS on Views](https://github.com/orgs/supabase/discussions/1501)
- [Supabase Discussion #3424: RLS vs Security Barrier Views](https://github.com/orgs/supabase/discussions/3424)
- [PostgreSQL 18: Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Postgres Views Security Gotcha (DEV Community)](https://dev.to/datadeer/postgres-views-the-hidden-security-gotcha-in-supabase-ckd)
- [Bytebase: Common RLS Footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns/)
- [pganalyze: RLS, BYPASSRLS, LEAKPROOF](https://pganalyze.com/blog/5mins-postgres-row-level-security-bypassrls-security-invoker-views-leakproof-functions)
- [Cybertec: PostgreSQL RLS, Views and Magic](https://www.cybertec-postgresql.com/en/postgresql-row-level-security-views-and-a-lot-of-magic/)
