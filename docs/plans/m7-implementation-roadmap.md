# M7 Implementation Roadmap

**Date:** 2026-02-24
**Status:** Approved
**Authors:** Claude Opus (PM), Gemini CLI (Engineering Swarm), Product Owner
**Supersedes:** Gap analysis Section 10 sprint ordering (now the source of truth)

---

## 1. Executive Summary

M7 transforms CompGraph from a dev-only prototype into a production-ready platform. Three workstreams run in parallel:

1. **API Versioning + Quick Wins** — establish the `/api/v1/` contract and close trivial quality gaps
2. **Eval Tool Consolidation** — merge the split-brain eval architecture into one Postgres-backed system
3. **Supabase Auth + RBAC** — lock down all endpoints with invite-only authentication and role-based access

All three converge on a production-ready state where the platform can be demonstrated to stakeholders behind authentication, with a working evaluation tool for prompt quality management.

---

## 2. Locked Product Decisions

These decisions are final. Do not revisit during implementation.

| Decision | Detail | Decided By |
|----------|--------|------------|
| **Target user** | Business admin with some technical knowledge — NOT engineers | Product Owner |
| **Auth model** | Invite-only. No public signup URL. Magic link for provisioning, email+password for login. | Product Owner |
| **Auth provider** | Supabase Auth (not custom JWT) | CLAUDE.md pre-commitment |
| **Roles** | `admin` (full access, invite users, pipeline controls, eval) and `viewer` (read-only dashboard) | Product Owner |
| **Eval LLM provider** | OpenRouter (API credits available). LiteLLM as the abstraction layer. | Product Owner |
| **Eval tool UX** | Guided flow with jargon simplification for non-engineers. No hard-locked stepper. | PM + Product Owner |
| **Ground truth labeling** | Admin user does this via the eval Review page | Product Owner |
| **Standalone eval app** | Delete `eval/` directory after Phase B merge | Product Owner |
| **API versioning** | Prefix only (`/api/v1/`). No version negotiation middleware, no V2 scaffolding. | PM (engineering disagreement resolution) |
| **SWR adoption** | New M7 components + Settings page polling only. No blanket migration of existing pages. | PM |
| **Factory-boy** | Rejected. Revisit only if a schema migration breaks >5 tests. | PM |
| **Frontend auth SDK** | `@supabase/supabase-js` only. No `@supabase/auth-ui-react` pre-built UI kit. | PM |
| **python-dotenv** | Rejected. Project uses `pydantic-settings` with `SettingsConfigDict(env_file=".env")`. | PM |
| **Background job auth** | Orchestrators use `service_role` connection (bypasses RLS). Not per-user JWT. | PM |

---

## 3. Already Resolved (Do Not Re-implement)

These items from the audit reports are confirmed fixed in the codebase. Skip them.

