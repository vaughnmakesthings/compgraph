# API Versioning (#199) + Frontend Auth (#208) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move all API routes under `/api/v1/` prefix, then wire the existing frontend auth UI to Supabase Auth JS with session management, token injection, and route protection.

**Architecture:** Two parallel branches — #199 (backend prefix refactor + frontend path update) merges first, then #208 (Supabase client integration into existing auth UI stubs) rebases and merges. No new pages or components are created; all auth UI already exists and needs wiring only.

**Tech Stack:** FastAPI `APIRouter` prefix nesting, `@supabase/supabase-js` browser client, React context for session state, module-level token bridge for `apiFetch`.

**Design doc:** `docs/plans/2026-02-25-auth-versioning-design.md`

---

## Part 1: Issue #199 — API Versioning

**Branch:** `feat/issue-199-api-versioning`
**Agent:** `python-backend-developer`

### Task 1: Create worktree and branch

**Step 1:** Create isolated worktree

```bash
cd /Users/vmud/Documents/dev/projects/compgraph
git worktree add ../compgraph-199 -b feat/issue-199-api-versioning main
cd ../compgraph-199
uv sync
```

**Step 2:** Verify test baseline

```bash
uv run pytest -x -q --tb=short -m "not integration" --no-cov
```

Expected: All tests pass (789+).

---

### Task 2: Strip `/api/` prefix from individual routers

**Files:**
- Modify: `src/compgraph/api/routes/scrape.py:22` — change `prefix="/api/scrape"` to `prefix="/scrape"`
- Modify: `src/compgraph/api/routes/enrich.py:31` — change `prefix="/api/enrich"` to `prefix="/enrich"`
- Modify: `src/compgraph/api/routes/scheduler.py:17` — change `prefix="/api/scheduler"` to `prefix="/scheduler"`
- Modify: `src/compgraph/api/routes/pipeline.py:24` — change `prefix="/api/pipeline"` to `prefix="/pipeline"`
- Modify: `src/compgraph/api/routes/aggregation.py:21` — change `prefix="/api/aggregation"` to `prefix="/aggregation"`
- Modify: `src/compgraph/api/routes/companies.py:10` — change `prefix="/api/companies"` to `prefix="/companies"`
- Modify: `src/compgraph/api/routes/admin.py:20` — change `prefix="/api/v1/admin"` to `prefix="/admin"`

**Step 1:** Edit each router file — change the `prefix=` argument on the `APIRouter()` constructor.

Every router follows the same pattern. Example for `scrape.py`:

```python
# Before
router = APIRouter(prefix="/api/scrape", tags=["scrape"])

# After
router = APIRouter(prefix="/scrape", tags=["scrape"])
```

For `admin.py` specifically:

```python
# Before
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# After
router = APIRouter(prefix="/admin", tags=["admin"])
```

**Step 2:** Do NOT run tests yet — they will fail because `main.py` still mounts routers directly on `app`, so routes like `/scrape/trigger` won't resolve to any valid path. That's expected and fixed in Task 3.

---

### Task 3: Create central v1 router in main.py

**Files:**
- Modify: `src/compgraph/main.py:1-88`

**Step 1:** Replace the router mounting block (lines 78-87) with a central `v1_router`:

```python
from fastapi import APIRouter, FastAPI
# ... existing imports ...

# After app creation and middleware setup (after line 76):

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(scrape_router)
v1_router.include_router(enrich_router)
v1_router.include_router(scheduler_router)
v1_router.include_router(pipeline_router)
v1_router.include_router(aggregation_router)
v1_router.include_router(companies_router)
v1_router.include_router(postings_router, prefix="/postings", tags=["postings"])
v1_router.include_router(eval_router, prefix="/eval", tags=["eval"])
v1_router.include_router(admin_router)

app.include_router(health_router)  # stays unversioned at /health
app.include_router(v1_router)
```

Note: `APIRouter` import already exists via `admin.py` etc. but must be imported in `main.py` directly.

**Step 2:** Run tests to see how many break (expected: ~90 path assertions fail)

```bash
uv run pytest -x -q --tb=line -m "not integration" --no-cov 2>&1 | head -30
```

Expected: Many failures with `404` or path mismatch errors.

---

### Task 4: Update backend test paths to `/api/v1/`

