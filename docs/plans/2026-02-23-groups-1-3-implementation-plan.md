# Groups 1–3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 13 GitHub issues across three groups: Quick Wins + Eval Unblocking (6), Job Feed Polish (5), and Settings UX (2).

**Architecture:** Group 1 unblocks eval runs and improves error visibility. Group 2 polishes the Hiring page (filters, pay, columns, pagination). Group 3 restores status on navigation and adds confirmation dialogs for destructive/LLM actions.

**Tech Stack:** FastAPI, Next.js 16, Vitest, pytest, @tremor/react (added for Group 2/3)

---

## Group 1: Quick Wins + Eval Unblocking

### Task 1: #179 — apiFetch extracts FastAPI error detail

**Files:**
- Modify: `web/src/lib/api-client.ts:31-34`
- Test: `web/src/test/api-client.test.ts`

**Step 1: Write the failing test**

Add to `web/src/test/api-client.test.ts` in the `describe('api error handling')` block:

```typescript
it('throws with FastAPI detail when response has detail field', async () => {
  vi.mocked(fetch).mockResolvedValueOnce({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'No corpus file found' }),
  } as Response)

  await expect(api.createEvalRun({
    pass_number: 1,
    model: 'claude-haiku-4-5-20251001',
    prompt_version: 'pass1_v1',
  })).rejects.toThrow('No corpus file found')
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm test -- api-client.test.ts -t "throws with FastAPI detail"`
Expected: FAIL (current apiFetch throws "API error 400: /api/eval/runs")

**Step 3: Implement apiFetch detail extraction**

In `web/src/lib/api-client.ts`, replace lines 31-34:

```typescript
  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = (await res.json()) as { detail?: string }
      detail = typeof body.detail === 'string' ? body.detail : undefined
    } catch {
      /* non-JSON body — ignore */
    }
    throw new Error(detail ?? `API error ${res.status}: ${path}`)
  }
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm test -- api-client.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/lib/api-client.ts web/src/test/api-client.test.ts
git commit -m "fix(web): extract FastAPI detail in apiFetch for actionable error messages (#179)"
```

---

### Task 2: #178 — Eval corpus.json generation script

**Files:**
- Create: `scripts/generate_eval_corpus.py`
- Modify: `.gitignore`
- Modify: `CLAUDE.md` (Eval section)

**Step 1: Add corpus.json to .gitignore**

Append to `.gitignore` (after `eval/data/eval.db`):

```
eval/data/corpus.json
```

**Step 2: Create generate_eval_corpus.py**

Create `scripts/generate_eval_corpus.py`:

```python
#!/usr/bin/env python3
"""Generate eval/data/corpus.json from live postings for eval runs.

Usage:
  op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py
  op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py --limit 100 --company-slug bds

Output: eval/data/corpus.json (git-ignored)
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from compgraph.config import Settings
from compgraph.db.models import Company, Posting, PostingSnapshot


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval corpus from postings")
    parser.add_argument("--limit", type=int, default=200, help="Max corpus size")
    parser.add_argument("--company-slug", type=str, help="Filter by company slug")
    args = parser.parse_args()

    settings = Settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    corpus_path = Path(__file__).parent.parent / "eval" / "data" / "corpus.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    latest_snapshot_date = (
        select(func.max(PostingSnapshot.snapshot_date))
        .where(PostingSnapshot.posting_id == Posting.id)
        .correlate(Posting)
        .scalar_subquery()
    )

    async with async_session() as session:
        q = (
            select(Posting, PostingSnapshot, Company.slug)
            .join(
                PostingSnapshot,
                (PostingSnapshot.posting_id == Posting.id)
                & (PostingSnapshot.snapshot_date == latest_snapshot_date),
            )
            .join(Company, Company.id == Posting.company_id)
            .where(Posting.is_active)
        )
        if args.company_slug:
            q = q.where(Company.slug == args.company_slug)
        q = q.order_by(Posting.first_seen_at.desc()).limit(args.limit)
        result = await session.execute(q)
        rows = result.all()

    corpus = []
    for posting, snapshot, slug in rows:
        corpus.append({
            "id": f"posting_{posting.id}",
            "company_slug": slug,
            "title": snapshot.title_raw or "",
            "location": snapshot.location_raw or "",
            "full_text": (snapshot.full_text_raw or "")[:10000],
            "reference_pass1": None,
            "reference_pass2": None,
        })

    corpus_path.write_text(json.dumps(corpus, indent=2))
    print(f"Wrote {len(corpus)} items to {corpus_path}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run script (dry run)**

Run: `op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py --limit 5`
Expected: Creates eval/data/corpus.json with 5 items

**Step 5: Add CLAUDE.md entry**

In `CLAUDE.md` under Enrichment or Eval section, add:

```markdown
- Run `op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py` to populate `eval/data/corpus.json` before launching eval runs.
```

**Step 6: Commit**

```bash
git add scripts/generate_eval_corpus.py .gitignore CLAUDE.md
git commit -m "feat: add generate_eval_corpus script to populate corpus.json (#178)"
```

---

### Task 3: #177 — Eval model dropdown + backend validator

**Files:**
- Modify: `web/src/app/eval/runs/page.tsx:134-136, 218-246`
- Modify: `src/compgraph/eval/router.py:394-398`
- Test: `tests/test_eval_router.py`

**Step 1: Add backend SUPPORTED_MODELS and validator**

In `src/compgraph/eval/router.py`, before `class RunCreate`:

```python
SUPPORTED_MODELS = {
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
}
```

Add to `RunCreate`:

```python
from pydantic import field_validator

