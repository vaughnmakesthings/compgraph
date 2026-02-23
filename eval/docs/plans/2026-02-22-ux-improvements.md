# UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all improvements identified in the 2026-02-22 three-agent UX/design audit, producing a higher-quality reference implementation for the main CompGraph project.

**Architecture:** Changes are grouped foundation-first so each layer builds on the last. Shared utilities and components are created before pages that use them. URL query params replace in-memory-only state. No new pages are added — existing pages are improved.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind CSS v4 (`@theme` in `globals.css`), `next/navigation` (`useSearchParams`, `useRouter`), Vitest 4 + Testing Library

**Notes for main project:** Every pattern here is intentional. Key learnings are marked 🔑. This branch is a living reference — consult it when building the main UI.

---

## Batch 1 — Foundation: Tokens, Shared Components, DataTable

*No UI dependencies. Everything else builds on this.*

---

### Task 1: Add medal and threshold color tokens to globals.css

**Files:**
- Modify: `web/src/app/globals.css`

**Context:** `leaderboard/page.tsx` uses hardcoded `#D4A017` (gold) and `#B87333` (bronze). `prompt-diff/page.tsx` uses raw Tailwind `green-600`/`amber-600`/`red-600` for match% thresholds. Both violate the token system. The fix: add semantic tokens for these purposes, then reference them in components.

**Step 1: Add tokens to `:root` in globals.css**

Find the `:root` block. After the `--status-*` variables (around line 113), add:

```css
  /* Medal rankings */
  --medal-gold: #D4A017;
  --medal-silver: #A0A0A0;
  --medal-bronze: #B87333;

  /* Match quality thresholds (prompt-diff, leaderboard) */
  --threshold-high: var(--success);
  --threshold-mid: var(--warning);
  --threshold-low: var(--error);
```

**Step 2: Add Tailwind mappings in `@theme inline` block** (around line 51 in globals.css)

```css
  --color-medal-gold: var(--medal-gold);
  --color-medal-silver: var(--medal-silver);
  --color-medal-bronze: var(--medal-bronze);
  --color-threshold-high: var(--threshold-high);
  --color-threshold-mid: var(--threshold-mid);
  --color-threshold-low: var(--threshold-low);
```

**Step 3: Add dark mode overrides** in the `.dark` block (find it, add after existing entries):

```css
  --medal-gold: #E8C76A;
  --medal-silver: #C8C8C8;
  --medal-bronze: #D4956A;
  --threshold-high: var(--success);
  --threshold-mid: var(--warning);
  --threshold-low: var(--error);
```

**Step 4: Run typecheck + tests**

```bash
cd web && npm run typecheck && npm test
```

Expected: 0 errors, 107 tests passing

**Step 5: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat: add medal and threshold color tokens to design system"
```

---

### Task 2: Fix all hardcoded color violations

**Files:**
- Modify: `web/src/app/leaderboard/page.tsx` (lines 65–71)
- Modify: `web/src/app/prompt-diff/page.tsx` (lines 102–111)
- Modify: `web/src/app/review/page.tsx` (lines 86–92, 399–404, 530–532)
- Modify: `web/src/app/runs/page.tsx` (lines 346, 369, 385, 411–413)

**Step 1: Fix leaderboard/page.tsx RankCell**

Replace the entire `RankCell` function:

```tsx
function RankCell({ rank }: { rank: number }) {
  if (rank === 1) {
    return <span className="font-semibold text-medal-gold">#{rank}</span>;
  }
  if (rank === 2) {
    return <span className="text-medal-silver">#{rank}</span>;
  }
  if (rank === 3) {
    return <span className="text-medal-bronze">#{rank}</span>;
  }
  return <span className="text-muted-foreground">#{rank}</span>;
}
```

🔑 **Pattern:** Token names describe *purpose* (`medal-gold`), not value (`#D4A017`). Dark mode just works.

**Step 2: Fix prompt-diff/page.tsx match% colors**

Replace the `className` ternary in the `matchPct` column render (lines 102–111):

```tsx
className={cn(
  "font-semibold",
  pct >= 90
    ? "text-threshold-high"
    : pct >= 70
      ? "text-threshold-mid"
      : "text-threshold-low",
)}
```

**Step 3: Fix review/page.tsx field disagreement color** (line 86–92)

Change `text-amber-500` → `text-warning` in both places in `FieldComparisonPanel`:

```tsx
className={`text-[12px] ${disagree ? "text-warning font-medium" : "text-muted-foreground"}`}
// and:
className={`font-mono text-[13px] tabular-nums text-right max-w-[60%] break-words ${disagree ? "text-warning" : "text-foreground"}`}
```

**Step 4: Fix review/page.tsx pass-mismatch warning box** (lines 399–404)

```tsx
<div className="mt-4 rounded-lg border border-warning/50 bg-warning-muted p-4 text-[13px] text-warning-foreground">
```

**Step 5: Fix review/page.tsx vote error** (line 530–532)

```tsx
<p className="mt-3 text-[12px] text-status-wrong">
```

**Step 6: Fix runs/page.tsx form error** (line 346)

```tsx
<p className="mt-3 text-[12px] text-status-wrong">
```

**Step 7: Fix runs/page.tsx progress bar** (line 369) — replace `transition-all` with `transition-[width]`

```tsx
className="h-full rounded-full bg-primary transition-[width] duration-300"
```

**Step 8: Fix runs/page.tsx failed progress error** (line 385)

```tsx
<p className="text-[12px] text-status-wrong">
```

**Step 9: Fix runs/page.tsx fetch error box** (lines 411–413)

```tsx
<div className="rounded-lg border border-error/30 bg-error-muted p-4 text-[13px] text-status-wrong">
```

**Step 10: Run lint + typecheck + tests**

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Expected: 0 lint warnings, 0 type errors, 107 tests passing

**Step 11: Commit**

```bash
git add web/src/app/leaderboard/page.tsx web/src/app/prompt-diff/page.tsx web/src/app/review/page.tsx web/src/app/runs/page.tsx
git commit -m "fix: replace all hardcoded colors with design tokens"
```

---

### Task 3: Create ErrorBox and LoadingCard shared components

**Files:**
- Create: `web/src/components/error-box.tsx`
- Create: `web/src/components/loading-card.tsx`
- Modify: `web/src/app/leaderboard/page.tsx` (line 429–433)
- Modify: `web/src/app/runs/page.tsx` (lines 411–413, 417–421)

