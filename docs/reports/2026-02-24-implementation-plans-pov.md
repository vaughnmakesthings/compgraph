# M7 Foundation: Strategic Implementation POVs & Plans

**Date:** 2026-02-24  
**Author:** Gemini CLI (Engineering Swarm)  
**Subject:** Implementation Blueprints for Auth, Eval Consolidation, and API Versioning

---

## 1. Supabase Auth Integration Design
**Goal:** Transition from unauthenticated endpoints to a production-grade, RBAC-enabled JWT flow.

### Flow Trace
1.  **Supabase Config**: Retrieve `SUPABASE_JWT_SECRET` from 1Password and add to `.env`.
2.  **JWT Middleware**: Create `src/compgraph/api/auth.py`. Implement a `VerifyJWT` middleware that decodes the bearer token from the `Authorization` header using the secret.
3.  **`get_current_user` Dependency**:
    -   Add `src/compgraph/api/deps.py:get_current_user`.
    -   This dependency will extract the `sub` (UUID) and `role` from the decoded JWT.
    -   It will verify the user exists in the `public.users` table (or JIT-create a skeleton record).
4.  **RLS Policies**:
    -   Add a new Alembic migration: `alembic/versions/[id]_enable_rls.py`.
    -   `ALTER TABLE postings ENABLE ROW LEVEL SECURITY;`
    -   `CREATE POLICY "Allow authenticated read" ON postings FOR SELECT TO authenticated USING (true);`
    -   `CREATE POLICY "Admin only controls" ON scrape_runs FOR ALL TO authenticated USING (auth.jwt() ->> 'role' = 'service_role' OR auth.jwt() ->> 'email' LIKE '%@mosaic.com');`
5.  **Frontend Login**:
    -   `web/src/app/login/page.tsx`: Simple form using `@supabase/auth-ui-react`.
    -   Update `web/src/lib/api-client.ts` to include the `Authorization: Bearer ${token}` header from `supabase.auth.getSession()`.

---

## 2. Eval Tool Consolidation: Migration Plan
**Goal:** Eliminate the split-brain architecture and move to the integrated Postgres-backed engine.

### File Mapping & Migration
| Source (`eval/eval/`) | Destination (`src/compgraph/eval/`) | Transformation Required |
| :--- | :--- | :--- |
| `runner.py` | `logic.py` | Refactor `run_evaluation` to accept `AsyncSession` (Postgres) instead of `EvalStore`. |
| `providers.py` | `providers.py` | Keep `litellm` wrapper; ensure `OPENROUTER_API_KEY` is pulled from `Settings`. |
| `schemas.py` | `schemas.py` | Align Pydantic models with `models.py` column names. |
| `prompts/*.py` | `prompts/*.py` | No changes needed; just relative import fix. |

### `router.py` (Line 529 Replacement)
Instead of a stub, `create_run` will now:
```python
# src/compgraph/eval/router.py
from compgraph.eval.logic import run_evaluation

@router.post("/runs")
async def create_run(body: RunCreate, db: DbDep):
    # 1. Initialize DB record in eval_runs
    # 2. Launch background task
    task = asyncio.create_task(run_evaluation(db, ...))
    _background_tasks.add(task)
    # 3. Use the tracking_id for frontend polling
```

### Config & Ground Truth
-   **Config**: Add `OPENROUTER_API_KEY: SecretStr` to `src/compgraph/config.py`.
-   **Ground Truth Strategy**: 
    1.  Create `scripts/bootstrap_eval_corpus.py`.
    2.  Read `eval/data/corpus.json` and bulk-insert into the Postgres `eval_corpus` table using `INSERT ON CONFLICT DO NOTHING`.
    3.  Admin UI will then allow "Non-Technical" users to update the `reference_pass1/2` JSON blobs directly in the DB.

---

## 3. The `/api/v1/` Cutover Sequence
**Goal:** Atomic transition to versioned APIs without breaking the production frontend.

### Affected File Map
1.  **Backend Routes**: `src/compgraph/main.py`
2.  **Infrastructure**: `web/vercel.json`
3.  **Frontend Client**: `web/src/lib/constants.ts` and `api-client.ts`
4.  **Tests**: `tests/test_api_*.py`

### Atomic Changeset
**Change 1 (Backend - `main.py`):**
```python
# Wrap all internal routes in a v1 router
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(scrape_router)
# ... all other routers ...
app.include_router(v1_router)
```

**Change 2 (Infrastructure - `vercel.json`):**
```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://dev.compgraph.io/api/v1/:path*" }
  ]
}
```
*Note: This rewrite ensures the existing frontend code (pointing to `/api/...`) continues to work while the backend is now at `/api/v1/...`.*

**Change 3 (Frontend - `api-client.ts`):**
Update `API_BASE` in `web/src/lib/constants.ts` to include `/v1`.
*Sequence: Deploy backend + vercel.json first, then merge frontend changes.*