class RunCreate(BaseModel):
    pass_number: int
    model: str
    prompt_version: str
    concurrency: int = Field(default=5, ge=1, le=50)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if v not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {v}. Must be one of: {sorted(SUPPORTED_MODELS)}")
        return v
```

**Step 2: Write failing test for 422 on unknown model**

In `tests/test_eval_router.py`:

```python
async def test_create_run_rejects_unknown_model(client, ...):
    # Mock corpus exists
    response = await client.post(
        "/api/eval/runs",
        json={"pass_number": 1, "model": "gpt-4", "prompt_version": "pass1_v1", "concurrency": 5},
    )
    assert response.status_code == 422
    assert "Unsupported model" in response.json()["detail"][0]["msg"]
```

**Step 3: Run backend test**

Run: `uv run pytest tests/test_eval_router.py -v -k "create_run"`

**Step 4: Replace model input with select in eval runs page**

In `web/src/app/eval/runs/page.tsx`:

- Change default: `useState("claude-haiku-4-5-20251001")`
- Replace `<input type="text" ...>` with:

```tsx
const MODEL_OPTIONS = [
  { label: "Claude Haiku 4.5", value: "claude-haiku-4-5-20251001" },
  { label: "Claude Sonnet 4.6", value: "claude-sonnet-4-6" },
  { label: "Claude Opus 4.6", value: "claude-opus-4-6" },
] as const

<select
  value={model}
  onChange={(e) => setModel(e.target.value)}
  disabled={submitting}
  className="w-full rounded border px-2 py-1.5 disabled:opacity-50"
  style={{ borderColor: "#BFC0C0", ... }}
>
  {MODEL_OPTIONS.map((o) => (
    <option key={o.value} value={o.value}>{o.label}</option>
  ))}
</select>
```

**Step 5: Run frontend tests**

Run: `cd web && npm test`
Expected: PASS

**Step 6: Commit**

```bash
git add src/compgraph/eval/router.py tests/test_eval_router.py web/src/app/eval/runs/page.tsx
git commit -m "fix: eval model dropdown with valid IDs + backend validator (#177)"
```

---

### Task 4: #180 — formatRoleArchetype utility

**Files:**
- Create or modify: `web/src/lib/utils.ts`
- Modify: `web/src/app/hiring/page.tsx:272`
- Modify: `web/src/app/competitors/[slug]/page.tsx:734, 946`

**Step 1: Add formatRoleArchetype to utils**

Create `web/src/lib/utils.ts` if absent, or add:

```typescript
export function formatRoleArchetype(role: string): string {
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}
```

**Step 2: Apply at hiring page badge**

In `web/src/app/hiring/page.tsx`, line ~272:

```tsx
{formatRoleArchetype(item.role_archetype)}
```

Keep filter option values and comparisons as raw `item.role_archetype`.

**Step 3: Apply at competitors page (2 sites)**

In `web/src/app/competitors/[slug]/page.tsx` at lines 734 and 946:

```tsx
{formatRoleArchetype(posting.role_archetype)}
```

**Step 4: Run tests**

Run: `cd web && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/lib/utils.ts web/src/app/hiring/page.tsx web/src/app/competitors/[slug]/page.tsx
git commit -m "fix: format role archetype badges as Title Case (#180)"
```

---

### Task 5: #187 — Consolidate pyproject.toml dev groups

**Files:**
- Modify: `pyproject.toml`

**Step 1: Merge dependency-groups.dev into optional-dependencies dev**

The `[dependency-groups].dev` (lines 91-95) has only `pytest-cov>=7.0.0`. The `[project.optional-dependencies].dev` (lines 26-34) has 7 packages. Per Cubic feedback: consolidate.

Option A: Remove `[dependency-groups]` and bump pytest-cov in optional-dependencies:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=7.0.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "sqlalchemy[mypy]>=2.0.0",
    "types-requests>=2.31.0",
]
```