**Files (9 test files, ~90 path occurrences):**
- `tests/test_scrape_routes.py` — 14 occurrences
- `tests/test_postings_api.py` — 16 occurrences
- `tests/test_pipeline_status.py` — 14 occurrences
- `tests/test_enrichment_pass1.py` — 12 occurrences
- `tests/test_enrichment_pass2.py` — 2 occurrences
- `tests/test_eval_router.py` — 11 occurrences
- `tests/test_api_aggregation.py` — 8 occurrences
- `tests/test_scheduler.py` — 7 occurrences
- `tests/test_auth_middleware.py` — 6 occurrences (already `/api/v1/admin`, verify no changes needed)

**Step 1:** For each test file, find-and-replace `"/api/` with `"/api/v1/` in test path strings. Be careful:
- `"/api/v1/admin` paths in `test_auth_middleware.py` are ALREADY correct — don't double-prefix
- `"/health"` paths should NOT be changed (unversioned)

The replacement rule: `"/api/` → `"/api/v1/` EXCEPT where `"/api/v1/` already exists.

**Step 2:** Run full test suite

```bash
uv run pytest -x -q --tb=short -m "not integration" --no-cov
```

Expected: All tests pass.

**Step 3:** Run lint and typecheck

```bash
uv run ruff check src/ tests/ --fix && uv run ruff format src/ tests/
uv run mypy src/compgraph/
```

Expected: Clean.

**Step 4:** Commit

```bash
git add src/compgraph/main.py src/compgraph/api/routes/*.py tests/
git commit -m "feat(api): add /api/v1/ prefix via central v1 router (#199)

Move all API routes under /api/v1/ using a central APIRouter.
Individual routers stripped of /api/ prefix. Health stays
unversioned. Test paths updated (~90 assertions).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Add backward-compat 308 redirect

**Files:**
- Modify: `src/compgraph/main.py`
- Create: `tests/test_legacy_redirect.py`

**Step 1:** Write test for the redirect

```python
# tests/test_legacy_redirect.py
"""Verify /api/* 308-redirects to /api/v1/* for backward compat."""
import pytest
from httpx import AsyncClient

from compgraph.main import app


