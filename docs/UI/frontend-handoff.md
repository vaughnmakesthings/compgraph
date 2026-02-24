# CompGraph — Design System Handoff

## What is this?

CompGraph is a **B2B competitive intelligence platform** for the field marketing industry. It scrapes job postings from competing agencies, enriches them with LLM entity extraction, and surfaces hiring patterns, client relationships, pay benchmarking, and market positioning insights.

This handoff contains a complete, implementation-ready design system. Your job is to build the frontend.

---

## Files in this package

| File | Purpose | When to reference |
|---|---|---|
| `frontend-handoff.md` | **You are here.** Architecture, dependencies, implementation order. | Read first, always. |
| `design-tokens.md` | Every color, font, spacing, and component token with copy-paste CSS. | When writing `globals.css`, theming, or any component styling. |
| `design-system.html` | Interactive visual reference. Open in a browser to see every component. | When you need to see what something should look like. Dark/light toggle, click sidebar items to see 3-tier nav. |

---

## Stack

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 16.x |
| Styling | Tailwind CSS (inline `@theme`, no config file) | v4 |
| Components | shadcn/ui | Latest |
| Data viz | Tremor | Latest (BarList, DonutChart, AreaChart, BarChart, Table) |
| Prose | @tailwindcss/typography | Latest |
| Icons | Heroicons (outline variant only) | `@heroicons/react/24/outline` |
| Fonts | Google Fonts: Sora, DM Sans, JetBrains Mono | — |
| Database | Supabase (Postgres + Auth + Edge Functions) | — |
| Deployment | Vercel | — |

---

## Project Setup

```bash
npx create-next-app@latest compgraph --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd compgraph

# Core dependencies
npm install @supabase/supabase-js @supabase/ssr
npm install @tremor/react
npm install @heroicons/react
npm install @tailwindcss/typography
npm install next-themes  # for dark mode toggle

# shadcn/ui init
npx shadcn@latest init
# When prompted: style=default, base-color=slate (we override everything), css-variables=yes

# Install shadcn components as needed
npx shadcn@latest add button badge card table input dialog dropdown-menu alert tabs tooltip
```

### Font Loading

In `app/layout.tsx`:
```tsx
import { DM_Sans, Sora, JetBrains_Mono } from 'next/font/google'

const dmSans = DM_Sans({ subsets: ['latin'], variable: '--font-sans' })
const sora = Sora({ subsets: ['latin'], variable: '--font-display' })
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' })

// Apply to <body>:
<body className={`${dmSans.variable} ${sora.variable} ${jetbrains.variable} font-sans`}>
```

---

## File Structure

```
src/
├── app/
│   ├── globals.css              ← Token system lives here (see design-tokens.md §7)
│   ├── layout.tsx               ← Font loading, ThemeProvider, sidebar shell
│   ├── page.tsx                 ← Dashboard (redirect or default view)
│   ├── dashboard/
│   │   └── page.tsx
│   ├── competitors/
│   │   ├── page.tsx             ← All competitors grid/list
│   │   └── [slug]/
│   │       └── page.tsx         ← Individual competitor dossier
│   ├── hiring/
│   │   ├── feed/page.tsx        ← Job posting feed
│   │   ├── benchmarking/page.tsx
│   │   └── archetypes/page.tsx
│   ├── market/page.tsx          ← Market overview
│   ├── scrape-history/page.tsx
│   └── settings/page.tsx
├── components/
│   ├── ui/                      ← shadcn/ui components (auto-generated)
│   ├── layout/
│   │   ├── sidebar.tsx          ← 3-tier collapsible nav (see design-system.html)
│   │   ├── sidebar-nav.tsx      ← Nav item components
│   │   └── topbar.tsx           ← Breadcrumb + search + theme toggle
│   ├── data/
│   │   ├── kpi-card.tsx         ← KPI card with icon, value, delta
│   │   ├── competitor-table.tsx
│   │   ├── bar-list-card.tsx    ← Tremor BarList wrapper
│   │   ├── donut-card.tsx       ← Tremor DonutChart wrapper
│   │   ├── area-chart-card.tsx
│   │   ├── grouped-bar-card.tsx
│   │   └── spark-table.tsx      ← Table with inline sparklines
│   ├── content/
│   │   ├── callout.tsx          ← Finding / Positive / Risk / Caution variants
│   │   └── dossier-layout.tsx   ← Full competitor dossier composition
│   └── theme-provider.tsx       ← next-themes wrapper
├── lib/
│   ├── supabase/
│   │   ├── client.ts
│   │   ├── server.ts
│   │   └── middleware.ts
│   └── utils.ts                 ← cn() helper, formatters
└── types/
    ├── competitor.ts
    ├── job-posting.ts
    └── insight.ts
```

---

## Implementation Order

Build in this sequence. Each phase should be fully working before moving on.

### Phase 1: Shell & Tokens
1. Set up `globals.css` with the full token system from `design-tokens.md` §7
2. Override all shadcn/ui default colors per `design-tokens.md` §8
3. Build `layout.tsx` with font loading and `ThemeProvider`
4. Build the sidebar shell with 3-tier collapsible nav
5. Build the topbar with breadcrumbs and dark/light toggle
6. Verify: light mode, dark mode, sidebar expand/collapse all work

### Phase 2: Core Components
1. Build `kpi-card.tsx` — icon (Heroicon), label, mono value, delta with color
2. Build `callout.tsx` — four variants (finding, positive, risk, caution)
3. Build Tremor data wrappers: `bar-list-card`, `donut-card`, `area-chart-card`, `grouped-bar-card`
4. Build `spark-table.tsx` — table with inline Tremor SparkAreaChart
5. Verify: all components render correctly in both themes

