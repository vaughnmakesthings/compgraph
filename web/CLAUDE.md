# web/CLAUDE.md

Frontend for CompGraph — Next.js 16 App Router deployed to Vercel.

## Commands

```bash
npm run dev              # Dev server (localhost:3000)
npm run build            # Production build
npm run lint             # ESLint strict (--max-warnings 0)
npm run typecheck        # TypeScript --noEmit
npm test                 # Vitest run
npm run test:coverage    # v8 coverage (50% line/function/statement, 30% branch)
npm run test:watch       # Vitest watch mode
```

## Stack

- **Next.js 16** (App Router, React 19) — all pages are `"use client"` today, no RSC data fetching yet
- **Tailwind CSS v4** — `@theme` block in `globals.css`, no `tailwind.config.js`
- **@tremor/react** — chart wrappers (BarChart, AreaChart, DonutChart) and data viz primitives
- **Recharts 3** — underlying chart engine (Tremor wraps it)
- **@heroicons/react** — icons (outline variant, 24px)
- **@radix-ui** — Dialog, DropdownMenu, Tooltip, Slot primitives
- **Vitest 4 + jsdom** — test runner with React Testing Library

## Project Structure

```
src/
  app/                    # Next.js App Router pages
    layout.tsx            # Root layout — wraps children in Shell
    page.tsx              # Dashboard (Pipeline Health)
    globals.css           # @theme tokens, font imports, Tremor safelist
    competitors/          # Competitor list + [slug] dossier
    eval/                 # 5 sub-pages: runs, review, accuracy, leaderboard, prompt-diff
    hiring/               # Job Feed (posting explorer)
    market/               # Market Overview
    prospects/            # Prospects list + [slug] detail
    settings/             # Pipeline controls, run history
  components/
    layout/               # Shell, Sidebar, Header (barrel: index.ts)
    charts/               # BarChart, AreaChart, DonutChart wrappers (barrel: index.ts)
    data/                 # KpiCard, Badge, TablePagination (barrel: index.ts)
    ui/                   # Button, Skeleton, SectionCard, ConfirmDialog
    content/              # MockupBanner, Callout
  lib/
    api-client.ts         # Typed API client (single apiFetch wrapper)
    types.ts              # All API response interfaces
    constants.ts          # API_BASE, COMPANIES array
    utils.ts              # Shared utility functions
    mock/                 # Mock data for prospects/dossiers
  test/
    setup.ts              # jest-dom matchers import
    *.test.tsx             # Test files colocated by page/feature
    components/            # Component-specific test files
```

## Architecture Patterns

### API Client

All backend calls go through `src/lib/api-client.ts`. The pattern:

1. `apiFetch<T>(path, options?)` — generic wrapper that prepends `API_BASE`, sets JSON headers, sanitizes error detail (XSS protection), throws on non-OK responses
2. `api` object — named methods per endpoint, each returning typed promises
3. Query params built with `URLSearchParams`, appended only when non-empty
4. `API_BASE` from `NEXT_PUBLIC_API_URL` env var (defaults to `http://localhost:8000`)

**Rule:** Never call `fetch()` directly in pages. Always add new endpoints to the `api` object.

### Data Fetching

Pages use `useState` + `useEffect` + `api.*` calls. The established pattern:

```typescript
const [data, setData] = useState<T | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  api.getSomething()
    .then(setData)
    .catch((err) => setError(err instanceof Error ? err.message : "Failed"))
    .finally(() => setLoading(false));
}, []);
```

For pages needing multiple parallel fetches, use `Promise.all` (see `page.tsx` dashboard).

For live polling (pipeline controls), use `setInterval` with terminal-state detection to auto-stop:

```typescript
const TERMINAL_STATES = new Set(["success", "partial", "failed", "cancelled"]);
// Poll every 3s, clear interval when status hits a terminal state
```

### Component Organization

- **Barrel exports** — each component directory has `index.ts` re-exporting public components
- **Import via barrel** — `import { Shell } from "@/components/layout"` (not direct file path)
- **`"use client"` directive** — required on every component using hooks, event handlers, or browser APIs
- **Props interfaces** — defined inline in the same file, not extracted to types.ts (types.ts is API-only)

### Design Tokens

All design decisions flow from CSS variables defined in `globals.css` `@theme` block. Reference by `var(--token)` in inline styles or by Tailwind arbitrary values.

| Token | Value | Usage |
|-------|-------|-------|
| `--color-jet-black` | `#2D3142` | Text, sidebar background |
| `--color-coral` | `#EF8354` | Primary accent, active indicators, chart-1 |
| `--color-blue-slate` | `#4F5D75` | Secondary text, muted icons |
| `--color-silver` | `#BFC0C0` | Borders |
| `--color-teal-jade` | `#1B998B` | Success, positive trends, chart-2 |
| `--color-chestnut` | `#8C2C23` | Error, negative trends, chart-5 |
| `--color-warm-gold` | `#DCB256` | Warning, chart-4 |
| `--color-background` | `#F4F4F0` | Page background |
| `--color-surface` | `#FFFFFF` | Card/panel background |