@pytest.mark.anyio
async def test_legacy_api_path_redirects_to_v1(client):
    """GET /api/pipeline/status should 308 to /api/v1/pipeline/status."""
    response = await client.get("/api/pipeline/status", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/api/v1/pipeline/status"


@pytest.mark.anyio
async def test_legacy_redirect_preserves_query_params(client):
    """GET /api/postings?limit=10 should 308 with query string preserved."""
    response = await client.get("/api/postings?limit=10", follow_redirects=False)
    assert response.status_code == 308
    assert "/api/v1/postings?limit=10" in response.headers["location"]


@pytest.mark.anyio
async def test_health_not_redirected(client):
    """GET /health should not be redirected (unversioned)."""
    response = await client.get("/health")
    assert response.status_code == 200
```

**Step 2:** Run test to verify failure

```bash
uv run pytest tests/test_legacy_redirect.py -v --no-cov
```

Expected: FAIL (no redirect handler exists yet).

**Step 3:** Add redirect handler to `main.py` after the `app.include_router(v1_router)` line:

```python
from fastapi.responses import RedirectResponse
from fastapi import Request

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def legacy_api_redirect(request: Request, path: str):
    """Temporary 308 redirect from /api/* to /api/v1/* for backward compat."""
    query = f"?{request.query_params}" if request.query_params else ""
    return RedirectResponse(
        url=f"/api/v1/{path}{query}",
        status_code=308,
    )
```

**Step 4:** Run tests

```bash
uv run pytest tests/test_legacy_redirect.py -v --no-cov
uv run pytest -x -q --tb=short -m "not integration" --no-cov
```

Expected: All pass.

**Step 5:** Commit

```bash
git add src/compgraph/main.py tests/test_legacy_redirect.py
git commit -m "feat(api): add 308 redirect from /api/* to /api/v1/* (#199)

Temporary backward-compat redirect preserving method and query params.
Will be removed after frontend is confirmed on versioned paths.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Update frontend api-client.ts paths

**Files:**
- Modify: `web/src/lib/api-client.ts` — all ~40 path strings
- Modify: `web/src/test/api-client.test.ts` — all path assertions

**Step 1:** In `api-client.ts`, find-and-replace `'/api/` with `'/api/v1/` for every path string. Do NOT change `'/health'`.

Verify list of changes (every line with a path):
- Line 53: `'/api/pipeline/status'` → `'/api/v1/pipeline/status'`
- Line 55: `'/api/pipeline/runs'` → `'/api/v1/pipeline/runs'`
- Line 61: `/api/aggregation/velocity` → `/api/v1/aggregation/velocity`
- Line 68: `/api/aggregation/brand-timeline` → `/api/v1/aggregation/brand-timeline`
- Line 70: `'/api/aggregation/pay-benchmarks'` → `'/api/v1/aggregation/pay-benchmarks'`
- Line 72: `'/api/aggregation/lifecycle'` → `'/api/v1/aggregation/lifecycle'`
- Line 74: `'/api/aggregation/churn-signals'` → `'/api/v1/aggregation/churn-signals'`
- Line 76: `'/api/aggregation/coverage-gaps'` → `'/api/v1/aggregation/coverage-gaps'`
- Line 78: `'/api/aggregation/agency-overlap'` → `'/api/v1/aggregation/agency-overlap'`
- Line 81: `'/api/aggregation/trigger'` → `'/api/v1/aggregation/trigger'`
- Line 100: `/api/postings` → `/api/v1/postings`
- Line 103: `/api/postings/` → `/api/v1/postings/`
- Line 105: `'/api/eval/runs'` → `'/api/v1/eval/runs'`
- Lines 107-160: all `/api/eval/*` → `/api/v1/eval/*`
- Line 163: `'/api/companies'` → `'/api/v1/companies'`
- Lines 167-182: all `/api/scrape/*` → `/api/v1/scrape/*`
- Lines 186-189: all `/api/enrich/*` → `/api/v1/enrich/*`
- Lines 193-201: all `/api/scheduler/*` → `/api/v1/scheduler/*`

**Step 2:** In `api-client.test.ts`, update all path assertions:
- Replace `'/api/pipeline/status'` with `'/api/v1/pipeline/status'` (and similar for all paths)
- Replace regex patterns: `/\/api\/postings$/` → `/\/api\/v1\/postings$/`
- Replace regex patterns: `/\/api\/aggregation\/velocity$/` → `/\/api\/v1\/aggregation\/velocity$/`
- Replace regex patterns: `/\/api\/aggregation\/brand-timeline$/` → `/\/api\/v1\/aggregation\/brand-timeline$/`

**Step 3:** Run frontend tests

```bash
cd web && npm test
```

Expected: All 233+ tests pass.

**Step 4:** Run frontend lint + typecheck

```bash
npm run lint && npm run typecheck
```

Expected: Clean.

**Step 5:** Commit

```bash
git add web/src/lib/api-client.ts web/src/test/api-client.test.ts
git commit -m "feat(web): update API client paths to /api/v1/ (#199)

All ~40 endpoint paths in api-client.ts and their test assertions
updated to use versioned /api/v1/ prefix. Health stays at /health.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Final validation and PR

**Step 1:** Run full backend + frontend test suites

```bash
uv run pytest -x -q --tb=short -m "not integration" --no-cov
cd web && npm test && npm run lint && npm run typecheck && npm run build
```

Expected: All pass, build succeeds.

**Step 2:** Push and create draft PR

```bash
git push -u origin feat/issue-199-api-versioning
gh pr create --draft --title "feat(api): add /api/v1/ prefix for all routes (#199)" --body "$(cat <<'EOF'
## Summary
- Central `v1_router` with `/api/v1/` prefix in `main.py`
- Individual router prefixes stripped to relative paths
- 308 backward-compat redirect from `/api/*` → `/api/v1/*`
- Frontend `api-client.ts` paths updated to versioned endpoints
- ~90 backend test assertions + ~40 frontend test assertions updated

Closes #199

## Test plan
- [ ] All backend unit tests pass with versioned paths
- [ ] Legacy redirect returns 308 with correct location header
- [ ] Frontend tests pass with updated paths
- [ ] `npm run build` succeeds (no broken imports)
- [ ] Health endpoint remains at `/health` (unversioned)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Part 2: Issue #208 — Frontend Auth Pages

**Branch:** `feat/issue-208-frontend-auth`
**Agent:** `react-frontend-developer`

### Task 8: Create worktree and branch

**Step 1:** Create isolated worktree

```bash
cd /Users/vmud/Documents/dev/projects/compgraph
git worktree add ../compgraph-208 -b feat/issue-208-frontend-auth main
cd ../compgraph-208/web
npm install
```

**Step 2:** Verify test baseline

```bash
npm test
```

Expected: All 233+ tests pass.

---

### Task 9: Install `@supabase/supabase-js`

**Files:**
- Modify: `web/package.json`

**Step 1:** Install the package

```bash
cd web && npm install @supabase/supabase-js
```

**Step 2:** Verify it installed

```bash
grep supabase web/package.json
```

Expected: `"@supabase/supabase-js": "^2.x.x"` in dependencies.

**Step 3:** Run tests to confirm nothing broke

```bash
npm test
```

Expected: All pass.

**Step 4:** Commit

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): install @supabase/supabase-js (#208)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Create Supabase client singleton

**Files:**
- Create: `web/src/lib/supabase.ts`
- Create: `web/.env.local.example`

**Step 1:** Write test for the module

Create `web/src/test/supabase-client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("supabase client", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("exports null when window is undefined (SSR)", async () => {
    const originalWindow = globalThis.window;
    // @ts-expect-error — simulate SSR
    delete globalThis.window;
    const { supabase } = await import("@/lib/supabase");
    expect(supabase).toBeNull();
    globalThis.window = originalWindow;
  });

  it("exports a SupabaseClient when window exists", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
    const { supabase } = await import("@/lib/supabase");
    expect(supabase).not.toBeNull();
    expect(supabase).toHaveProperty("auth");
  });
});
```

**Step 2:** Run test to verify failure

```bash
npm test -- src/test/supabase-client.test.ts
```

Expected: FAIL — module doesn't exist.

**Step 3:** Create `web/src/lib/supabase.ts`:

```typescript
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export const supabase: SupabaseClient | null =
  typeof window !== "undefined"
    ? createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      )
    : null;
```

**Step 4:** Create `web/.env.local.example`:

```
# Supabase Auth — get values from 1Password "Supabase Auth Keys" (DEV vault)
NEXT_PUBLIC_SUPABASE_URL=https://tkvxyxwfosworwqxesnz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 5:** Run test

```bash
npm test -- src/test/supabase-client.test.ts
```

Expected: PASS.

**Step 6:** Commit

```bash
git add web/src/lib/supabase.ts web/.env.local.example web/src/test/supabase-client.test.ts
git commit -m "feat(web): add Supabase client singleton with SSR guard (#208)

Returns null during SSR (no window/localStorage), live client on browser.
Includes .env.local.example for developer onboarding.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 11: Create auth token bridge module

**Files:**
- Create: `web/src/lib/auth-token.ts`

**Step 1:** Write test `web/src/test/auth-token.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { getAuthToken, setAuthToken } from "@/lib/auth-token";

describe("auth-token bridge", () => {
  beforeEach(() => {
    setAuthToken(null);
  });

  it("returns null by default", () => {
    expect(getAuthToken()).toBeNull();
  });

  it("returns the token after setAuthToken", () => {
    setAuthToken("jwt-abc-123");
    expect(getAuthToken()).toBe("jwt-abc-123");
  });

  it("clears the token when set to null", () => {
    setAuthToken("jwt-abc-123");
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });
});
```

**Step 2:** Run test to verify failure

```bash
npm test -- src/test/auth-token.test.ts
```

Expected: FAIL — module doesn't exist.

**Step 3:** Create `web/src/lib/auth-token.ts`:

```typescript
/**
 * Module-level token bridge between auth context and api-client.
 * Updated by AuthProvider on session changes. Read synchronously by apiFetch.
 * No Supabase dependency — keeps api-client.ts decoupled from auth.
 */
let currentToken: string | null = null;

export function setAuthToken(token: string | null): void {
  currentToken = token;
}

export function getAuthToken(): string | null {
  return currentToken;
}
```

**Step 4:** Run test

```bash
npm test -- src/test/auth-token.test.ts
```

Expected: PASS.

**Step 5:** Commit

```bash
git add web/src/lib/auth-token.ts web/src/test/auth-token.test.ts
git commit -m "feat(web): add auth token bridge module (#208)

Module-level get/set for JWT token, decoupling api-client from Supabase.
AuthProvider writes, apiFetch reads — synchronous, no async per-request.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 12: Inject auth token into apiFetch

**Files:**
- Modify: `web/src/lib/api-client.ts:27-48`
- Modify: `web/src/test/api-client.test.ts`

**Step 1:** Write tests for token injection in `api-client.test.ts`. Add at the end of the file:

```typescript
import { setAuthToken } from "../lib/auth-token";

describe("api auth token injection", () => {
  beforeEach(() => {
    setAuthToken(null);
  });

  it("includes Authorization header when token is set", async () => {
    setAuthToken("test-jwt-token");
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok" }),
    } as Response);

    await api.getPipelineStatus();

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer test-jwt-token");
  });

  it("omits Authorization header when no token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok" }),
    } as Response);

    await api.health();

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });
});
```

**Step 2:** Run test to verify failure

```bash
npm test -- src/test/api-client.test.ts
```

Expected: FAIL — `Authorization` header not present.

**Step 3:** Modify `apiFetch` in `api-client.ts`:

```typescript
import { getAuthToken } from "./auth-token";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...headers, ...(options?.headers as Record<string, string>) },
    });
  } catch (cause) {
    throw new Error(`Network error: ${path}`, { cause });
  }
  if (!res.ok) {
    // 401 = session expired — clear token to trigger re-auth
    if (res.status === 401) {
      const { setAuthToken: clearToken } = await import("./auth-token");
      clearToken(null);
    }
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = typeof body.detail === "string" ? sanitizeErrorDetail(body.detail) : undefined;
    } catch {
      /* non-JSON body — ignore */
    }
    throw new Error(detail ?? `API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}
```

**Step 4:** Run tests

```bash
npm test -- src/test/api-client.test.ts
```

Expected: All pass (existing + new).

**Step 5:** Commit

```bash
git add web/src/lib/api-client.ts web/src/test/api-client.test.ts
git commit -m "feat(web): inject auth token into apiFetch headers (#208)

Bearer token read from auth-token bridge module. 401 responses
clear the token to trigger re-authentication. No Supabase import
in api-client — stays decoupled via bridge.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 13: Create AuthProvider context

**Files:**
- Create: `web/src/lib/auth-context.tsx`
- Create: `web/src/test/auth-context.test.tsx`

**Step 1:** Write test `web/src/test/auth-context.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth-context";

// Mock Supabase
const mockGetSession = vi.fn();
const mockOnAuthStateChange = vi.fn();
const mockSignOut = vi.fn();

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      onAuthStateChange: (cb: unknown) => mockOnAuthStateChange(cb),
      signOut: () => mockSignOut(),
    },
  },
}));