### Phase 3: Page Layouts
1. Dashboard — KPI row + BarList + DonutChart
2. Competitor dossier — full mixed layout (KPI row → callout → prose → BarList → callouts → table) as shown in `design-system.html` "Full Dossier Composition"
3. Job feed — filterable table with badges
4. Market overview — area charts + grouped bar charts

### Phase 4: Data Layer
1. Supabase schema for competitors, job_postings, scrape_runs, insights
2. Server components fetching real data
3. Edge functions for scrape orchestration
4. LLM enrichment pipeline integration

---

## Critical Design Rules

These are non-negotiable. Refer to `design-tokens.md` §11 for the full anti-pattern list.

1. **Only 7 source colors exist.** Everything derives from them. Never introduce new hues.
2. **No Tailwind default grays.** Delete `slate`, `gray`, `zinc`, `neutral` from your vocabulary. Use `--muted`, `--muted-foreground`, `--border` only.
3. **No purple/indigo/violet.** Not in the palette. Period.
4. **Heroicons outline only.** No solid fill, no other icon libraries, no emoji.
5. **JetBrains Mono for all numbers.** Costs, counts, dates, percentages — always mono with `tabular-nums`.
6. **Sora for headings only.** Page titles, section headers, card titles. Never for body text.
7. **DM Sans for everything else.** Body, labels, nav, table cells.
8. **Minimum 11px.** Only chart axis annotations can be 11px. All reading text 12px+. Body text 14px.
9. **Sidebar is always dark.** `#2D3142` regardless of theme. Does not respond to light/dark toggle.
10. **Chart colors are for data differentiation only.** Never use chart palette colors semantically. Use `--success`, `--warning`, `--error` tokens for status.
11. **No glassmorphism, no gradients, no `transition-all`.** Solid backgrounds, specific transition properties.
12. **Focus rings use coral** (`--ring: #EF8354`) with 20% opacity shadow.

---

## Sidebar Navigation Data Model

The sidebar is data-driven. Competitors and tiers come from the database.

```typescript
interface SidebarNav {
  topLevel: NavItem[]          // Dashboard, Market Overview
  sections: NavSection[]       // "Intelligence", "System"
}

interface NavSection {
  label: string                // "INTELLIGENCE"
  items: NavItem[]
}

interface NavItem {
  label: string                // "Competitors"
  icon: string                 // Heroicon component name
  href?: string                // Direct link (leaf items)
  children?: NavGroup[]        // Tier groups (collapsible)
}

interface NavGroup {
  label: string                // "Tier 1 — Direct"
  count: number                // Number of entities
  entities: NavEntity[]
}

interface NavEntity {
  label: string                // "BDS Connected Solutions"
  href: string                 // /competitors/bds-connected-solutions
  count?: number               // Posting count
  color: string                // Chart palette color for dot
}
```

---

## Tremor Component Mapping

Reference `design-system.html` for exact visual appearance. Override Tremor's default colors with CompGraph tokens.

| Composition | Tremor Component | Usage |
|---|---|---|
| Hiring volume | `BarList` | Horizontal bars, chart palette colors, competitor names |
| Client distribution | `DonutChart` | Center metric, custom legend beside it |
| Hiring trends | `AreaChart` | Multi-series, 8% opacity fills, time axis |
| Pay benchmarking | `Table` + `SparkAreaChart` | Inline sparklines in table cells |
| Role distribution | `BarChart` | Grouped bars, 4 series per group |

Override Tremor defaults:
```tsx
const chartColors = {
  coral: '#EF8354',
  teal: '#1B998B',
  slate: '#4F5D75',
  gold: '#DCB256',
  chestnut: '#8C2C23',
}
```

---

## KPI Card Pattern

Every KPI card follows this exact structure:

```
┌─────────────────────────┐
│ [Icon]                  │  ← 32×32 muted bg, Heroicon inside
│ LABEL                   │  ← 12px DM Sans uppercase tracking-wider muted
│ $247,000                │  ← 28px JetBrains Mono semibold
│ ↑ 12.4% vs last quarter │  ← 12px JetBrains Mono, teal/chestnut/gold
└─────────────────────────┘
```

Delta colors: `--success` for up, `--error` for down, `--warning` for flat/stale.

---

## Dossier Page Pattern (Most Complex Layout)

The competitor dossier is the primary content view. Structure from top to bottom:

1. **Header** — Competitor name (Sora 22px), subtitle, badges (Active/Inactive), "Updated X ago"
2. **KPI Row** — 4× KPI cards in a grid
3. **Callout (Finding)** — Top-line LLM-generated insight
4. **Prose Section** — `@tailwindcss/typography` styled narrative
5. **BarList Card** — Hiring by role type
6. **Callout (Positive)** — Growth signal
7. **Callout (Caution)** — Data freshness warning
8. **Table** — Detailed job postings with sort, filter, pagination

See the "Full Dossier Composition" section in `design-system.html` for the exact visual.

---

## Dark Mode Implementation

Use `next-themes` with class strategy:

```tsx
// theme-provider.tsx
import { ThemeProvider } from 'next-themes'

export function CompGraphThemeProvider({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      {children}
    </ThemeProvider>
  )
}
```

Default to dark mode. All token switching happens via CSS variables — no conditional Tailwind classes needed for colors. The sidebar ignores the theme entirely.

---

## What "Done" Looks Like

Open `design-system.html` in a browser side-by-side with the running app. They should be visually indistinguishable for every component, in both light and dark mode. The HTML reference is the source of truth for all visual decisions.