**Context:** Every page reimplements error/loading UI. Extract these into components once, use everywhere. 🔑 **Pattern for main project:** always extract repeated layout patterns into components before a second page needs them.

**Step 1: Create web/src/components/error-box.tsx**

```tsx
interface ErrorBoxProps {
  message: string;
}

export function ErrorBox({ message }: ErrorBoxProps) {
  return (
    <div className="rounded-lg border border-error/30 bg-error-muted px-4 py-3 text-[13px] text-status-wrong">
      {message}
    </div>
  );
}
```

**Step 2: Create web/src/components/loading-card.tsx**

```tsx
interface LoadingCardProps {
  message?: string;
}

export function LoadingCard({ message = "Loading\u2026" }: LoadingCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-10 text-center shadow-sm">
      <p className="animate-pulse text-[13px] text-muted-foreground">{message}</p>
    </div>
  );
}
```

**Step 3: Replace inline error box in leaderboard/page.tsx** (lines 429–433)

```tsx
import { ErrorBox } from "@/components/error-box";
import { LoadingCard } from "@/components/loading-card";
// ...
{error && <ErrorBox message={error} />}
// ...
{loading ? (
  <LoadingCard message="Loading leaderboard data\u2026" />
) : ( ...
```

**Step 4: Replace inline error/loading in runs/page.tsx** (lines 411–421)

```tsx
import { ErrorBox } from "@/components/error-box";
import { LoadingCard } from "@/components/loading-card";
// ...
{error && <ErrorBox message={error} />}
// ...
{loading ? (
  <LoadingCard />
) : ( ...
```

**Step 5: Run lint + typecheck + tests**

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Expected: 107 tests, 0 errors

**Step 6: Commit**

```bash
git add web/src/components/error-box.tsx web/src/components/loading-card.tsx web/src/app/leaderboard/page.tsx web/src/app/runs/page.tsx
git commit -m "feat: add ErrorBox and LoadingCard shared components"
```

---

### Task 4: Add overflow-x-auto wrapper to DataTable

**Files:**
- Modify: `web/src/components/data-table.tsx`

**Context:** The leaderboard field-accuracy table has 14+ columns. Without an overflow wrapper, it breaks layouts below ~1280px wide. The fix is a single wrapper `div`.

🔑 **Pattern:** Always wrap data tables in `overflow-x-auto` — you'll never regret it and will always regret not doing it.

**Step 1: Wrap the `<table>` in data-table.tsx**

```tsx
export function DataTable<T extends object>({
  columns, data, ariaLabel, rowKey,
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full" aria-label={ariaLabel}>
        {/* ... rest unchanged ... */}
      </table>
    </div>
  );
}
```

**Step 2: Run tests**

```bash
cd web && npm test
```

Expected: 107 passing

**Step 3: Commit**

```bash
git add web/src/components/data-table.tsx
git commit -m "fix: wrap DataTable in overflow-x-auto for wide tables"
```

---

### Task 5: Create canonical run label utility

**Files:**
- Create: `web/src/lib/run-utils.ts`
- Modify: `web/src/app/runs/page.tsx` (option labels)
- Modify: `web/src/app/review/page.tsx` (option labels)
- Modify: `web/src/app/prompt-diff/page.tsx` (replace `formatRunLabel`)
- Modify: `web/src/app/accuracy/page.tsx` (option labels)

**Context:** Each page formats run labels differently. Canonical format: `Model / Prompt · Pass N · #ID`.

🔑 **Pattern for main project:** Put all entity-formatting functions in `lib/` immediately. Never let the same entity format itself differently on two pages.

**Step 1: Create web/src/lib/run-utils.ts**

```ts
import type { Run } from "@/lib/api-client";

/**
 * Canonical run label: "haiku-3.5 / pass1_v1 · Pass 1 · #42"
 * Used consistently across all run selectors and tables.
 */
export function formatRunLabel(run: Run): string {
  return `${run.model} / ${run.prompt_version} \u00B7 Pass ${run.pass_number} \u00B7 #${run.id}`;
}
```

**Step 2: Update run option labels in runs/page.tsx** — no select needed here, runs table already shows model/prompt/pass separately. Skip.

**Step 3: Update run option labels in accuracy/page.tsx** (option text in run select, line ~525–529)

```tsx
import { formatRunLabel } from "@/lib/run-utils";
// ...
{runs.map((run) => (
  <option key={run.id} value={run.id}>
    {formatRunLabel(run)}
  </option>
))}
```

**Step 4: Update review/page.tsx** (both run selectors, lines ~357–360, ~384–386)

```tsx
import { formatRunLabel } from "@/lib/run-utils";
// ...
{runs.map((run) => (
  <option key={run.id} value={run.id} disabled={run.id === runBId}>
    {formatRunLabel(run)}
  </option>
))}
```

Same for run B select.

**Step 5: Update prompt-diff/page.tsx** — delete the local `formatRunLabel` function (line 44–46) and replace with import:

```tsx
import { formatRunLabel } from "@/lib/run-utils";
```

(The function signature is identical, so all existing `formatRunLabel(run)` calls work unchanged.)

**Step 6: Run lint + typecheck + tests**

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Expected: 107 passing, 0 errors

**Step 7: Commit**

```bash
git add web/src/lib/run-utils.ts web/src/app/accuracy/page.tsx web/src/app/review/page.tsx web/src/app/prompt-diff/page.tsx
git commit -m "feat: canonical run label utility, used across all run selectors"
```

---

## Batch 2 — Sidebar Workflow Grouping

---

### Task 6: Add section grouping and rename ambiguous nav items

**Files:**
- Modify: `web/src/components/sidebar.tsx`

**Context:** The nav shows 6 items in a flat list with no indication of which tools are for "running evals" vs "analyzing results." Mental model: **Management** (Run Tests) → **Analysis** (everything else). Also: "Review" is ambiguous (confused with Accuracy Review), and "Prompt Diff" is jargon.

🔑 **Pattern:** Sidebar section headers cost nothing and dramatically reduce cognitive load for new users.

**Step 1: Update sidebar.tsx nav definitions**

Replace the `navItems` and `bottomItems` arrays and add a group structure:

```tsx
interface NavGroup {
  label: string;
  items: NavItemDef[];
}