vi.mock("@/lib/auth-token", () => ({
  setAuthToken: vi.fn(),
  getAuthToken: vi.fn(),
}));

function TestConsumer() {
  const { user, role, loading } = useAuth();
  if (loading) return <div>loading</div>;
  if (!user) return <div>no user</div>;
  return <div>user: {user.email} role: {role}</div>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
  });

  it("shows loading initially, then resolves session", async () => {
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: "jwt-123",
          user: { email: "test@co.com", app_metadata: { role: "admin" } },
        },
      },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    expect(screen.getByText("loading")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("user: test@co.com role: admin")).toBeInTheDocument();
    });
  });

  it("shows no user when session is null", async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("no user")).toBeInTheDocument();
    });
  });

  it("defaults role to viewer when app_metadata.role is missing", async () => {
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: "jwt-456",
          user: { email: "viewer@co.com", app_metadata: {} },
        },
      },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("user: viewer@co.com role: viewer")).toBeInTheDocument();
    });
  });
});
```

**Step 2:** Run test to verify failure

```bash
npm test -- src/test/auth-context.test.tsx
```

Expected: FAIL — module doesn't exist.

**Step 3:** Create `web/src/lib/auth-context.tsx`:

```typescript
"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { supabase } from "./supabase";
import { setAuthToken } from "./auth-token";
import type { Session, User } from "@supabase/supabase-js";

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  role: string;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  session: null,
  user: null,
  role: "viewer",
  loading: true,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const prevTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }

    supabase.auth.getSession().then(({ data }) => {
      const s = data.session;
      setSession(s);
      setAuthToken(s?.access_token ?? null);
      prevTokenRef.current = s?.access_token ?? null;
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      const newToken = newSession?.access_token ?? null;
      // Only update state if token actually changed (prevents event storm re-renders)
      if (newToken !== prevTokenRef.current) {
        prevTokenRef.current = newToken;
        setSession(newSession);
        setAuthToken(newToken);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const user = session?.user ?? null;
  const role =
    (typeof user?.app_metadata?.role === "string"
      ? user.app_metadata.role
      : null) ?? "viewer";

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setSession(null);
    setAuthToken(null);
  }

  return (
    <AuthContext.Provider value={{ session, user, role, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
```

**Step 4:** Run test

```bash
npm test -- src/test/auth-context.test.tsx
```

Expected: PASS.

**Step 5:** Commit

```bash
git add web/src/lib/auth-context.tsx web/src/test/auth-context.test.tsx
git commit -m "feat(web): add AuthProvider context with session management (#208)

Wraps app with Supabase session state. Exposes useAuth() hook
for role/user/session. Token bridge updated via onAuthStateChange.
Compares access tokens to prevent event storm re-renders.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 14: Wrap root layout with AuthProvider

**Files:**
- Modify: `web/src/app/layout.tsx`

**Step 1:** The root layout is a Server Component (no `"use client"`). Create a client wrapper:

Create `web/src/app/providers.tsx`:

```typescript
"use client";

import { AuthProvider } from "@/lib/auth-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
```

**Step 2:** Modify `web/src/app/layout.tsx`:

```typescript
import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "CompGraph",
  description: "Competitive intelligence for field marketing agencies",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          {children}
        </Providers>
        <Toaster />
      </body>
    </html>
  );
}
```

**Step 3:** Run tests

```bash
npm test
```

Expected: All pass. Existing tests mock `api-client` so they don't trigger real Supabase calls.

**Step 4:** Commit

```bash
git add web/src/app/layout.tsx web/src/app/providers.tsx
git commit -m "feat(web): wrap root layout with AuthProvider (#208)

Client Providers component wraps children with AuthProvider.
Root layout remains a Server Component for metadata export.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 15: Add auth guard to (app) layout

**Files:**
- Modify: `web/src/app/(app)/layout.tsx`
- Create: `web/src/test/app-layout-auth.test.tsx`

**Step 1:** Write test:

```typescript
// web/src/test/app-layout-auth.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mockUseAuth = vi.fn();
const mockRedirect = vi.fn();

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    mockRedirect(path);
    throw new Error("REDIRECT"); // simulate Next.js redirect behavior
  },
}));

vi.mock("@/components/layout", () => ({
  Shell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="shell">{children}</div>
  ),
}));