| ID | Issue | Evidence |
|----|-------|----------|
| SEC-02 | SQL wildcard injection | `_escape_like()` restored in `postings.py:92` (PR #196) |
| SEC-03 | Missing SSL in Alembic | `connect_args={"ssl": "require"}` in `alembic/env.py:69` |
| DATA-01 | Double-counting enrichments | `latest_enrichment` CTE in `pay_benchmarks.py`, `posting_lifecycle.py` |
| DATA-02 | Missing FK indexes | Issue #45 closed; composite indexes on all major FK columns |
| DATA-03 | Brand duplication | `dedup_brands.py` run in prod; 3 pairs consolidated |
| SCRP-01 | Silent scraper failures | `check_baseline_anomaly()` in `orchestrator.py:122` |
| QA-01 | Shallow health endpoint | `health.py` has DB `SELECT 1` + scheduler liveness, returns 503 on failure |
| PERF-05 | Incorrect aggregate ordering | Raw SQL, confirmed N/A for ORM usage |

---

## 4. Phase A: API Versioning + Quick Wins

**Goal:** Establish the `/api/v1/` contract and close trivial quality gaps.
**Dependencies:** None — can start immediately.
**Effort:** Small (1-2 days)

### 4.1 `/api/v1/` Prefix (ARCH-03)

**Approach:** Option C — backend first with 308 redirect for backward compatibility.

**Current state (verified):**
- 6 routers define prefix in their `APIRouter()`: scrape, enrich, scheduler, pipeline, aggregation, companies
- 2 routers get prefix from `main.py`: postings (`/api/postings`), eval (`/api/eval`)
- Frontend `api-client.ts` imports `API_BASE` from `constants.ts` (`NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'`)
- `vercel.json` rewrites `/api/:path*` → `https://dev.compgraph.io/api/:path*` (wildcard — already handles `/api/v1/`)
- `/health` stays at `/health` (no version prefix for health checks)

**Step 1 — Backend PR (deploy first):**

```python
# src/compgraph/main.py — new pattern
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(scrape_router)
v1_router.include_router(enrich_router)
v1_router.include_router(scheduler_router)
v1_router.include_router(pipeline_router)
v1_router.include_router(aggregation_router)
v1_router.include_router(companies_router)
v1_router.include_router(postings_router, tags=["postings"])
v1_router.include_router(eval_router, tags=["eval"])
app.include_router(v1_router)
app.include_router(health_router)  # health stays unversioned
```

Changes required:
- `src/compgraph/main.py` — replace 8 `app.include_router()` calls with `v1_router` wrapper
- 6 route files — strip `/api/<resource>` prefix from `APIRouter()` (now handled by wrapper):
  - `src/compgraph/api/routes/scrape.py:22` — `prefix="/api/scrape"` → `prefix="/scrape"`
  - `src/compgraph/api/routes/enrich.py:23` — `prefix="/api/enrich"` → `prefix="/enrich"`
  - `src/compgraph/api/routes/scheduler.py:17` — `prefix="/api/scheduler"` → `prefix="/scheduler"`
  - `src/compgraph/api/routes/pipeline.py:24` — `prefix="/api/pipeline"` → `prefix="/pipeline"`
  - `src/compgraph/api/routes/aggregation.py:21` — `prefix="/api/aggregation"` → `prefix="/aggregation"`
  - `src/compgraph/api/routes/companies.py:10` — `prefix="/api/companies"` → `prefix="/companies"`
- 2 routers in main.py — strip prefix (now handled by wrapper):
  - `postings_router` — remove `prefix="/api/postings"` from `include_router()`
  - `eval_router` — remove `prefix="/api/eval"` from `include_router()`
- Add catch-all backward-compatibility redirect:

```python
# src/compgraph/main.py — temporary redirect (remove in Step 3)
from fastapi.responses import RedirectResponse

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def redirect_to_v1(path: str, request: Request):
    url = str(request.url).replace("/api/", "/api/v1/", 1)
    return RedirectResponse(url=url, status_code=308)  # 308 preserves HTTP method
```

- Update all Python test files: `/api/` → `/api/v1/` in path assertions (~30 assertions)
- Merge → CD deploys backend. Old frontend still works via 308 redirect.

**Step 2 — Frontend PR (deploy after backend is live):**

```typescript
// web/src/lib/constants.ts — change API_BASE
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
// No change needed here — paths in api-client.ts change instead
```

- `web/src/lib/api-client.ts` — update all paths: `/api/pipeline/status` → `/api/v1/pipeline/status` (50+ paths)
- `web/src/**/*.test.{ts,tsx}` — update test expectations (~30 assertions)
- `web/vercel.json` — **NO CHANGE** (wildcard already works)
- Merge → Vercel deploys. Frontend now calls `/api/v1/` directly.

**Step 3 — Cleanup PR (after both are live):**
- Remove the `/api/{path:path}` catch-all redirect from `main.py`
- Verify no traffic hits old paths (check server logs)

### 4.2 Quick Wins (ship alongside v1 prefix)

| Item | File | Change | Effort |
|------|------|--------|--------|
| CG-QUAL-001 | `src/compgraph/preflight.py:1005` | Replace `datetime.now()` with `datetime.now(UTC)` | Trivial |
| LLM-01 (partial) | `src/compgraph/eval/schemas.py` or enrichment schemas | Add upper bound to Pydantic pay validators: Hourly $10-$150, Annual $20K-$300K, `min <= max` | Small |
| UX-02 | `web/src/app/settings/page.tsx` | Wrap destructive buttons (truncate, stop) with ConfirmDialog | Small |

---

## 5. Phase B: Eval Tool Consolidation

**Goal:** Eliminate the split-brain architecture. Make the "Run Evaluation" button actually call LLMs.
**Dependencies:** None — can start in parallel with Phase A.
**Effort:** Medium-Large (1-2 weeks)

### 5.0 Bootstrap (Phase 0 — prereqs before code changes)

| Step | Action | Detail |
|------|--------|--------|
| 1 | Generate eval corpus | Run `scripts/generate_eval_corpus.py` against the live Supabase DB. This populates `eval/data/corpus.json` — currently **empty** (only `.gitkeep` exists). |
| 2 | Bootstrap corpus into Postgres | Create `scripts/bootstrap_eval_corpus.py` — reads corpus.json, bulk-inserts into `eval_corpus` table via `INSERT ON CONFLICT DO NOTHING`. |
| 3 | Verify `eval_corpus` table has data | Query: `SELECT count(*) FROM eval_corpus` — must be >0 before Phase 1 begins. |

### 5.1 Execution Engine Merge (Phase 1)

**File mapping — what moves where:**

| Source (`eval/eval/`) | Destination (`src/compgraph/eval/`) | Transformation |
|----------------------|-------------------------------------|----------------|
| `runner.py` | `logic.py` (new) | Replace `EvalStore` calls with `AsyncSession` (Postgres). Replace `eval.prompts.load_prompt` with integrated prompt loader. Replace `eval.providers.call_llm` with local `providers.py`. |
| `providers.py` | `providers.py` (new) | Keep LiteLLM wrapper. Pull model config from `Settings` instead of `eval.config.MODELS`. Use `OPENROUTER_API_KEY` from `pydantic-settings`. |
| `config.py` | Merge into `src/compgraph/config.py` | Add `OPENROUTER_API_KEY: SecretStr`, `EVAL_CONCURRENCY: int = 5`, `EVAL_MAX_TOKENS_PASS1: int = 2048`, `EVAL_MAX_TOKENS_PASS2: int = 1024`. Add `EVAL_MODELS` dict (the 16-model catalog from `eval/eval/config.py`). |
| `schemas.py` | `schemas.py` (existing) | Align Pydantic models (`Pass1Result`, `Pass2Result`) with `eval/models.py` column names. |
| `prompts/pass1_v1.py` | `prompts/pass1_v1.py` (new dir) | Copy as-is; fix relative imports. |
| `prompts/pass2_v1.py` | `prompts/pass2_v1.py` (new dir) | Copy as-is; fix relative imports. |
| `store.py` | **DELETE** | All storage goes through Postgres `AsyncSession`. |
| `elo.py` | Already exists in integrated module | No action. |
| `ground_truth.py` | Review for useful logic to merge | May contain validation logic for ground truth entries. |
| `validator.py` | Review for useful logic to merge | May contain field-level validation helpers. |
| `api.py` | **DELETE** | Standalone API replaced by integrated `router.py`. |
| `ui/` | **DELETE** | Streamlit UI replaced by Next.js pages. |

**Dependency change:**
- Add `litellm` to root `pyproject.toml` `[project.dependencies]` (currently only in `eval/pyproject.toml`)
- Do NOT add `python-dotenv` — `pydantic-settings` handles `.env` loading

**Router wiring — replace the stub at `router.py:529`:**

```python
# src/compgraph/eval/router.py — replace TODO at line 529
from compgraph.eval.logic import run_evaluation

# Inside create_run():
# 1. Create EvalRun DB record (already done above line 529)
# 2. Launch background task that writes progress to DB
task = asyncio.create_task(
    run_evaluation(
        run_id=run.id,
        pass_number=body.pass_number,
        model=body.model,
        prompt_version=body.prompt_version,
        postings=postings,
        db_factory=async_session_factory,  # pass factory, not session (background task needs its own)
    )
)
task.add_done_callback(lambda t: _background_tasks.discard(t))
_background_tasks.add(task)

# 3. Return tracking info for frontend polling
return {"tracking_id": tracking_key, "run_id": str(run.id), "status": "starting", "total": len(postings)}
```

**Progress tracking:**
- `run_evaluation()` updates `eval_runs` row in DB as it progresses (completed count, status, tokens, cost)
- `GET /api/v1/eval/runs/{id}` already returns run status from DB — frontend polls this
- `GET /api/v1/eval/progress/{tracking_id}` stays for real-time in-memory progress (faster than DB polling)
- Both endpoints work: in-memory for sub-second updates, DB for persistence across restarts

**1Password secret:**
- Add `OPENROUTER_API_KEY` to `.env` template
- Store actual key in 1Password DEV vault
- Access via: `op run --env-file=.env -- uv run compgraph`

### 5.2 Comparison Engine (Phase 2)

Build after Phase 1 is deployed and admin has run at least 2 evaluations to compare.

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Field-level diff | Compare `parsed_result` JSONB between two `eval_results` rows. Display structured diffs: "Model A: $15/hr vs Model B: $18/hr" | Use existing `EvalComparison` model |
| Cost vs accuracy | Rank models by `accuracy / cost_usd`. Display as scatter plot (Recharts). | Accuracy = match rate against `reference_pass1/2` |
| Regression detection | For each corpus entry: did the newer prompt version get it right when the older version did? Flag regressions. | Compare `parse_success` + field match rates |
| Trust scoring | Per-field accuracy rates aggregated across corpus. "Pay extraction: 92% match rate". | Aggregate `eval_field_reviews.is_correct` |

### 5.3 Guided UX for Business Admins (Phase 3)

Build after Phase 2 proves the comparison engine works.

| Feature | Detail |
|---------|--------|
| Terminology simplification | "Tokens" → "Processing Volume", "Latency" → "Thinking Time", "Temperature" → "Creativity Level" |
| Model selection | Dropdown with human-friendly labels: "Fast/Cheap (Haiku 4.5)" vs "Smart/Premium (Opus 4.6)" instead of raw model IDs |
| Scenario templates | Pre-built configs: "Test Pay Extraction Accuracy", "Compare Brand Detection", "Full Pipeline Benchmark" |
| Guided flow | Recommended sequence: Define → Run → Compare → Feedback → Analyze → Iterate. Non-linear navigation allowed. |
| Ground truth editing | Structured forms on Review page for admin to correct individual fields (not raw JSON blob editing) |
| Pre-filled corrections | Suggest corrections from reference data when admin reviews a result |

### 5.4 Standalone App Cleanup

After Phase 1 is merged and verified:
- Delete the entire `eval/` directory (runner, store, Streamlit UI, config, schemas, prompts, tests)
- Stop the Pi service: `ssh compgraph-dev 'systemctl stop compgraph-eval && systemctl disable compgraph-eval'`
- Remove `eval/` from any CI/CD workflows
- Remove `eval/pyproject.toml` dependencies that are now in root `pyproject.toml`

---

## 6. Phase C: Supabase Auth & RBAC

**Goal:** Lock down all endpoints. Implement invite-only authentication with admin/viewer roles.
**Dependencies:** Phase A should be complete (auth routes need `/api/v1/` prefix).
**Effort:** Medium-Large (1-2 weeks)

### 6.1 Supabase Auth Project Configuration

| Setting | Value | Where |
|---------|-------|-------|
| Magic link provider | Enabled | Supabase Dashboard → Auth → Providers |
| Email+password provider | Enabled | Supabase Dashboard → Auth → Providers |
| Public signup | **Disabled** | Supabase Dashboard → Auth → Settings |
| Redirect URLs | `https://compgraph.vercel.app/setup`, `http://localhost:3000/setup` | Supabase Dashboard → Auth → URL Configuration |
| JWT secret | `SUPABASE_JWT_SECRET` | 1Password DEV vault → `.env` → `config.py` |
| Site URL | `https://compgraph.vercel.app` | Supabase Dashboard → Auth → URL Configuration |

### 6.2 Backend Auth Middleware

**New file: `src/compgraph/api/auth.py`**

```python
# Core auth dependency
from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from compgraph.config import settings
from compgraph.db.models import User

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Decode Supabase JWT, look up user in public.users table.
    Returns 401 if token invalid or user not found (invite-only — no JIT creation)."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    try:
        payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"],
                             audience="authenticated")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.execute(select(User).where(User.auth_uid == payload["sub"]))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")  # NOT 403 — invite-only
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Route guard: admin role required."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

**Config additions (`src/compgraph/config.py`):**
```python
SUPABASE_JWT_SECRET: SecretStr  # HS256 secret from Supabase project settings
AUTH_DISABLED: bool = False     # Set True in test env to bypass auth
```

**Auth bypass for tests (`src/compgraph/api/auth.py`):**
```python
async def get_current_user(...) -> User:
    if settings.AUTH_DISABLED:
        return User(id=uuid4(), email="test@test.com", role="admin", name="Test User")
    # ... normal JWT flow
```

### 6.3 Database Migration

**Alembic migration: add `auth_uid` column to `users` table**

```python
# alembic/versions/xxxx_add_auth_uid_to_users.py
def upgrade():
    op.add_column("users", sa.Column("auth_uid", sa.String(255), unique=True, nullable=True))
    op.create_index("ix_users_auth_uid", "users", ["auth_uid"])

def downgrade():
    op.drop_index("ix_users_auth_uid")
    op.drop_column("users", "auth_uid")
```

**Current User model** (`src/compgraph/db/models.py:459`):
```
id: UUID (PK)
email: String(255), unique
name: String(255), nullable
role: String(20), default="viewer"
invited_by: FK(users.id), nullable
created_at: DateTime(tz), server_default=now()
```
After migration adds: `auth_uid: String(255), unique, nullable` — links to Supabase `auth.users.id`.

### 6.4 Admin Invite Endpoint

**New endpoint: `POST /api/v1/admin/invite`**

```python
@router.post("/admin/invite")
async def invite_user(
    body: InviteRequest,  # {email: str, role: "admin" | "viewer"}
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # 1. Call Supabase Admin API to send magic link to email
    #    supabase.auth.admin.invite_user_by_email(email, redirect_to="/setup")
    # 2. Create User record in public.users with email, role, invited_by=admin.id
    #    auth_uid populated later when user clicks magic link and provisions account
    # 3. Return success
```

### 6.5 Frontend Auth Pages

**New pages:**

| Page | Route | Purpose |
|------|-------|---------|
| Login | `/login` | Email + password form. Uses `supabase.auth.signInWithPassword()`. Redirect to `/` on success. |
| Setup | `/setup` | Magic link landing page. User sets name + password via `supabase.auth.updateUser()`. One-time use. |

**Auth context provider (`web/src/lib/auth-context.tsx`):**
- Wrap app layout
- On mount: check `supabase.auth.getSession()`
- If no session: redirect to `/login`
- Store user + role in React context
- Inject `Authorization: Bearer ${token}` into `apiFetch()` calls

**Admin invite form:**
- Add to Settings page (admin-only section)
- Simple form: email input + role dropdown (admin/viewer) + Send Invite button
- Calls `POST /api/v1/admin/invite`

**Route protection:**
- All pages require auth (no public pages)
- Admin-only sections: pipeline controls (trigger/stop/pause), Settings admin panel, eval run triggers
- Viewer sees: all dashboards, posting explorer, brand intel, eval results (read-only)

### 6.6 RLS Policies

**Single Alembic migration: enable RLS + create policies on all tables.**

Alembic cannot auto-detect RLS — this is a hand-written SQL migration.

**Access tiers:**

| Tier | Tables | Viewer | Admin | service_role |
|------|--------|--------|-------|--------------|
| Dimension | companies, brands, retailers, markets, location_mappings | SELECT | SELECT | INSERT, UPDATE |
| Fact | postings, posting_snapshots, posting_enrichments, posting_brand_mentions | SELECT | SELECT | INSERT (snapshots: strict append-only, no UPDATE/DELETE), UPDATE (enrichments only) |
| Aggregation | 7 `agg_*` tables | SELECT | SELECT | TRUNCATE + INSERT |
| Run tracking | scrape_runs, enrichment_runs | SELECT | SELECT | INSERT, UPDATE |
| Eval | eval_runs, eval_samples, eval_results, eval_prompts, eval_corpus, eval_comparisons, eval_field_reviews | SELECT | SELECT, INSERT, UPDATE | INSERT, UPDATE |
| Auth | users | SELECT own row | SELECT all, UPDATE role, DELETE | Full access |

**Key implementation detail:**
- Application API requests use the user's JWT → RLS policies filter automatically
- Background orchestrators (scrape, enrich, aggregate, scheduler) use `service_role` key → bypass RLS entirely
- This requires two separate database connection configurations:
  - `async_session_factory` (app traffic) — uses connection string with user-scoped role
  - `service_session_factory` (background jobs) — uses connection string with service_role key
- Supabase provides both connection strings in the project dashboard

### 6.7 Auth Testing Strategy

| Test type | Auth handling | When |
|-----------|-------------|------|
| Unit tests (pytest, no DB) | `AUTH_DISABLED=true` in test settings → `get_current_user` returns stub User | M7 |
| Role-specific unit tests | Mock `get_current_user` to return `User(role="admin")` or `User(role="viewer")` | M7 |
| Integration tests (live DB) | `AUTH_DISABLED=true` (integration tests focus on DB queries, not auth) | M7 |
| E2E auth flow tests | Playwright against test Supabase project | Deferred to M8 |

### 6.8 Route Access Matrix

After auth is implemented, every endpoint has a required role:

| Route | Method | Required Role |
|-------|--------|---------------|
| `/health` | GET | **Public** (no auth) |
| `/api/v1/companies` | GET | Viewer+ |
| `/api/v1/postings` | GET | Viewer+ |
| `/api/v1/postings/{id}` | GET | Viewer+ |
| `/api/v1/aggregation/velocity` | GET | Viewer+ |
| `/api/v1/aggregation/brand-timeline` | GET | Viewer+ |
| `/api/v1/aggregation/pay-benchmarks` | GET | Viewer+ |
| `/api/v1/aggregation/lifecycle` | GET | Viewer+ |
| `/api/v1/aggregation/churn-signals` | GET | Viewer+ |
| `/api/v1/aggregation/coverage-gaps` | GET | Viewer+ |
| `/api/v1/aggregation/agency-overlap` | GET | Viewer+ |
| `/api/v1/aggregation/trigger` | POST | **Admin** |
| `/api/v1/scrape/trigger` | POST | **Admin** |
| `/api/v1/scrape/status` | GET | Viewer+ |
| `/api/v1/scrape/pause` | POST | **Admin** |
| `/api/v1/scrape/resume` | POST | **Admin** |
| `/api/v1/scrape/stop` | POST | **Admin** |
| `/api/v1/scrape/force-stop` | POST | **Admin** |
| `/api/v1/enrich/trigger` | POST | **Admin** |
| `/api/v1/enrich/pass1/trigger` | POST | **Admin** |
| `/api/v1/enrich/pass2/trigger` | POST | **Admin** |
| `/api/v1/enrich/status` | GET | Viewer+ |
| `/api/v1/enrich/status/{run_id}` | GET | Viewer+ |
| `/api/v1/pipeline/status` | GET | Viewer+ |
| `/api/v1/pipeline/runs` | GET | Viewer+ |
| `/api/v1/scheduler/status` | GET | Viewer+ |
| `/api/v1/scheduler/jobs/{id}/trigger` | POST | **Admin** |
| `/api/v1/scheduler/jobs/{id}/pause` | POST | **Admin** |
| `/api/v1/scheduler/jobs/{id}/resume` | POST | **Admin** |
| `/api/v1/eval/corpus` | GET | Viewer+ |
| `/api/v1/eval/runs` | GET | Viewer+ |
| `/api/v1/eval/runs` | POST | **Admin** |
| `/api/v1/eval/runs/{id}` | GET | Viewer+ |
| `/api/v1/eval/runs/{id}/results` | GET | Viewer+ |
| `/api/v1/eval/runs/{id}/field-accuracy` | GET | Viewer+ |
| `/api/v1/eval/runs/{id}/field-reviews` | GET/POST | GET: Viewer+, POST: **Admin** |
| `/api/v1/eval/leaderboard-data` | GET | Viewer+ |
| `/api/v1/eval/comparisons` | GET/POST | GET: Viewer+, POST: **Admin** |
| `/api/v1/eval/elo` | GET | Viewer+ |
| `/api/v1/eval/models` | GET | Viewer+ |
| `/api/v1/admin/invite` | POST | **Admin** |

---

## 7. Phase D: Infrastructure (Sprint 2)

**Goal:** Provision shared infrastructure that unblocks future features.
**Dependencies:** Phase C complete (auth needed for rate limiting).
**Effort:** Small-Medium (3-5 days)

### 7.1 Redis (OPS-06)

| Item | Detail |
|------|--------|
| Install | `apt install redis-server` on DO droplet |
| Config | Bind `127.0.0.1:6379`, no auth (localhost only), maxmemory 256MB |
| Service | `systemctl enable redis-server` |
| Python | Add `redis[hiredis]` to `pyproject.toml` |
| Unlocks | PERF-04 (API caching), SEC-04 (rate limiting), ARCH-05 (multi-worker locks), arq (job queue, M8) |

### 7.2 Rate Limiting (SEC-04)

| Item | Detail |
|------|--------|
| Dependency | `slowapi` (or custom middleware) |
| Requires | SEC-01 (auth) + OPS-06 (Redis) |
| Policy | Per-authenticated-user limits: 60 req/min for GET, 10 req/min for POST (pipeline triggers) |
| Scope | All `/api/v1/` routes. `/health` exempt. |

### 7.3 DB-Backed Run Tracking (ARCH-02)

| Item | Detail |
|------|--------|
| Migration | Add `last_heartbeat_at` column to `scrape_runs` and `enrichment_runs` |
| Change | Orchestrators write heartbeat to DB every 30s during active runs |
| Zombie detection | On startup, mark runs with stale heartbeats (>5 min) as `FAILED` |
| Remove | Global `_runs` dicts in scrape/enrichment orchestrators |

### 7.4 Service Layer Extraction (ARCH-01, incremental)

| Item | Detail |
|------|--------|
| Start with | `src/compgraph/services/posting_service.py` — extract query building from `postings.py` routes |
| Pattern | Service class injected via FastAPI `Depends`. Routes become thin (validate input → call service → return response). |
| Scope | Postings routes only in M7. Expand to other routes in M8. |
| Benefit | Testable without HTTP layer. Query logic reusable across routes. |

---

## 8. Phase E: Feature Sprint

**Goal:** High-value UX features that require Phase C auth.
**Dependencies:** Phase C complete.
**Effort:** Medium (1-2 weeks)

### 8.1 Evidence Trails (UX-01)

**Prerequisites (3 schema/pipeline changes before frontend work):**

1. **Alembic migration:** Add `matched_text` (Text, nullable) and `posting_section` (String(50), nullable) to `posting_brand_mentions`
2. **Pass 2 enrichment prompt change:** Update `prompts/pass2_v1.py` to capture the exact text span and section (title/description/qualifications) that triggered the brand match
3. **Backfill script:** `scripts/backfill_brand_evidence.py` — re-enrich existing mentions to populate new columns (or mark as "legacy — no evidence")

**Frontend components:**
- `EvidenceBadge` — shows evidence count per brand mention
- `SourcePostingLink` — deep-link to posting with highlighted matched text
- Display in Brand Intel view and Posting Detail view

### 8.2 Skeleton Loaders (UX-05)

Replace layout-shifting spinners with dimension-accurate CSS skeleton loaders on:
- Dashboard page (velocity charts, brand timeline)
- Posting Explorer (table rows)
- Brand Intel (brand cards)

### 8.3 SWR for New Components (UX-03, partial)

- Install `swr` npm dependency
- Use SWR for any new M7 real-time components (auth-gated dashboards, eval progress)
- Refactor Settings page polling (`settings/page.tsx:657-699`) from `setTimeout` chains to SWR `refreshInterval`
- Do NOT migrate existing load-once pages (competitors, market, hiring)

---

## 9. Sprint Sequence & Dependencies

```
Week 1-2: Phase A (API v1 prefix + quick wins)
          Phase B.0 (eval corpus bootstrap — can run in parallel)

Week 2-4: Phase B.1 (eval runner merge — largest single task)
          Phase C.1-C.3 (auth config + middleware + migration — in parallel with eval)

Week 4-5: Phase C.4-C.6 (frontend auth pages + RLS policies)
          Phase B cleanup (delete eval/ standalone app)

Week 5-6: Phase D (Redis + rate limiting + run tracking + service layer)

Week 6-8: Phase E (evidence trails + skeleton loaders + SWR)
          Phase B.2 (comparison engine — after eval runs exist)

Week 8+:  Phase B.3 (guided UX — after comparison engine proves out)
```

**Critical path:** Phase A → Phase C → Phase D → Phase E
**Parallel track:** Phase B (eval) runs alongside everything, converges at Phase E

**Blocking dependencies (cannot start until prerequisite ships):**

| Item | Blocked By |
|------|-----------|
| Phase C (auth) | Phase A (needs `/api/v1/` prefix) |
| Phase D.2 (rate limiting) | Phase C (auth) + Phase D.1 (Redis) |
| Phase D.3 (DB-backed runs) | Alembic migration for `last_heartbeat_at` |
| Phase E.1 (evidence trails) | Migration + prompt change + backfill |
| Phase B.2 (comparison engine) | Phase B.1 (runner must work first) |
| Phase B.3 (guided UX) | Phase B.2 (comparisons must exist) |

---

## 10. Deferred to M8+

| ID | Item | Reason |
|----|------|--------|
| ARCH-04 | Auto-generate TS types from Pydantic | Frontend types are view models, not DB mirrors |
| ARCH-05 | Multi-worker locks | Single-worker uvicorn is fine at current scale. Needs Redis (OPS-06). |
| LLM-02 | Confidence decay engine | Product feature, needs user feedback first |
| LLM-03 | Cross-source triangulation | YAGNI — no second data source planned |
| UX-06 | HITL feedback loop | Needs Phase B.2 (eval comparison engine) |
| UX-07 | CRM push integration | No user request |
| UX-08 | Responsive layout audit | Low priority |
| QA-03 | Factory-boy test factories | 703 tests at 82% coverage — fixtures work |
| QA-04 | Structured LLM telemetry | Needs Grafana/Prometheus (not provisioned) |
| QA-05 | Visual regression testing | Insufficient UI churn |
| QA-06 | Load testing (k6) | After multi-worker scaling |
| OPS-01 | Infrastructure as Code | 1 droplet doesn't justify Terraform |
| OPS-03 | Log retention | Address when disk usage becomes a problem |
| PERF-02 | Parallel aggregation | Address when nightly window exceeds SLA |
| PERF-03 | Anthropic Batch API | Needs eval tool quality validation first |
| PERF-04 | API caching (Redis) | After Redis provisioned + traffic justifies it |
| SCRP-02 | Blind redirect following | Low impact currently |
| SCRP-03 | ATS drift detector | No company has changed ATS yet |
| SEC-05 | Secret rotation automation | Manual rotation is fine at current key count |
| SCALE-001 | Hardcoded scraper params | Move to config.py when tuning is needed |
| SCALE-002 | Anthropic Batch API | Same as PERF-03 |

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Supabase Auth magic link emails land in spam | Medium | High (blocks onboarding) | Test with real email domains before launch. Configure SPF/DKIM if using custom domain. |
| LiteLLM dependency conflicts with existing packages | Low | Medium (blocks eval) | Pin version. Test in isolated venv first. |
| OpenRouter rate limits during eval runs | Low | Low (eval is batch, not real-time) | Add retry with exponential backoff in `providers.py`. |
| RLS policies break background orchestrators | Medium | High (pipeline stops) | Verify all orchestrators use `service_role` connection. Test with integration tests before enabling RLS. |
| `/api/v1/` 308 redirect breaks POST requests | Low | High (pipeline controls fail) | 308 (not 301/302) preserves HTTP method. Test all POST endpoints through redirect. |
| Eval corpus is empty or too small for meaningful comparison | Medium | Medium (eval tool is useless) | Verify `generate_eval_corpus.py` produces >50 entries. If not, manually seed from production postings. |
| Auth testing bypass (`AUTH_DISABLED`) accidentally enabled in production | Low | Critical (no auth) | Add startup check: if `AUTH_DISABLED=true` and `ENV=production`, refuse to start. |

---

## 12. Definition of Done (M7)

M7 is complete when:

- [ ] All API endpoints are behind `/api/v1/` prefix
- [ ] All API endpoints require authentication (except `/health`)
- [ ] Admin and viewer roles enforced on all routes per the access matrix
- [ ] Invite flow works: admin invites → magic link → user provisions → user logs in
- [ ] RLS enabled on all tables with correct tier policies
- [ ] Eval tool "Run Evaluation" button triggers actual LLM calls via OpenRouter
- [ ] Eval results write to Postgres (not aiosqlite)
- [ ] Eval corpus has >0 entries with ground truth data
- [ ] Standalone `eval/` directory is deleted
- [ ] `CG-QUAL-001` fixed (timezone-aware datetime)
- [ ] Settings page destructive actions have ConfirmDialog
- [ ] Redis provisioned on droplet
- [ ] Rate limiting active on API
- [ ] Run tracking is DB-backed (no in-memory `_runs` dicts)
- [ ] Backend tests pass at >50% coverage
- [ ] Frontend tests pass at >50% coverage
- [ ] All CI checks green
- [ ] Deployed to dev.compgraph.io and compgraph.vercel.app

---

## Appendix A: New Dependencies

| Package | Destination | Purpose |
|---------|-------------|---------|
| `litellm` | `pyproject.toml` (root) | LLM provider abstraction for eval tool |
| `python-jose[cryptography]` | `pyproject.toml` (root) | JWT decoding for Supabase Auth |
| `redis[hiredis]` | `pyproject.toml` (root) | Caching, rate limiting, future job queue |
| `slowapi` | `pyproject.toml` (root) | API rate limiting middleware |
| `@supabase/supabase-js` | `web/package.json` | Supabase Auth client SDK |
| `swr` | `web/package.json` | Server state management (new components + Settings) |

## Appendix B: New Environment Variables

| Variable | Type | Where | Purpose |
|----------|------|-------|---------|
| `SUPABASE_JWT_SECRET` | SecretStr | `.env` + 1Password | JWT validation for auth middleware |
| `OPENROUTER_API_KEY` | SecretStr | `.env` + 1Password | LLM provider for eval tool |
| `AUTH_DISABLED` | bool | `.env` (test only) | Bypass auth in test environment |
| `EVAL_CONCURRENCY` | int | `.env` (optional) | Concurrent LLM calls in eval (default: 5) |

## Appendix C: New Files to Create

| File | Purpose |
|------|---------|
| `src/compgraph/api/auth.py` | JWT middleware, `get_current_user`, `require_admin` |
| `src/compgraph/eval/logic.py` | Ported eval runner (from `eval/eval/runner.py`) |
| `src/compgraph/eval/providers.py` | LiteLLM wrapper (from `eval/eval/providers.py`) |
| `src/compgraph/eval/prompts/pass1_v1.py` | Pass 1 prompt (from `eval/eval/prompts/`) |
| `src/compgraph/eval/prompts/pass2_v1.py` | Pass 2 prompt (from `eval/eval/prompts/`) |
| `src/compgraph/services/posting_service.py` | Query builder extracted from postings routes |
| `scripts/bootstrap_eval_corpus.py` | Load corpus.json into Postgres `eval_corpus` table |
| `web/src/app/login/page.tsx` | Login page |
| `web/src/app/setup/page.tsx` | Account provisioning page (magic link landing) |
| `web/src/lib/auth-context.tsx` | Auth context provider + route protection |
| `alembic/versions/xxxx_add_auth_uid.py` | Add `auth_uid` to users table |
| `alembic/versions/xxxx_enable_rls.py` | Enable RLS + create policies on all tables |
| `alembic/versions/xxxx_add_heartbeat.py` | Add `last_heartbeat_at` to run tables |
| `alembic/versions/xxxx_add_evidence_cols.py` | Add `matched_text` + `posting_section` to brand mentions |

## Appendix D: Cross-References

| Document | Location | Relationship |
|----------|----------|-------------|
| Gap Analysis (master) | `docs/reports/gap-analysis-consolidated.md` | Source audit — Sections 1-9 findings, Section 10 dependency map, Section 11 PM disposition |
| Strategic Roadmap | `docs/reports/strategic-roadmap-refined.md` | Section 7 PM POV on 13 strategic findings |
| Code Review Log | `docs/reports/code-review-log.md` | Detailed findings with status tracking |
| Engineering Disagreements | `docs/reports/2026-02-24-engineering-disagreements.md` | ARCH-03, UX-03, QA-03 resolutions |
| Gemini Implementation POVs | `docs/reports/2026-02-24-implementation-plans-pov.md` | Gemini proposals for auth, eval, v1 cutover |
| Eval Tool CLAUDE.md | `eval/CLAUDE.md` | Standalone eval app docs (delete after Phase B) |
| Frontend Conventions | `web/CLAUDE.md` | Test patterns, design tokens, deployment |