Then remove the entire `[dependency-groups]` section.

**Step 2: Verify uv sync**

Run: `uv sync --group dev` (if using groups) or `uv sync --all-extras`
Expected: No errors

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "fix: consolidate dev dependency groups in pyproject.toml (#187)"
```

---

### Task 6: #168 — EnrichStatus union type

**Files:**
- Modify: `web/src/lib/types.ts:207-219`
- Modify: `web/src/app/settings/page.tsx` (remove .toUpperCase() workaround if present)

**Step 1: Define EnrichStatus union**

In `web/src/lib/types.ts`:

```typescript
export type EnrichStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'stopping'
  | 'success'
  | 'partial'
  | 'failed'
  | 'cancelled'

export interface EnrichStatusResponse {
  run_id: string
  status: EnrichStatus
  // ... rest unchanged
}
```

**Step 2: Update settings page**

Search for `.toUpperCase()` on enrich status and remove if it was a workaround. Ensure `TERMINAL_STATES` includes lowercase values (it already uses `"success"`, `"partial"`, etc.).

**Step 3: Run typecheck**

Run: `cd web && npm run typecheck`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/lib/types.ts web/src/app/settings/page.tsx
git commit -m "fix: add EnrichStatus union type (#168)"
```

---

## Group 2: Job Feed Polish

### Task 7: #173 — Company filter from api.getCompanies()

**Files:**
- Modify: `web/src/app/hiring/page.tsx:78-96, 51-76`

**Step 1: Add companies state and fetch on mount**

```typescript
const [companies, setCompanies] = useState<Array<{ id: string; name: string; slug: string }>>([])

useEffect(() => {
  let cancelled = false
  api.getCompanies().then((data) => {
    if (!cancelled) setCompanies(data)
  }).catch(() => {})
  return () => { cancelled = true }
}, [])
```

**Step 2: Replace uniqueCompanies useMemo with companies**

Use `companies` for the company dropdown options. Map `id` to value, `name` to label. Remove `uniqueCompanies` useMemo.

**Step 3: Pass company_id to listPostings when companyFilter set**

In the `load` effect, pass `company_id: companyFilter || undefined` to `api.listPostings`. Add `companyFilter` to the effect deps. Reset `offset` to 0 when filters change.

**Step 4: Run tests**

Run: `cd web && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/app/hiring/page.tsx
git commit -m "fix: company filter shows all companies from API (#173)"
```

---

### Task 8: #174 — Pay range format + pay_currency

**Files:**
- Modify: `src/compgraph/api/routes/postings.py` (PostingListItem, SELECT, row mapping)
- Modify: `web/src/lib/types.ts` (PostingListItem)
- Modify: `web/src/app/hiring/page.tsx` (formatPayRange, display)

**Step 1: Backend — add pay_currency**

In `src/compgraph/api/routes/postings.py`:
- Add `pay_currency: str | None` to `PostingListItem`
- Add `PostingEnrichment.pay_currency` to SELECT
- Map in row constructor: `pay_currency=row[9]` (adjust index after adding)

**Step 2: Frontend types**

In `web/src/lib/types.ts`, add `pay_currency: string | null` to `PostingListItem`.

**Step 3: Fix formatPayRange**

In `web/src/app/hiring/page.tsx`:

```typescript
function formatPayRange(
  min: number | null,
  max: number | null,
  currency?: string | null
): string {
  if (min === null && max === null) return "—"
  const opts: Intl.NumberFormatOptions = {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }
  const fmt = (n: number) => n.toLocaleString("en-US", opts)
  let s: string
  if (min !== null && max !== null) s = `$${fmt(min)}–$${fmt(max)}`
  else if (min !== null) s = `$${fmt(min)}+`
  else s = `up to $${fmt(max!)}`
  if (currency && currency !== "USD") s += ` ${currency}`
  return s
}
```

Call with `formatPayRange(item.pay_min, item.pay_max, item.pay_currency)`.

**Step 4: Run tests**

Run: `uv run pytest tests/` and `cd web && npm test`

**Step 5: Commit**

```bash
git add src/compgraph/api/routes/postings.py web/src/lib/types.ts web/src/app/hiring/page.tsx
git commit -m "fix: pay range 2 decimals + currency indicator (#174)"
```

---