// Import AFTER mocks
import AppLayout from "@/app/(app)/layout";

describe("AppLayout auth guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeleton while auth is resolving", () => {
    mockUseAuth.mockReturnValue({ session: null, loading: true });
    render(<AppLayout>content</AppLayout>);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("redirects to /login when no session", () => {
    mockUseAuth.mockReturnValue({ session: null, loading: false });
    expect(() => render(<AppLayout>content</AppLayout>)).toThrow("REDIRECT");
    expect(mockRedirect).toHaveBeenCalledWith("/login");
  });

  it("renders Shell with children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      session: { access_token: "jwt" },
      loading: false,
    });
    render(<AppLayout>dashboard content</AppLayout>);
    expect(screen.getByTestId("shell")).toBeInTheDocument();
    expect(screen.getByText("dashboard content")).toBeInTheDocument();
  });
});
```

**Step 2:** Run to verify failure

```bash
npm test -- src/test/app-layout-auth.test.tsx
```

**Step 3:** Modify `web/src/app/(app)/layout.tsx`:

```typescript
"use client";

import { redirect } from "next/navigation";
import { Shell } from "@/components/layout";
import { useAuth } from "@/lib/auth-context";
import { Skeleton } from "@/components/ui/skeleton";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label="Loading application"
        style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}
      >
        <Skeleton style={{ width: 200, height: 24 }} />
      </div>
    );
  }

  if (!session) {
    redirect("/login");
  }

  return <Shell>{children}</Shell>;
}
```

**Step 4:** Run tests

```bash
npm test -- src/test/app-layout-auth.test.tsx
npm test
```

Expected: All pass.

**Step 5:** Commit

```bash
git add web/src/app/\\(app\\)/layout.tsx web/src/test/app-layout-auth.test.tsx
git commit -m "feat(web): add auth guard to app layout — block render until session (#208)