const navGroups: NavGroup[] = [
  {
    label: "Analysis",
    items: [
      { label: "Leaderboard", href: "/leaderboard", icon: Trophy },
      { label: "Accuracy Review", href: "/accuracy", icon: ClipboardCheck },
      { label: "A/B Compare", href: "/review", icon: GitCompareArrows },
      { label: "Run Diff", href: "/prompt-diff", icon: FileDiff },
    ],
  },
  {
    label: "Management",
    items: [
      { label: "Run Tests", href: "/runs", icon: FlaskConical },
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
    ],
  },
];
```

**Step 2: Update the `<nav>` render in Sidebar**

Replace the flat `{navItems.map(...)}` block with grouped rendering:

```tsx
<nav aria-label="Main navigation" className="flex-1 overflow-y-auto px-3 pt-3">
  {navGroups.map((group) => (
    <div key={group.label} className="mb-3">
      {!collapsed && (
        <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
          {group.label}
        </p>
      )}
      <div className="space-y-0.5">
        {group.items.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <NavItem
              key={item.href}
              item={item}
              isActive={isActive}
              collapsed={collapsed}
            />
          );
        })}
      </div>
    </div>
  ))}
</nav>
```

**Step 3: Run lint + typecheck + tests**

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Tests that check nav items by label need updating if any exist. Check:

```bash
cd web && npm test -- --reporter=verbose 2>&1 | grep -i sidebar
```

If sidebar tests exist and reference old labels, update the label strings.

**Step 4: Commit**

```bash
git add web/src/components/sidebar.tsx
git commit -m "feat: sidebar workflow grouping (Analysis/Management) and clearer nav labels"
```

---

## Batch 3 — URL Query Params for Run Context

---

### Task 7: Preserve selected run in accuracy/page.tsx via URL

**Files:**
- Modify: `web/src/app/accuracy/page.tsx`
- Modify: `web/src/app/accuracy/__tests__/page.test.tsx`

**Context:** When a user navigates away from Accuracy Review and returns, they must re-select the run. URL params fix this and make URLs shareable (e.g., `/accuracy?run=42`).

🔑 **Pattern for Next.js App Router:** Use `useSearchParams()` to read, `router.replace(pathname + '?' + params)` to write. Always use `replace` (not `push`) for selector changes to avoid polluting browser history.

**Step 1: Add imports to accuracy/page.tsx**

```tsx
import { useSearchParams, useRouter, usePathname } from "next/navigation";
```

**Step 2: Add hook calls at top of component body** (before existing state)

```tsx
const searchParams = useSearchParams();
const router = useRouter();
const pathname = usePathname();
```

**Step 3: Initialize selectedRunId from URL**

Change:
```tsx
const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
```
To:
```tsx
const [selectedRunId, setSelectedRunId] = useState<number | null>(() => {
  const param = searchParams.get("run");
  return param ? Number(param) : null;
});
```

**Step 4: Sync URL when run changes** — update `handleRunChange`:

```tsx
const handleRunChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
  const val = e.target.value;
  const newId = val ? Number(val) : null;
  setSelectedRunId(newId);
  const params = new URLSearchParams(searchParams.toString());
  if (newId) {
    params.set("run", String(newId));
  } else {
    params.delete("run");
  }
  router.replace(`${pathname}?${params.toString()}`);
};
```

**Step 5: Update test mock for next/navigation**

In `web/src/app/accuracy/__tests__/page.test.tsx`, the existing mock already provides `useRouter` and `usePathname`. Add `useSearchParams`:

```tsx
vi.mock("next/navigation", () => ({
  usePathname: () => "/accuracy",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));
```

**Step 6: Run tests**

```bash
cd web && npm test
```

Expected: 107 passing

**Step 7: Commit**

```bash
git add web/src/app/accuracy/page.tsx web/src/app/accuracy/__tests__/page.test.tsx
git commit -m "feat: persist selected run in URL query param on accuracy page"
```

---

### Task 8: Preserve run selection in review/page.tsx via URL

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Step 1: Add imports**

```tsx
import { useSearchParams, useRouter, usePathname } from "next/navigation";
```

**Step 2: Add hooks at top of component**

```tsx
const searchParams = useSearchParams();
const router = useRouter();
const pathname = usePathname();
```

**Step 3: Initialize runAId + runBId from URL**

```tsx
const [runAId, setRunAId] = useState<number | null>(() => {
  const p = searchParams.get("runA");
  return p ? Number(p) : null;
});
const [runBId, setRunBId] = useState<number | null>(() => {
  const p = searchParams.get("runB");
  return p ? Number(p) : null;
});
```

**Step 4: Create URL-syncing helper**

Add this inside the component, before the handlers:

```tsx
const syncRunParams = useCallback((aId: number | null, bId: number | null) => {
  const params = new URLSearchParams(searchParams.toString());
  if (aId) params.set("runA", String(aId)); else params.delete("runA");
  if (bId) params.set("runB", String(bId)); else params.delete("runB");
  router.replace(`${pathname}?${params.toString()}`);
}, [searchParams, router, pathname]);
```

**Step 5: Call syncRunParams in both onChange handlers**

```tsx
onChange={(e) => {
  const id = e.target.value ? Number(e.target.value) : null;
  setRunAId(id);
  syncRunParams(id, runBId);
}}
// and:
onChange={(e) => {
  const id = e.target.value ? Number(e.target.value) : null;
  setRunBId(id);
  syncRunParams(runAId, id);
}}
```

**Step 6: Run tests**

```bash
cd web && npm test
```

Expected: 107 passing

**Step 7: Commit**

```bash
git add web/src/app/review/page.tsx
git commit -m "feat: persist run A/B selection in URL query params on review page"
```

---

### Task 9: Preserve run selection in prompt-diff/page.tsx via URL

**Files:**
- Modify: `web/src/app/prompt-diff/page.tsx`

**Step 1–5:** Same pattern as Task 8 but with `baseline` and `candidate` params:

```tsx
import { useSearchParams, useRouter, usePathname } from "next/navigation";
// ...
const [baselineRunId, setBaselineRunId] = useState<number | null>(() => {
  const p = searchParams.get("baseline");
  return p ? Number(p) : null;
});
const [candidateRunId, setCandidateRunId] = useState<number | null>(() => {
  const p = searchParams.get("candidate");
  return p ? Number(p) : null;
});
```

Sync helper and onChange handlers follow the same pattern as Task 8 with `baseline`/`candidate` keys.

**Step 6: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/prompt-diff/page.tsx
git commit -m "feat: persist baseline/candidate run selection in URL on prompt-diff page"
```

---

## Batch 4 — Leaderboard Redesign

---

### Task 10: Add sortable columns to DataTable

**Files:**
- Modify: `web/src/components/data-table.tsx`
- Modify: `web/src/app/leaderboard/page.tsx` (enable sort on key columns)

**Context:** Leaderboard users want to sort by ELO, accuracy, cost, etc. This adds optional client-side sort to the existing DataTable component.

🔑 **Pattern:** Add sort state to DataTable as optional controlled props. Pass `sortable: true` on Column definitions where sort makes sense. Never sort by default — preserve original order as default.

**Step 1: Update Column interface and DataTableProps**

```tsx
export interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right" | "center";
  width?: string;
  mono?: boolean;
  sortable?: boolean;  // NEW
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  ariaLabel: string;
  rowKey?: (row: T, index: number) => React.Key;
}
```

**Step 2: Add sort state and sorted data inside DataTable**

```tsx
import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

export function DataTable<T extends object>({ columns, data, ariaLabel, rowKey }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];
      const aStr = String(aVal ?? "");
      const bStr = String(bVal ?? "");
      // Try numeric sort first
      const aNum = parseFloat(aStr.replace(/[^0-9.-]/g, ""));
      const bNum = parseFloat(bStr.replace(/[^0-9.-]/g, ""));
      const cmp = isNaN(aNum) || isNaN(bNum)
        ? aStr.localeCompare(bStr)
        : aNum - bNum;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };
  // ... render uses sortedData
```

**Step 3: Update header cells to show sort UI for sortable columns**

```tsx
<th key={col.key} scope="col" className={cn(...)}>
  {col.sortable ? (
    <button
      onClick={() => handleSort(col.key)}
      className="flex items-center gap-0.5 hover:text-foreground transition-colors"
    >
      {col.label}
      {sortKey === col.key ? (
        sortDir === "asc" ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />
      ) : (
        <ChevronsUpDown className="size-3 opacity-40" />
      )}
    </button>
  ) : (
    col.label
  )}
</th>
```

**Step 4: Mark sortable columns in leaderboard/page.tsx**

Add `sortable: true` to these `leaderboardColumns` entries: `elo`, `winPct`, `parseRate`, `accuracy`, `cost`, `latency`.

**Step 5: Run tests**

```bash
cd web && npm test
```

Expected: 107 passing (DataTable has no test currently — no need to add one now, covered by existing render tests)

**Step 6: Commit**

```bash
git add web/src/components/data-table.tsx web/src/app/leaderboard/page.tsx
git commit -m "feat: sortable columns in DataTable, enabled on leaderboard"
```

---

### Task 11: Add model/prompt filter chips to leaderboard

**Files:**
- Modify: `web/src/app/leaderboard/page.tsx`

**Context:** The only current filter is Pass (All/1/2). Researchers commonly want to isolate a specific model. This adds model and prompt filter chips alongside the existing pass filter.

**Step 1: Add filter state**

```tsx
const [modelFilter, setModelFilter] = useState<string>("all");
const [promptFilter, setPromptFilter] = useState<string>("all");
```

**Step 2: Derive filter option lists**

```tsx
const modelOptions = useMemo(() => {
  const models = [...new Set(runs.map((r) => r.model))].sort();
  return ["all", ...models];
}, [runs]);

const promptOptions = useMemo(() => {
  const prompts = [...new Set(runs.map((r) => r.prompt_version))].sort();
  return ["all", ...prompts];
}, [runs]);
```

**Step 3: Apply filters to filteredRuns**

Update the existing `filteredRuns` useMemo:

```tsx
const filteredRuns = useMemo(() => {
  return runs.filter((r) => {
    if (passFilter !== "all" && r.pass_number !== passFilter) return false;
    if (modelFilter !== "all" && r.model !== modelFilter) return false;
    if (promptFilter !== "all" && r.prompt_version !== promptFilter) return false;
    return true;
  });
}, [runs, passFilter, modelFilter, promptFilter]);
```

**Step 4: Add filter UI above the existing pass filter buttons**

Replace the existing pass filter `<div>` with a combined filter bar:

```tsx
<div className="flex flex-wrap items-center gap-3">
  {/* Pass filter */}
  <div className="flex items-center gap-1">
    <span className="text-[11px] text-muted-foreground/60 mr-1">Pass</span>
    {passOptions.map((opt) => (
      <button key={String(opt.value)} onClick={() => setPassFilter(opt.value)}
        className={`rounded px-2 py-1 text-[12px] font-medium transition-colors ${
          passFilter === opt.value
            ? "bg-primary text-primary-foreground"
            : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
        }`}>
        {opt.label}
      </button>
    ))}
  </div>
  {/* Model filter */}
  {modelOptions.length > 2 && (
    <div className="flex items-center gap-1">
      <span className="text-[11px] text-muted-foreground/60 mr-1">Model</span>
      {modelOptions.map((m) => (
        <button key={m} onClick={() => setModelFilter(m)}
          className={`rounded px-2 py-1 text-[12px] font-medium transition-colors ${
            modelFilter === m
              ? "bg-primary text-primary-foreground"
              : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
          }`}>
          {m === "all" ? "All" : m}
        </button>
      ))}
    </div>
  )}
  {/* Results count */}
  <span className="ml-auto text-[11px] text-muted-foreground/60">
    {filteredRuns.length} of {runs.length} runs
  </span>
</div>
```

**Step 5: Run tests + commit**

```bash
cd web && npm run typecheck && npm test
git add web/src/app/leaderboard/page.tsx
git commit -m "feat: model/prompt filter chips on leaderboard"
```

---

### Task 12: Color-code field accuracy values in leaderboard table

**Files:**
- Modify: `web/src/app/leaderboard/page.tsx` (fieldAccuracyColumns)

**Context:** The field accuracy table shows raw percentages with no visual cues. Color-coding makes best/worst fields instantly scannable.

**Step 1: Update field accuracy column render**

In `fieldAccuracyColumns`, replace the default render (which shows raw string) with a colored version:

```tsx
cols.push({
  key: field,
  label: field,
  align: "center",
  mono: true,
  sortable: true,
  render: (row) => {
    const val = row[field];
    if (val === "—") return <span className="text-muted-foreground/50">—</span>;
    const num = parseFloat(val);
    return (
      <span className={cn(
        "font-mono tabular-nums text-[12px]",
        num >= 90 ? "text-threshold-high font-medium" :
        num >= 70 ? "text-threshold-mid" :
        "text-threshold-low"
      )}>
        {val}
      </span>
    );
  },
});
```

**Step 2: Add ELO column tooltip**

In `leaderboardColumns`, update the `elo` entry:

```tsx
{
  key: "elo",
  label: "Elo",
  mono: true,
  render: (row) => (
    <span className="font-mono font-semibold tabular-nums" title="ELO rating calculated from A/B comparison votes. Higher = better.">
      {row.elo}
    </span>
  ),
},
```

**Step 3: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/leaderboard/page.tsx
git commit -m "feat: color-coded field accuracy values and ELO tooltip on leaderboard"
```

---

### Task 13: Add next-step link from leaderboard to Review

**Files:**
- Modify: `web/src/app/leaderboard/page.tsx`

**Context:** After viewing the leaderboard, the natural next action is to do more A/B comparisons to improve ELO data. Add a link at the bottom.

**Step 1: Add a footer link below both tables**

At the bottom of the main content, after the field accuracy section and before `</div>` closing `space-y-6`:

```tsx
<div className="flex items-center justify-end border-t border-border/50 pt-4">
  <Link href="/review" className="text-[12px] text-primary hover:underline">
    Compare runs to improve ELO data →
  </Link>
</div>
```

Add `import Link from "next/link";` at the top.

**Step 2: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/leaderboard/page.tsx
git commit -m "feat: add next-step link from leaderboard to A/B compare"
```

---

## Batch 5 — Review Page Improvements

---

### Task 14: Add keyboard shortcuts to review/page.tsx

**Files:**
- Modify: `web/src/app/review/page.tsx`
- Create: `web/src/app/review/__tests__/page.test.tsx`

**Context:** The accuracy page has 9 keyboard shortcuts; the review page has zero. For heavy comparison sessions, mouse-only is a serious bottleneck.

Bindings:
- `a` → vote "A is Better"
- `b` → vote "B is Better"
- `t` → vote "Tie"
- `x` → vote "Both Bad"
- `ArrowLeft` → go to previous posting
- `ArrowRight` → go to next posting
- `Escape` → no-op (reserved, could undo in future)

🔑 **Pattern:** The keyboard handler guard pattern from accuracy page works here too: check `target.tagName` before processing keys, guard against `TEXTAREA` (notes field) and modifier keys.

**Step 1: Add imports**

```tsx
import { useState, useEffect, useCallback, useMemo } from "react";
```

(`useEffect` is already imported)

**Step 2: Add the VOTE_KEY_MAP constant** (near VOTE_BUTTONS definition)

```tsx
const VOTE_KEY_MAP: Record<string, VoteWinner> = {
  a: "a",
  b: "b",
  t: "tie",
  x: "both_bad",
};
```

**Step 3: Add document-level keyboard handler** (after the existing `useCallback` handlers)

```tsx
useEffect(() => {
  if (!currentItem || totalComparisons === 0) return;

  const handleKeyDown = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.tagName === "INPUT") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    const voteWinner = VOTE_KEY_MAP[e.key];
    if (voteWinner) {
      e.preventDefault();
      handleVote(voteWinner);
      return;
    }

    if (e.key === "ArrowLeft") {
      e.preventDefault();
      goPrev();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      goNext();
    }
  };

  document.addEventListener("keydown", handleKeyDown);
  return () => document.removeEventListener("keydown", handleKeyDown);
}, [currentItem, totalComparisons, handleVote, goPrev, goNext]);
```

**Step 4: Add hotkey legend** below the vote buttons (after the `voteError` block and before closing `</div>` of vote section):

```tsx
<div className="mt-3 border-t border-border/50 pt-2">
  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
    {[
      ["A", "A Better"],
      ["B", "B Better"],
      ["T", "Tie"],
      ["X", "Both Bad"],
      ["←→", "Navigate"],
    ].map(([key, label]) => (
      <span key={key} className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
        <kbd className="rounded border border-border/50 bg-muted px-1 py-0.5 font-mono text-[10px] text-muted-foreground">
          {key}
        </kbd>
        {label}
      </span>
    ))}
  </div>
</div>
```

**Step 5: Write keyboard interaction tests**

Create `web/src/app/review/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@/__tests__/helpers/render";
import userEvent from "@testing-library/user-event";

const { mockCreateComparison } = vi.hoisted(() => ({
  mockCreateComparison: vi.fn().mockResolvedValue({ id: 1 }),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/review",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));
vi.mock("next-themes", () => ({
  useTheme: () => ({ setTheme: vi.fn(), resolvedTheme: "light", theme: "light" }),
}));
vi.mock("@/lib/api-client", () => ({
  getRuns: vi.fn().mockResolvedValue([
    { id: 1, model: "haiku-3.5", prompt_version: "pass1_v1", pass_number: 1, corpus_size: 50, created_at: "2026-02-18T00:00:00", total_duration_ms: 1000, total_cost_usd: 0.1, total_input_tokens: 1000, total_output_tokens: 500 },
    { id: 2, model: "sonnet-4", prompt_version: "pass1_v2", pass_number: 1, corpus_size: 50, created_at: "2026-02-19T00:00:00", total_duration_ms: 1200, total_cost_usd: 0.2, total_input_tokens: 1200, total_output_tokens: 600 },
  ]),
  getRunResults: vi.fn().mockImplementation((id: number) =>
    Promise.resolve([{ id: id === 1 ? 101 : 201, run_id: id, posting_id: "posting-1", parsed_result: JSON.stringify({ role_archetype: "manager" }), parse_success: true, raw_response: null, input_tokens: 100, output_tokens: 50, cost_usd: 0.001, latency_ms: 500 }])
  ),
  getCorpus: vi.fn().mockResolvedValue([
    { id: "posting-1", company_slug: "acme", title: "Manager", location: "Remote", full_text: "Job posting", reference_pass1: null, reference_pass2: null },
  ]),
  getComparisons: vi.fn().mockResolvedValue([]),
  createComparison: mockCreateComparison,
}));

import ReviewPage from "@/app/review/page";

async function selectRuns() {
  const selects = await screen.findAllByRole("combobox");
  const [selectA, selectB] = selects;
  await userEvent.selectOptions(selectA, "1");
  await userEvent.selectOptions(selectB, "2");
  await waitFor(() => expect(screen.getByText("Which extraction is better?")).toBeInTheDocument());
  selectA.blur();
  selectB.blur();
}

describe("ReviewPage keyboard shortcuts", () => {
  it("pressing A votes 'a'", async () => {
    render(<ReviewPage />);
    await selectRuns();
    mockCreateComparison.mockClear();
    await userEvent.keyboard("a");
    await waitFor(() => expect(mockCreateComparison).toHaveBeenCalledWith(
      expect.objectContaining({ winner: "a" })
    ));
  });

  it("pressing B votes 'b'", async () => {
    render(<ReviewPage />);
    await selectRuns();
    mockCreateComparison.mockClear();
    await userEvent.keyboard("b");
    await waitFor(() => expect(mockCreateComparison).toHaveBeenCalledWith(
      expect.objectContaining({ winner: "b" })
    ));
  });

  it("pressing T votes 'tie'", async () => {
    render(<ReviewPage />);
    await selectRuns();
    mockCreateComparison.mockClear();
    await userEvent.keyboard("t");
    await waitFor(() => expect(mockCreateComparison).toHaveBeenCalledWith(
      expect.objectContaining({ winner: "tie" })
    ));
  });

  it("pressing X votes 'both_bad'", async () => {
    render(<ReviewPage />);
    await selectRuns();
    mockCreateComparison.mockClear();
    await userEvent.keyboard("x");
    await waitFor(() => expect(mockCreateComparison).toHaveBeenCalledWith(
      expect.objectContaining({ winner: "both_bad" })
    ));
  });
});
```

**Step 6: Run tests to verify they pass**

```bash
cd web && npm test
```

Expected: 111 passing (107 existing + 4 new keyboard tests)

**Step 7: Commit**

```bash
git add web/src/app/review/page.tsx web/src/app/review/__tests__/page.test.tsx
git commit -m "feat: keyboard shortcuts for voting on review page (a/b/t/x + arrow nav)"
```

---

### Task 15: Show prominent run labels in review comparison header

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Context:** The A/B panels show generic "Run A" and "Run B" labels. Since sides are randomized to reduce bias, reviewers must track which run they're actually looking at. Prominent run identity labels prevent confusion.

**Step 1: Derive display run labels from selected IDs and swap state**

Add this derived value inside the component (after `displayedPair`):

```tsx
const runALabel = useMemo(() => {
  const run = runs.find((r) => r.id === runAId);
  return run ? formatRunLabel(run) : "Run A";
}, [runs, runAId]);

const runBLabel = useMemo(() => {
  const run = runs.find((r) => r.id === runBId);
  return run ? formatRunLabel(run) : "Run B";
}, [runs, runBId]);

const displayALabel = displayedPair?.actualAIsRunA ? runALabel : runBLabel;
const displayBLabel = displayedPair?.actualAIsRunA ? runBLabel : runALabel;
```

**Step 2: Update FieldComparisonPanel call to pass actual labels**

```tsx
<FieldComparisonPanel label={displayALabel} fields={fieldsA} otherFields={fieldsB} />
<FieldComparisonPanel label={displayBLabel} fields={fieldsB} otherFields={fieldsA} />
```

**Step 3: Add randomization notice** to the comparison area (above the two panels):

```tsx
<p className="mt-4 text-[11px] text-muted-foreground/50 text-center">
  Sides are randomized per posting to reduce bias — judge by content, not position.
</p>
```

**Step 4: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/review/page.tsx
git commit -m "feat: show actual run labels in comparison panels, add randomization notice"
```

---

### Task 16: Block cross-pass comparisons on review page

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Context:** Comparing Pass 1 vs Pass 2 results in invalid comparisons because the field schemas differ. Currently shows a warning but loads data anyway. This should be a hard block.

**Step 1: Add passMismatch derived value**

```tsx
const passMismatch = useMemo(() => {
  if (runAId === null || runBId === null) return false;
  const runA = runs.find((r) => r.id === runAId);
  const runB = runs.find((r) => r.id === runBId);
  return !!(runA && runB && runA.pass_number !== runB.pass_number);
}, [runs, runAId, runBId]);
```

**Step 2: Replace the existing mismatch warning** (lines 394–406) with a blocking error state:

```tsx
{passMismatch && (
  <div className="mt-4 rounded-lg border border-error/30 bg-error-muted p-4 text-[13px] text-status-wrong">
    Cannot compare runs with different pass numbers. Please select two Pass 1 or two Pass 2 runs.
  </div>
)}
```

**Step 3: Guard the data loading effect** — add early return if passMismatch:

In the `useEffect` that triggers when `runAId`/`runBId` change:

```tsx
if (runAId === null || runBId === null) { /* reset */ return; }
// NEW:
const runA = runs.find((r) => r.id === runAId);
const runB = runs.find((r) => r.id === runBId);
if (runA && runB && runA.pass_number !== runB.pass_number) return;
```

Note: `runs` must be in the dependency array.

**Step 4: Guard the main content render** — wrap the main content block:

```tsx
{!passMismatch && (runAId === null || runBId === null) ? (
  // existing empty state
) : !passMismatch && dataLoading ? (
  // existing loading state
) : !passMismatch && totalComparisons === 0 ? (
  // existing no common postings state
) : !passMismatch ? (
  // existing comparison UI
) : null}
```

**Step 5: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/review/page.tsx
git commit -m "fix: block cross-pass comparisons with hard error instead of soft warning"
```

---

### Task 17: Vote save confirmation feedback

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Context:** After clicking a vote button, the only feedback is `submitting` disabling buttons briefly. No success indication before auto-advance. Add a brief "✓ Saved" flash.

**Step 1: Add lastVotedPosting state**

```tsx
const [lastSavedPostingId, setLastSavedPostingId] = useState<string | null>(null);
```

**Step 2: In handleVote, after `setVotes(...)`, set lastSaved and clear it after 800ms**

```tsx
setVotes((prev) => ({ ...prev, [currentItem.postingId]: winner }));
setLastSavedPostingId(currentItem.postingId);
setTimeout(() => setLastSavedPostingId(null), 800);
```

**Step 3: Show the confirmation** — in the vote section header area, add a small indicator:

```tsx
<h3 className="font-display mb-4 text-[14px] font-semibold text-foreground flex items-center gap-2">
  Which extraction is better?
  {lastSavedPostingId && (
    <span className="text-[11px] font-normal text-status-correct animate-pulse">✓ Saved</span>
  )}
</h3>
```

**Step 4: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/review/page.tsx
git commit -m "feat: show brief save confirmation after voting on review page"
```

---

### Task 18: Add next-step link from review page to leaderboard

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Context:** After completing comparisons, there's no path to the leaderboard. When all postings are voted, show a "View rankings →" link.

**Step 1: Add allVoted derived value**

```tsx
const allVoted = totalComparisons > 0 && Object.keys(votes).length >= totalComparisons;
```

**Step 2: Add next-step banner** above the hotkey legend in vote section:

```tsx
{allVoted && (
  <div className="mt-4 flex items-center justify-between rounded-md border border-success/30 bg-success-muted px-4 py-2.5">
    <span className="text-[12px] text-status-correct font-medium">
      All {totalComparisons} comparisons complete
    </span>
    <Link href="/leaderboard" className="text-[12px] text-primary hover:underline font-medium">
      View updated rankings →
    </Link>
  </div>
)}
```

**Step 3: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/review/page.tsx
git commit -m "feat: show next-step link to leaderboard when all comparisons are voted"
```

---

## Batch 6 — Accuracy Page Polish

---

### Task 19: Mini-dots size + save confirmation pulse

**Files:**
- Modify: `web/src/app/accuracy/page.tsx`

**Step 1: Increase mini-dot size** (line ~590)

```tsx
className={cn(
  "h-2 w-2 rounded-full",  // was h-1.5 w-1.5
  currentReviews[f] ? "bg-primary" : "bg-muted",
)}
```

**Step 2: Add save confirmation state**

```tsx
const [savedField, setSavedField] = useState<string | null>(null);
```

**Step 3: Set savedField after successful save** in `handleJudgment`, after `setReviews(...)`:

```tsx
setSavedField(fieldName);
setTimeout(() => setSavedField(null), 600);
```

**Step 4: Show brief ✓ in the field row** — in the field row render, add to the status badge area:

```tsx
{savedField === field ? (
  <span className="shrink-0 text-[11px] font-medium text-status-correct animate-pulse">✓</span>
) : (
  <StatusBadge status={status} size="sm" />
)}
```

**Step 5: Fix replace mode input background** (line ~801) — remove `bg-background` so it inherits the `bg-warning-muted` parent:

```tsx
className="w-28 rounded border border-warning/60 px-2 py-0.5 font-mono text-[12px] focus:outline-none focus:ring-1 focus:ring-primary"
```

**Step 6: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/accuracy/page.tsx
git commit -m "feat: larger mini-dots, field save pulse, replace input bg fix on accuracy page"
```

---

### Task 20: Mark All Correct confirmation modal

**Files:**
- Modify: `web/src/app/accuracy/page.tsx`

**Context:** One accidental keypress (`a`) marks 13 fields. A lightweight inline confirmation prevents this.

🔑 **Pattern:** For actions that mark many items at once, require a two-step confirm rather than a modal dialog. Modals interrupt flow; an inline "are you sure?" in the same location is faster to dismiss.

**Step 1: Add confirm state**

```tsx
const [confirmAllCorrect, setConfirmAllCorrect] = useState(false);
```

**Step 2: Update `a` keyboard handler** — don't call `handleMarkAllCorrect` directly:

```tsx
case "a":
  if (!confirmAllCorrect) {
    setConfirmAllCorrect(true);
    setTimeout(() => setConfirmAllCorrect(false), 3000); // auto-dismiss after 3s
  } else {
    setConfirmAllCorrect(false);
    handleMarkAllCorrect();
  }
  break;
```

**Step 3: Also clear confirmAllCorrect on posting navigation** — add to the `useEffect` on `postingIdx`:

```tsx
setConfirmAllCorrect(false);
```

**Step 4: Update the "[A] All ✓" button** in the panel header:

```tsx
{confirmAllCorrect ? (
  <div className="flex items-center gap-1.5">
    <span className="text-[11px] text-warning-foreground">Mark all 13 correct?</span>
    <button
      onClick={() => { setConfirmAllCorrect(false); handleMarkAllCorrect(); }}
      className="rounded border border-success/40 bg-success-muted px-2 py-0.5 text-[11px] font-medium text-status-correct"
    >
      Yes [A]
    </button>
    <button
      onClick={() => setConfirmAllCorrect(false)}
      className="rounded border border-border px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
    >
      Cancel
    </button>
  </div>
) : (
  <button onClick={() => setConfirmAllCorrect(true)}
    className="rounded border border-success/40 bg-success-muted px-2 py-0.5 text-[11px] font-medium text-status-correct transition-colors hover:bg-success-muted">
    [A] All ✓
  </button>
)}
```

**Step 5: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/accuracy/page.tsx
git commit -m "feat: two-step confirmation for Mark All Correct on accuracy page"
```

---

### Task 21: Add next-step link from accuracy page to A/B compare

**Files:**
- Modify: `web/src/app/accuracy/page.tsx`

**Context:** After reviewing all postings, there's no path to the Review page.

**Step 1: Add allPostingsComplete derived value**

```tsx
const allPostingsComplete = results.length > 0 && postingsComplete === results.length;
```

**Step 2: Add next-step banner** in the navigation bar area — after the `goPostingNext` button:

```tsx
{allPostingsComplete && (
  <div className="mt-3 flex items-center justify-between rounded-md border border-success/30 bg-success-muted px-4 py-2.5">
    <span className="text-[12px] text-status-correct font-medium">
      All {results.length} postings reviewed
    </span>
    <Link
      href={`/review?runA=${selectedRunId}`}
      className="text-[12px] text-primary hover:underline font-medium"
    >
      Compare with another run →
    </Link>
  </div>
)}
```

Add `import Link from "next/link";` to imports.

**Step 3: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/accuracy/page.tsx
git commit -m "feat: show next-step link to A/B compare when all accuracy reviews complete"
```

---

## Batch 7 — Runs Page + Prompt Diff

---

### Task 22: Run creation confirmation step

**Files:**
- Modify: `web/src/app/runs/page.tsx`

**Context:** "Start Run" immediately fires an expensive API call with no summary review. Adding a confirmation step shows a summary of what will run before submission.

🔑 **Pattern:** For expensive/irreversible async operations, always show "confirm parameters" before executing. This is especially important for API calls that cost money.

**Step 1: Add confirmStep state**

```tsx
const [confirmStep, setConfirmStep] = useState(false);
```

**Step 2: Update handleSubmit** — make it a two-step function:

Rename existing `handleSubmit` to `executeRun`. Create new `handleSubmit`:

```tsx
const handleSubmit = () => {
  if (!selectedModel || !selectedPrompt) {
    setFormError("Please select a model and prompt.");
    return;
  }
  setFormError(null);
  setConfirmStep(true);
};

const executeRun = async () => {
  setConfirmStep(false);
  setSubmitting(true);
  setProgress(null);
  try {
    const result = await createRun({ pass_number: passNumber, model: selectedModel, prompt_version: selectedPrompt, concurrency });
    setTrackingId(result.tracking_id);
    setProgress({ status: "starting", completed: 0, total: result.total });
  } catch (err) {
    setFormError(err instanceof Error ? err.message : "Failed to create run");
    setSubmitting(false);
  }
};
```

**Step 3: Add confirmation UI** above the form's action buttons (before the `<div className="mt-4 flex gap-2">`):

```tsx
{confirmStep && !submitting && (
  <div className="mt-4 rounded-md border border-warning/40 bg-warning-muted px-4 py-3">
    <p className="mb-2 text-[12px] font-medium text-warning-foreground">
      Ready to start run:
    </p>
    <ul className="mb-3 space-y-0.5 text-[12px] text-muted-foreground">
      <li>Pass {passNumber} · {selectedModel} · {selectedPrompt}</li>
      <li>Concurrency: {concurrency} | Corpus: all postings</li>
    </ul>
    <div className="flex gap-2">
      <button onClick={executeRun}
        className="rounded-md border border-border bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90">
        Confirm &amp; Start
      </button>
      <button onClick={() => setConfirmStep(false)}
        className="rounded-md border border-border bg-muted/30 px-3 py-1.5 text-[13px] font-medium text-muted-foreground hover:bg-muted/50">
        Back
      </button>
    </div>
  </div>
)}
```

**Step 4: Hide original Start Run button when in confirm step**

Change the existing `<button onClick={handleSubmit} ...>Start Run</button>`:

```tsx
{!confirmStep && (
  <button onClick={handleSubmit} disabled={submitting || !selectedModel || !selectedPrompt}
    className="rounded-md border border-border bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
    {submitting ? "Running\u2026" : "Start Run"}
  </button>
)}
```

**Step 5: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/runs/page.tsx
git commit -m "feat: add parameter confirmation step before starting an evaluation run"
```

---

### Task 23: Rename Prompt Diff and add collapsible prompt text

**Files:**
- Modify: `web/src/app/prompt-diff/page.tsx`
- Modify: `web/src/components/sidebar.tsx` (already done in Task 6 — verify)

**Context:** "Prompt Diff" is jargon and the page doesn't show the actual prompt text — only extraction result comparisons. Rename to "Run Diff" and add a note explaining what's being compared.

**Step 1: Update the AppShell title and subtitle**

```tsx
<AppShell title="Run Diff" subtitle="Field-level extraction comparison">
```

**Step 2: Add a description line below the run selectors**

```tsx
<p className="mt-3 text-[12px] text-muted-foreground/60">
  Compares extracted field values between two runs on the same corpus.
  Use this to measure how much extraction changed between prompt versions or models.
</p>
```

**Step 3: Run tests + commit**

```bash
cd web && npm test
git add web/src/app/prompt-diff/page.tsx
git commit -m "feat: rename Prompt Diff to Run Diff, add descriptive subtitle"
```

---

## Batch 8 — Verification and Final Polish

---

### Task 24: Full verification pass

**Step 1: Run the full test suite**

```bash
cd web && npm test
```

Expected: 111+ tests passing, 0 failures

**Step 2: Run typecheck**

```bash
cd web && npm run typecheck
```

Expected: 0 errors

**Step 3: Run lint**

```bash
cd web && npm run lint
```

Expected: 0 warnings (--max-warnings 0)

**Step 4: Fix any issues discovered above before proceeding**

**Step 5: Commit verification results (if any small fixes)**

```bash
git add -p  # stage only the specific fixes
git commit -m "fix: lint and typecheck cleanup"
```

---

### Task 25: Update memory notes with patterns and learnings

**Step 1: Update memory file**

Add to `/Users/vmud/.claude/projects/-Users-vmud-Documents-dev-projects-compgraph-eval/memory/MEMORY.md`:

Key patterns learned in this branch that apply to the main project:
- **URL query params:** `useSearchParams` + `router.replace` for run selectors
- **Keyboard handler guard:** check `target.tagName` before processing keys
- **Confirmation pattern:** inline two-step (not modal) for bulk actions
- **Token naming:** purpose-first (`medal-gold`, `threshold-high`), never value-first (`#D4A017`)
- **DataTable:** always `overflow-x-auto` wrapper
- **Next-step links:** each page should know its downstream successor

**Step 2: Final commit**

```bash
git add .
git commit -m "docs: update memory with UX patterns for main project"
```

---

## Summary of Changes

| File | Type | Key Change |
|------|------|-----------|
| `globals.css` | tokens | Medal + threshold tokens |
| `data-table.tsx` | component | overflow-x-auto, sortable columns |
| `error-box.tsx` | component | NEW — shared error UI |
| `loading-card.tsx` | component | NEW — shared loading UI |
| `run-utils.ts` | utility | NEW — canonical run label |
| `sidebar.tsx` | nav | Grouped sections, renamed items |
| `leaderboard/page.tsx` | page | Sort, filter chips, color-coded accuracy, medal tokens, next-step link |
| `review/page.tsx` | page | Keyboard shortcuts, run labels, pass block, vote confirmation, next-step link |
| `accuracy/page.tsx` | page | Mini-dots, save pulse, confirm-all, replace bg fix, next-step link |
| `runs/page.tsx` | page | Confirmation step, token fixes |
| `prompt-diff/page.tsx` | page | Rename, description, token fixes, canonical labels |
| `review/__tests__/page.test.tsx` | test | NEW — keyboard shortcut tests |

**Test count:** 107 → 111+ (4+ new keyboard tests for review page)
