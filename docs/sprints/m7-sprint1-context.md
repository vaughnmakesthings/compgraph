# M7 Sprint 1 — Foundation

**Goal:** Auth stack + critical fixes. Everything here must ship before Sprint 2 begins.

**Milestone:** [M7 Sprint 1 — Foundation](https://github.com/vaughnmakesthings/compgraph/milestone/9)

---

## Items This Sprint

### SEC-01 — Supabase Auth & RBAC (CRITICAL)

**Issues:** #59 (parent), #206, #207, #208, #209, #210
**Files:** `src/compgraph/api/deps.py`, `src/compgraph/api/routes/admin.py`, `src/compgraph/db/models.py`, `web/src/app/login/`, `web/src/app/setup/`, `web/src/app/layout.tsx`, `alembic/versions/`
**Acceptance:** Unauthenticated requests to `/trigger` and `/stop` return 401. Admin-only routes return 403 for viewer role.

**Subtasks (in order):**

| # | Issue | Title | Status |
|---|-------|-------|--------|
| 1 | [#206](https://github.com/vaughnmakesthings/compgraph/issues/206) | Configure Supabase Auth project (magic link, redirects, disable signup) | Needs manual step first |
| 2 | [#207](https://github.com/vaughnmakesthings/compgraph/issues/207) | Backend auth middleware (auth_uid migration, get_current_user, role guards, invite endpoint) | Ready |
| 3 | [#208](https://github.com/vaughnmakesthings/compgraph/issues/208) | Frontend auth pages (/login, /setup, auth context, admin invite UI) | Blocked by #207 |
| 4 | [#209](https://github.com/vaughnmakesthings/compgraph/issues/209) | RLS policies migration (viewer/admin/service_role across all 25 tables) | Blocked by #207 |
| 5 | [#210](https://github.com/vaughnmakesthings/compgraph/issues/210) | Auth testing strategy (AUTH_DISABLED env gate + mock JWT role tests) | Ready |

**Context pack:** Pack I (Auth & Access Control)

---

### ARCH-02 — DB-Backed Run Tracking (HIGH)

**Issue:** [#156](https://github.com/vaughnmakesthings/compgraph/issues/156)
**Files:** `src/compgraph/scrapers/orchestrator.py`, `src/compgraph/enrichment/orchestrator.py`, `alembic/versions/`
**Prereqs:** Alembic migration to add `last_heartbeat_at` column to `scrape_runs` and `enrichment_runs` tables (can be done in same PR).
**Acceptance:** No global `_runs` dicts remain; all pipeline/enrichment state tracked in `scrape_runs`/`enrichment_runs` tables. Concurrency guard queries DB instead of in-memory set.

**Context pack:** Pack G (Pipeline Orchestration)

---

### LLM-01 — Pay Sanity Checks (CRITICAL)

**Issue:** [#198](https://github.com/vaughnmakesthings/compgraph/issues/198)
**Files:** `src/compgraph/enrichment/schemas.py`
**Prereqs:** None
**Acceptance:** Pydantic rejects hourly > $150, annual > $300k, `pay_min > pay_max`. Unit tests confirm rejection of `"$1M budget"` patterns.

**Context pack:** Pack B (Enrichment Pipeline)

---

### ARCH-03 — /api/v1/ Prefix (MEDIUM)

**Issue:** [#199](https://github.com/vaughnmakesthings/compgraph/issues/199)
**Files:** `src/compgraph/main.py`, `tests/test_*.py` (~30 path assertions), `web/src/lib/api-client.ts` (~50 paths), `web/src/**/*.test.{ts,tsx}` (~30 expectations)
**Prereqs:** None — but **deploy order matters** (backend first with 308 redirect, then frontend). See cutover strategy in `docs/reports/gap-analysis-consolidated.md` §10.
**Acceptance:** All endpoints served at `/api/v1/`. Old `/api/` paths return 308 redirect (temporary, removed in cleanup PR). `/health` stays unversioned.

**Context pack:** Pack K (API Versioning M7) or Pack D (API Endpoints)

---

### UX-02 — ConfirmDialogs (MEDIUM)

**Issue:** [#184](https://github.com/vaughnmakesthings/compgraph/issues/184)
**Files:** `web/src/app/settings/page.tsx` (primary), any other pages with destructive/LLM-triggering actions
**Prereqs:** None
**Acceptance:** Trigger Pipeline, Stop Pipeline, and any delete/reset actions show a Tremor `ConfirmDialog` before executing. Reversible actions (Pause/Resume) do not require confirmation.

**Context pack:** `CLAUDE.md` + `web/CLAUDE.md` sufficient

---

## Manual Steps (Do Before Starting SEC-01)

- [ ] Enable magic link provider in Supabase Auth dashboard (project `tkvxyxwfosworwqxesnz`)
- [ ] Configure redirect URLs: `https://compgraph.vercel.app/setup` and `http://localhost:3000/setup`
- [ ] Disable public signup in Supabase Auth settings

These are dashboard-only clicks — see issue #206 for details.

---

## Recommended Build Order

```
1. UX-02 (ConfirmDialogs)     — no prereqs, quick win, unblocks demos
2. LLM-01 (pay constraints)   — no prereqs, single file
3. SEC-01.1 (#206)            — manual Supabase config (prereq for all auth)
4. SEC-01.2 (#207)            — backend middleware (prereq for .3 and .4)
5. SEC-01.5 (#210)            — testing strategy (can overlap with .2)
6. ARCH-02 (#156)             — DB-backed run tracking
7. SEC-01.3 (#208)            — frontend auth pages (needs #207 live)
8. SEC-01.4 (#209)            — RLS migration (needs auth_uid from #207)
9. ARCH-03 (#199)             — /api/v1/ prefix (2-PR cutover, backend then frontend)
```

ARCH-03 goes last — the 2-step deploy (backend → frontend) requires all other PRs to be merged first so the 308 redirect window is short.

---

## Parallel Track (Independent — Start Anytime)

**Eval Tool:** Issues #205 (parent), #211, #212, #213, #214 — milestone #13 (M7 Parallel — Eval Tool). No auth dependency. Can run concurrently with all Sprint 1 work.

---

## Context Packs

| Item | Pack | When to Load |
|------|------|-------------|
| SEC-01 | Pack I — Auth & Access Control | Before any auth work |
| ARCH-02 | Pack G — Pipeline Orchestration | Before touching orchestrator.py |
| LLM-01 | Pack B — Enrichment Pipeline | Before modifying schemas.py |
| ARCH-03 | Pack K — API Versioning (M7) | Before the prefix PR |
| UX-02 | CLAUDE.md + web/CLAUDE.md | Already in context |
| Eval Tool | Pack J — Eval Tool Consolidation (M7) | Before any eval work |