Unauthenticated users redirected to /login. Loading state shows
skeleton (blocks child mount to prevent race condition). Authenticated
users see Shell with children.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 16: Wire LoginForm to Supabase

**Files:**
- Modify: `web/src/components/auth/login-form.tsx`
- Create: `web/src/test/mocks/supabase.ts` (shared mock)
- Modify: `web/src/test/components/auth-components.test.tsx` (update mocks)

**Step 1:** Create shared Supabase mock `web/src/test/mocks/supabase.ts`:

```typescript
import { vi } from "vitest";

export const mockSignInWithPassword = vi.fn();
export const mockSignInWithOtp = vi.fn();
export const mockUpdateUser = vi.fn();
export const mockSignOut = vi.fn();
export const mockGetSession = vi.fn();
export const mockOnAuthStateChange = vi.fn(() => ({
  data: { subscription: { unsubscribe: vi.fn() } },
}));
export const mockResetPasswordForEmail = vi.fn();

export function mockSupabaseModule() {
  vi.mock("@/lib/supabase", () => ({
    supabase: {
      auth: {
        signInWithPassword: (...args: unknown[]) => mockSignInWithPassword(...args),
        signInWithOtp: (...args: unknown[]) => mockSignInWithOtp(...args),
        updateUser: (...args: unknown[]) => mockUpdateUser(...args),
        signOut: (...args: unknown[]) => mockSignOut(...args),
        getSession: (...args: unknown[]) => mockGetSession(...args),
        onAuthStateChange: (...args: unknown[]) => mockOnAuthStateChange(...args),
        resetPasswordForEmail: (...args: unknown[]) => mockResetPasswordForEmail(...args),
      },
    },
  }));
}

export function resetSupabaseMocks() {
  mockSignInWithPassword.mockReset();
  mockSignInWithOtp.mockReset();
  mockUpdateUser.mockReset();
  mockSignOut.mockReset();
  mockGetSession.mockReset();
  mockOnAuthStateChange.mockReset().mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
  mockResetPasswordForEmail.mockReset();
}
```