**Typography:** Three font families loaded via `@fontsource-variable`:
- `--font-display` — Sora Variable (headings, logo)
- `--font-body` — DM Sans Variable (body text, labels)
- `--font-mono` — JetBrains Mono Variable (KPI values, data, code)

**Radius scale:** `--radius-sm` (4px) for inputs/badges, `--radius-md` (6px) for buttons, `--radius-lg` (8px) for cards, `--radius-xl` (12px) for modals.

**Shadow scale:** `--shadow-sm` for cards, `--shadow-md` for dropdowns, `--shadow-lg` for modals.

**Chart palette:** 5-color sequence: coral, teal, slate, gold, chestnut. Passed to Tremor via `CHART_COLORS` array in chart wrappers. Safelist classes declared in `globals.css` `@source inline(...)` for Tailwind v4 JIT.

### Tremor Chart Wrappers

Charts are thin wrappers around `@tremor/react` in `src/components/charts/`:

- Accept domain-specific props (data array, category config)
- Map to Tremor's `categories` / `colors` / `index` API
- Apply `--font-body` to chart container
- Export via barrel: `import { BarChart } from "@/components/charts"`

When testing, mock `@tremor/react` to avoid canvas/ResizeObserver issues:

```typescript
vi.mock("@tremor/react", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@tremor/react")>();
  return {
    ...mod,
    BarChart: ({ data }) => <div data-testid="bar-chart">{JSON.stringify(data)}</div>,
  };
});

global.ResizeObserver = class ResizeObserver {
  observe = vi.fn(); unobserve = vi.fn(); disconnect = vi.fn();
};
```

## Test Conventions

- **Framework:** Vitest 4 + React Testing Library + jsdom
- **Location:** `src/test/` directory (not colocated with source)
- **Path alias:** `@/` maps to `src/` via vitest.config.ts `resolve.alias`
- **Globals:** `globals: true` in vitest config — `vi`, `describe`, `it`, `expect` available without import
- **Setup:** `src/test/setup.ts` imports `@testing-library/jest-dom` matchers

### What to Test

1. **Page rendering** — heading text, key labels, structural elements
2. **Loading states** — skeleton placeholders visible before data resolves
3. **Data display** — correct values derived from mock API responses
4. **Error states** — alert role present when API rejects
5. **Accessibility** — `aria-busy`, `aria-label`, `aria-current="page"`, `role="alert"`
6. **User interactions** — button clicks, filter toggles, pagination

### Test Patterns

- Mock `api` object methods, not `fetch`: `vi.mock("@/lib/api-client")`
- Use `vi.mocked(api)` for type-safe mock setup
- Use `waitFor` for async state updates after API resolution
- Never-resolving promises for loading state tests: `mockFn.mockReturnValue(new Promise(() => {}))`
- `beforeEach(() => vi.clearAllMocks())` in every test file

## Design Antipatterns

See the root `CLAUDE.md` section "Frontend Design Antipatterns" for the full list. Key rules:

- No purple/indigo/violet — use the brand palette above
- No gradient heroes — solid backgrounds with subtle borders
- No glassmorphism — solid `#FFFFFF` surfaces
- No `transition-all` — specify exact properties (`transition-colors`, `transition-opacity`)
- No decorative icons — every icon communicates meaning
- No uniform border-radius — use the radius scale by component role

## Common Pitfalls

- **Tailwind v4 has no config file.** All theming is in `globals.css` `@theme` block. Don't create `tailwind.config.js`.
- **Tremor chart colors need safelist.** If you add a new chart color hex, add `fill-[#hex]` and `stroke-[#hex]` to the `@source inline(...)` block in `globals.css` or Tailwind v4 JIT won't generate the classes.
- **`startTransition` for non-urgent state updates.** Sidebar expand/collapse uses `startTransition` to avoid blocking React 19 concurrent renders. Use the same pattern for non-critical UI state changes.
- **`eslint-disable-next-line react-hooks/exhaustive-deps`** — used intentionally in dashboard for controlled initial-load vs. filter-change fetch separation. Don't "fix" these without understanding the dual-effect pattern.
- **API types live in `types.ts`, not component files.** Component prop interfaces stay in their component files. API response shapes go in `lib/types.ts`.
- **Don't import from Tremor directly in pages.** Use the chart wrappers in `components/charts/` which apply the project's color palette and font.
- **`NEXT_PUBLIC_` prefix required** for env vars accessed client-side. `API_BASE` reads `NEXT_PUBLIC_API_URL`.
- **Vercel rewrites handle CORS.** In production, `/api/*` is rewritten to the backend via `vercel.json`. Don't add CORS headers or proxy middleware in Next.js.
- **No Server Components yet.** All pages are `"use client"`. Don't convert to RSC without a migration plan — the `api` client uses browser `fetch` and `useState`.