### Task 9: #182 — Merge Status and First Seen columns

**Files:**
- Modify: `web/src/app/hiring/page.tsx:214-227, 288-300, 236`

**Step 1: Update column headers**

Change from 7 columns to 6: remove "First Seen", keep "Status". Update header array to `["Title", "Company", "Location", "Role", "Pay Range", "Status"]`.

**Step 2: Merge the two cells**

Replace Status `<td>` and First Seen `<td>` with single cell:

```tsx
<td className="px-4 py-3">
  <div className="flex flex-col gap-1">
    <Badge variant={item.is_active ? "success" : "error"}>
      {item.is_active ? "Active" : "Inactive"}
    </Badge>
    <span style={{ fontSize: "12px", color: "#4F5D75" }}>
      {item.is_active
        ? `Start: ${formatDate(item.first_seen_at)}`
        : `Closed: ${formatDate(item.last_seen_at ?? item.first_seen_at)}`}
    </span>
  </div>
</td>
```

**Step 3: Update colSpan**

Change empty-state row `colSpan={7}` to `colSpan={6}`. Update SkeletonRow length to 6.

**Step 4: Commit**

```bash
git add web/src/app/hiring/page.tsx
git commit -m "feat: merge Status and First Seen into single column (#182)"
```

---

### Task 10: #175 — TablePagination component (first/prev/next/last)

**Files:**
- Create: `web/src/components/data/table-pagination.tsx`
- Modify: `web/src/app/hiring/page.tsx:306-349`

**Step 1: Install Tremor**

Run: `cd web && npm install @tremor/react`

**Step 2: Create TablePagination component**

Create `web/src/components/data/table-pagination.tsx`:

```tsx
"use client"

interface TablePaginationProps {
  page: number
  totalPages: number
  onFirst: () => void
  onPrev: () => void
  onNext: () => void
  onLast: () => void
}

export function TablePagination({
  page,
  totalPages,
  onFirst,
  onPrev,
  onNext,
  onLast,
}: TablePaginationProps) {
  return (
    <div className="flex items-center justify-between">
      <span style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "#4F5D75" }}>
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-1">
        <button type="button" onClick={onFirst} disabled={page <= 1} aria-label="First page">⏮</button>
        <button type="button" onClick={onPrev} disabled={page <= 1} aria-label="Previous">◀</button>
        <button type="button" onClick={onNext} disabled={page >= totalPages} aria-label="Next">▶</button>
        <button type="button" onClick={onLast} disabled={page >= totalPages} aria-label="Last page">⏭</button>
      </div>
    </div>
  )
}
```

Use CompGraph design tokens for disabled/active states. Reference: Tremor pagination-4 pattern. Icons can be from @heroicons/react if preferred.

**Step 3: Replace hiring page pagination**

Derive `page = Math.floor(offset / PAGE_SIZE) + 1`, `totalPages = Math.ceil(total / PAGE_SIZE)`. Replace Prev/Next with `<TablePagination ... />`.

**Step 4: Add unit test for TablePagination**

Create or extend `web/src/test/components/table-pagination.test.tsx`.

**Step 5: Commit**

```bash
git add web/src/components/data/table-pagination.tsx web/src/app/hiring/page.tsx web/package.json
git commit -m "feat: TablePagination with first/prev/next/last (#175)"
```

---

### Task 11: #176 — Filter bar upgrade (styled dropdowns, chips, sort, search)

**Scope:** This is a larger feature. Implement in order:
1. Backend: add `sort_by` and `search` params to `list_postings`
2. Frontend: add sortBy state, debounced search param, active chips row, Clear All

**Files:**
- Modify: `src/compgraph/api/routes/postings.py`
- Modify: `web/src/lib/api-client.ts` (listPostings params)
- Modify: `web/src/app/hiring/page.tsx`

**Step 1: Backend sort_by and search**

In `list_postings`, add:
- `sort_by: str = "first_seen_desc"`
- `search: str | None = None`

Apply `PostingSnapshot.title_raw.ilike(f"%{search}%")` when search is set. Apply ordering:
- `first_seen_desc` → `Posting.first_seen_at.desc()`
- `first_seen_asc` → `Posting.first_seen_at.asc()`
- `pay_desc` → `PostingEnrichment.pay_max.desc().nulls_last()`
- `pay_asc` → `PostingEnrichment.pay_max.asc().nulls_last()`
- `title_asc` → `PostingSnapshot.title_raw.asc().nulls_last()`

Reject unknown `sort_by` with 422.

**Step 2: Frontend api-client**

Add `sort_by` and `search` to `listPostings` params.

**Step 3: Frontend hiring page**