**Step 2:** Rewrite `login-form.tsx` — add state management, Supabase calls, error display, and router navigation. The full file replaces the stub `onSubmit`:

Key changes to `login-form.tsx`:
- Add imports: `supabase` from `@/lib/supabase`, `useRouter` from `next/navigation`
- Add state: `email`, `password`, `error`, `loading`
- Replace `onSubmit={(e) => e.preventDefault()}` with async handler that calls:
  - Password mode: `supabase.auth.signInWithPassword({ email, password })`
  - Magic link mode: `supabase.auth.signInWithOtp({ email })`
- Add error display above submit button
- On success: `router.push("/")`
- Wire "Forgot password?" to `supabase.auth.resetPasswordForEmail(email)`
- Disable button while loading

**Step 3:** Write tests for login form submission (add to auth-components.test.tsx or create separate file). Tests should verify:
- Password submit calls `signInWithPassword` with correct args
- Magic link submit calls `signInWithOtp` with correct args
- Error from Supabase is displayed
- Loading state disables button
- Successful login calls `router.push("/")`

**Step 4:** Run tests, lint, commit

```bash
npm test && npm run lint && npm run typecheck
git add web/src/components/auth/login-form.tsx web/src/test/mocks/supabase.ts web/src/test/components/auth-components.test.tsx
git commit -m "feat(web): wire LoginForm to Supabase Auth (#208)

Password and magic link modes connected. Error display, loading
state, forgot password flow. Shared Supabase mock for test reuse.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 17: Wire AccountSetupForm to Supabase

**Files:**
- Modify: `web/src/components/auth/account-setup-form.tsx:104-116`

**Step 1:** Replace the TODO stub (lines 110-112) with Supabase call:

```typescript
// Replace:
//   await new Promise((r) => setTimeout(r, 800));
// With:
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

// In handleSubmit:
const { error } = await supabase!.auth.updateUser({
  password,
  data: { first_name: firstName.trim(), last_name: lastName.trim() },
});
if (error) {
  setErrors({ submit: error.message });
  return;
}
router.push("/");
```

**Step 2:** Add `useRouter` hook and `router` declaration at component top.

**Step 3:** Add error display for `errors.submit` below the confirm password field.

**Step 4:** Write test — verify `updateUser` called with correct args, error displayed, success redirects.

**Step 5:** Run tests, lint, commit

```bash
npm test && npm run lint && npm run typecheck
git add web/src/components/auth/account-setup-form.tsx web/src/test/components/auth-components.test.tsx
git commit -m "feat(web): wire AccountSetupForm to Supabase updateUser (#208)

Replaces setTimeout stub with auth.updateUser() for password + name.
Error handling and redirect on success.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 18: Wire InviteUserForm to backend API

**Files:**
- Modify: `web/src/components/auth/invite-user-form.tsx:43-59`

**Step 1:** Replace the mock `handleConfirm` (lines 43-59) with real API call:

```typescript
// Replace setTimeout + mock user creation with:
import { api } from "@/lib/api-client";

async function handleConfirm() {
  const trimmed = email.trim().toLowerCase();
  const response = await api.inviteUser({ email: trimmed, role });
  // ... handle response, call onInvited with real user data
}
```

**Step 2:** Add `inviteUser` method to `api` object in `api-client.ts`:

```typescript
inviteUser: (body: { email: string; role: string }) =>
  apiFetch<{ user_id: string; email: string; role: string }>(
    "/api/v1/admin/invite",
    { method: "POST", body: JSON.stringify(body) },
  ),
```

**Step 3:** Write test — verify `apiFetch` called with correct path and body. Error handling for failed invites.

**Step 4:** Run tests, lint, commit

```bash
npm test && npm run lint && npm run typecheck
git add web/src/components/auth/invite-user-form.tsx web/src/lib/api-client.ts web/src/test/components/auth-components.test.tsx
git commit -m "feat(web): wire InviteUserForm to POST /api/v1/admin/invite (#208)

Replaces mock timeout with real API call via apiFetch. Adds
inviteUser method to api client. Error handling for failed invites.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 19: Final validation and PR

**Step 1:** Run full test suite

```bash
cd web && npm test && npm run lint && npm run typecheck && npm run build
```

Expected: All pass, build succeeds.

**Step 2:** Verify test coverage

```bash
npm run test:coverage
```

Expected: Above 50% threshold.

**Step 3:** Push and create draft PR

```bash
git push -u origin feat/issue-208-frontend-auth
gh pr create --draft --title "feat(web): frontend auth pages — Supabase integration (#208)" --body "$(cat <<'EOF'
## Summary
- Install `@supabase/supabase-js`, create client singleton with SSR guard
- `AuthProvider` context with `useAuth()` hook (session, role, signOut)
- Auth token bridge module — decouples api-client from Supabase
- Bearer token injection in `apiFetch` with 401 interception
- Auth guard in `(app)/layout.tsx` — blocks render until session resolves
- LoginForm wired to `signInWithPassword` / `signInWithOtp`
- AccountSetupForm wired to `updateUser` (password + name)
- InviteUserForm wired to `POST /api/v1/admin/invite`
- Shared Supabase test mock factory

Closes #208
Depends on: #199 (API versioning — rebase before merge)

## Test plan
- [ ] Auth context loads session and exposes role
- [ ] Token injected into API calls when authenticated
- [ ] Unauthenticated users redirected to /login
- [ ] Login form submits to Supabase (password + magic link modes)
- [ ] Setup form calls updateUser with name + password
- [ ] Invite form calls backend admin endpoint
- [ ] 401 response clears token
- [ ] `npm run build` succeeds
- [ ] All existing tests still pass

## Env vars needed
- `NEXT_PUBLIC_SUPABASE_URL` — set in Vercel dashboard
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — set in Vercel dashboard

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 4:** After #199 merges to main, rebase this branch:

```bash
git fetch origin main
git rebase origin/main
# Resolve api-client.ts conflicts (paths should already be /api/v1/)
npm test && npm run build
git push --force-with-lease
```

---

## Merge Order Checklist

1. [ ] #199 PR passes CI → merge to main
2. [ ] Rebase #208 on updated main
3. [ ] #208 PR passes CI → merge to main
4. [ ] Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in Vercel dashboard
5. [ ] Verify login flow works on https://compgraph.app/login
6. [ ] Clean up worktrees: `git worktree remove ../compgraph-199 && git worktree remove ../compgraph-208`