- Add `sortBy` state (default `"first_seen_desc"`)
- Move search from client-side filter to API param (debounce 300ms)
- Add active chips row when filters/sort are non-default
- Add Clear All button
- Use Tremor Select for dropdowns with CompGraph overrides

**Step 4: Commit**

```bash
git add src/compgraph/api/routes/postings.py web/src/lib/api-client.ts web/src/app/hiring/page.tsx
git commit -m "feat: filter bar upgrade with sort, search, chips (#176)"
```

---

## Group 3: Settings UX

### Task 12: #172 — Restore scrape/enrich status on mount

**Files:**
- Modify: `web/src/app/settings/page.tsx`

**Step 1: Add mount effect for scrape status**

Before the poll effects, add a `useEffect` that runs once on mount:

```typescript
useEffect(() => {
  let cancelled = false
  async function init() {
    try {
      const s = await api.getScrapeStatus()
      if (!cancelled && !TERMINAL_STATES.has(s.status) && s.run_id) {
        setScrapeActiveRunId(s.run_id)
      }
    } catch { /* ignore */ }
    try {
      const e = await api.getEnrichStatus()
      if (!cancelled && !TERMINAL_STATES.has(e.status) && e.run_id) {
        setEnrichActiveRunId(e.run_id)
      }
    } catch { /* ignore */ }
  }
  void init()
  return () => { cancelled = true }
}, [])
```

**Step 2: Run tests**

Run: `cd web && npm test`

**Step 3: Commit**

```bash
git add web/src/app/settings/page.tsx
git commit -m "fix: restore scrape/enrich status polling on mount (#172)"
```

---

### Task 13: #184 — ConfirmDialog for destructive/LLM actions

**Files:**
- Create: `web/src/components/ui/confirm-dialog.tsx`
- Modify: `web/src/app/settings/page.tsx` (6 callsites)
- Modify: `web/src/app/eval/runs/page.tsx` (replace confirmStep)

**Step 1: Install Tremor (if not done)**

Run: `cd web && npm install @tremor/react`

**Step 2: Create ConfirmDialog component**

Create `web/src/components/ui/confirm-dialog.tsx` using Tremor Dialog. Props: `open`, `onOpenChange`, `title`, `description`, `confirmLabel`, `cancelLabel`, `confirmVariant`, `onConfirm`. Style with CompGraph tokens (coral #EF8354, danger #8C2C23).

**Step 3: Add dialog state to Settings**

For each action (Trigger Scrape, Trigger Enrichment, Trigger Aggregation, Stop, Force-Stop, Trigger Scheduler Job), add `confirmOpen` state. On button click, open dialog. On confirm, call handler and close.

**Step 4: Replace eval runs confirmStep**

Remove `confirmStep` and inline confirm UI. Use `ConfirmDialog` when user clicks "Start Run". On confirm, call `executeRun()`.

**Step 5: Add unit test for ConfirmDialog**

**Step 6: Commit**

```bash
git add web/src/components/ui/confirm-dialog.tsx web/src/app/settings/page.tsx web/src/app/eval/runs/page.tsx
git commit -m "feat: ConfirmDialog for destructive and LLM-triggering actions (#184)"
```

---

## Execution Order Summary

| Order | Task | Issue |
|-------|------|-------|
| 1 | apiFetch detail | #179 |
| 2 | generate_eval_corpus.py | #178 |
| 3 | Eval model dropdown + validator | #177 |
| 4 | formatRoleArchetype | #180 |
| 5 | pyproject dev groups | #187 |
| 6 | EnrichStatus union | #168 |
| 7 | Company filter from API | #173 |
| 8 | Pay range + currency | #174 |
| 9 | Merge Status/First Seen | #182 |
| 10 | TablePagination | #175 |
| 11 | Filter bar upgrade | #176 |
| 12 | Status restore on mount | #172 |
| 13 | ConfirmDialog | #184 |

---

## Verification Checklist

- [ ] `uv run pytest -m "not integration"` passes
- [ ] `cd web && npm run lint && npm run typecheck && npm test && npm run build` passes
- [ ] Eval runs page: create run with corpus.json present shows model dropdown
- [ ] Hiring page: company filter shows all 5 companies, pay shows 2 decimals, Status column merged
- [ ] Settings: navigate away and back during scrape shows live panel; destructive actions show confirm dialog

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-02-23-groups-1-3-implementation-plan.md`.

**Two execution options:**

1. **Subagent-Driven (this session)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

2. **Parallel Session (separate)** — Open a new session with `@executing-plans` skill, batch execution with checkpoints.

**Which approach?**
