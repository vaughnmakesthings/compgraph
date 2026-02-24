# Eval Dashboard Brand Rebrand Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the eval dashboard's current color scheme (indigo/yellow primary, Satoshi/Rethink Sans fonts) with the CompGraph brand system (coral/jet-black primary, Sora/DM Sans/JetBrains Mono fonts), updating all design tokens, components, and hardcoded colors.

**Architecture:** The eval dashboard (`compgraph-eval/web/`) is a Next.js 16 + Tailwind v4 + shadcn/ui app. All theming flows through CSS custom properties in `globals.css` → `@theme inline` block → Tailwind utility classes. The rebrand touches: (1) design tokens in globals.css, (2) font loading in layout.tsx + package.json, (3) chart utility colors in chart-utils.ts, (4) hardcoded Tailwind color classes in components (badge, bar-list, status-badge, sidebar). No structural/layout changes needed — the shell, pages, and component hierarchy stay identical.

**Tech Stack:** Next.js 16, Tailwind CSS v4, shadcn/ui, Recharts 3, @fontsource-variable for fonts

**Source of truth:** `/Users/vmud/Documents/dev/projects/compgraph/docs/UI/compgraph-theme.css` and `/Users/vmud/Documents/dev/projects/compgraph/docs/UI/design-tokens.md`

---

## Current → Target Delta Summary

| Token | Current | Target |
|-------|---------|--------|
| `--primary` (light) | `#110088` (deep indigo) | `#EF8354` (coral-glow) |
| `--primary` (dark) | `#FCED39` (yellow) | `#EF8354` (coral) |
| `--brand-accent` | `#FCED39` (yellow) | remove; use `--primary` |
| `--background` (light) | `#FAFAF5` (warm off-white) | `#F4F4F0` (warm off-white) |
| `--foreground` (light) | `#111100` (near-black olive) | `#2D3142` (jet-black) |
| `--sidebar` | `#110055` (deep indigo) | `#2D3142` (jet-black) |
| `--ring` | `#110088` / `#FCED39` | `#EF8354` (coral) |
| Font: display | Rethink Sans | Sora |
| Font: body | Satoshi (Fontshare) | DM Sans |
| Font: mono | Berkeley Mono / JetBrains Mono | JetBrains Mono |
| Chart colors | indigo/emerald/yellow/blue/red | coral/teal/blue-slate/gold/chestnut |
| Status tokens | `--status-correct/wrong/improved` | `--success/warning/error` (semantic) |

---

### Task 1: Replace globals.css design tokens

**Files:**
- Modify: `compgraph-eval/web/src/app/globals.css`

**Step 1: Replace the entire globals.css with CompGraph brand tokens**

Replace the full file content with:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-surface: var(--surface);
  --color-surface-raised: var(--surface-raised);
  --color-surface-content: var(--surface-content);
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-success-muted: var(--success-muted);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-warning-muted: var(--warning-muted);
  --color-error: var(--error);
  --color-error-foreground: var(--error-foreground);
  --color-error-muted: var(--error-muted);
  --color-status-correct: var(--status-correct);
  --color-status-wrong: var(--status-wrong);
  --color-status-improved: var(--status-improved);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --radius-2xl: calc(var(--radius) + 8px);
  --font-sans: 'DM Sans Variable', 'DM Sans', system-ui, sans-serif;
  --font-display: 'Sora Variable', 'Sora', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono Variable', 'JetBrains Mono', ui-monospace, monospace;
}

:root {
  --radius: 0.5rem;

  /* Surface neutrals (CompGraph brand) */
  --background: #F4F4F0;
  --surface: #FFFFFF;
  --surface-raised: #FAFAF7;
  --surface-content: #EDEDEA;
  --foreground: #2D3142;
  --muted: #E8E8E3;
  --muted-foreground: #4F5D75;

  /* Primary / Secondary / Accent */
  --primary: #EF8354;
  --primary-foreground: #FFFFFF;
  --secondary: #4F5D75;
  --secondary-foreground: #FFFFFF;
  --accent: rgba(239, 131, 84, 0.10);
  --accent-foreground: #2D3142;
  --border: #BFC0C0;
  --input: #BFC0C0;
  --ring: #EF8354;

  /* Card / Popover (map to surface) */
  --card: var(--surface);
  --card-foreground: var(--foreground);
  --popover: var(--surface);
  --popover-foreground: var(--foreground);

  /* Destructive */
  --destructive: #8C2C23;

  /* Semantic states */
  --success: #1B998B;
  --success-foreground: #FFFFFF;
  --success-muted: rgba(27, 153, 139, 0.10);
  --warning: #DCB256;
  --warning-foreground: #2D3142;
  --warning-muted: rgba(220, 178, 86, 0.10);
  --error: #8C2C23;
  --error-foreground: #FFFFFF;
  --error-muted: rgba(140, 44, 35, 0.10);

  /* Status tokens (eval-specific — map to semantic) */
  --status-correct: #1B998B;
  --status-wrong: #8C2C23;
  --status-improved: #EF8354;

  /* Charts — brand palette in order */
  --chart-1: #EF8354;
  --chart-2: #1B998B;
  --chart-3: #4F5D75;
  --chart-4: #DCB256;
  --chart-5: #8C2C23;

  /* Sidebar — always dark (jet-black base) */
  --sidebar: #2D3142;
  --sidebar-foreground: #D0D1D1;
  --sidebar-primary: #EF8354;
  --sidebar-primary-foreground: #FFFFFF;
  --sidebar-accent: #363B4D;
  --sidebar-accent-foreground: #FFFFFF;
  --sidebar-border: #4F5D75;
  --sidebar-ring: #EF8354;
}

.dark {
  --background: #1A1B26;
  --surface: #2D3142;
  --surface-raised: #363B4D;
  --surface-content: #22233A;
  --foreground: #E8E8E3;
  --muted: #363B4D;
  --muted-foreground: #9CA3B4;

  --primary: #EF8354;
  --primary-foreground: #1A1B26;
  --secondary: #9CA3B4;
  --secondary-foreground: #1A1B26;
  --accent: rgba(239, 131, 84, 0.10);
  --accent-foreground: #E8E8E3;
  --border: #4F5D75;
  --input: #4F5D75;
  --ring: #EF8354;

  --card: var(--surface);
  --card-foreground: var(--foreground);
  --popover: var(--surface);
  --popover-foreground: var(--foreground);

  --destructive: #D4453A;

  --success: #22C4A8;
  --success-foreground: #1A1B26;
  --success-muted: rgba(34, 196, 168, 0.10);
  --warning: #E8C76A;
  --warning-foreground: #1A1B26;
  --warning-muted: rgba(232, 199, 106, 0.10);
  --error: #D4453A;
  --error-foreground: #FFFFFF;
  --error-muted: rgba(212, 69, 58, 0.10);

  /* Status tokens — brighter for dark mode */
  --status-correct: #22C4A8;
  --status-wrong: #D4453A;
  --status-improved: #EF8354;

  /* Charts — same palette, coral stays visible on dark */
  --chart-1: #EF8354;
  --chart-2: #22C4A8;
  --chart-3: #9CA3B4;
  --chart-4: #E8C76A;
  --chart-5: #D4453A;

  /* Sidebar stays same as light — already dark */
  --sidebar: #2D3142;
  --sidebar-foreground: #D0D1D1;
  --sidebar-primary: #EF8354;
  --sidebar-primary-foreground: #FFFFFF;
  --sidebar-accent: #363B4D;
  --sidebar-accent-foreground: #FFFFFF;
  --sidebar-border: #363B4D;
  --sidebar-ring: #EF8354;
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    transition: background-color 150ms ease-in-out, color 150ms ease-in-out;
  }
}

/* Display font for headings */
.font-display {
  font-family: var(--font-display);
}

/* Monospace font for data/metrics */
.font-mono {
  font-family: var(--font-mono);
}

/* Noise texture overlay — subtle grain on content areas */
.noise-bg {
  position: relative;
}
.noise-bg::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  border-radius: inherit;
}
.dark .noise-bg::before {
  opacity: 0.04;
}
```

**Step 2: Verify the file saved correctly**

Run: `head -5 compgraph-eval/web/src/app/globals.css`
Expected: `@import "tailwindcss";` as line 1

**Step 3: Commit**

```bash
git add src/app/globals.css
git commit -m "feat: replace design tokens with CompGraph brand palette"
```

---

### Task 2: Swap font packages

**Files:**
- Modify: `compgraph-eval/web/package.json`
- Modify: `compgraph-eval/web/src/app/layout.tsx`

**Step 1: Install new font packages, remove old ones**

Run from `compgraph-eval/web/`:
```bash
npm install @fontsource-variable/sora @fontsource-variable/dm-sans
npm uninstall @fontsource-variable/rethink-sans
```

Note: `@fontsource-variable/jetbrains-mono` is already installed — keep it.

**Step 2: Update layout.tsx font imports and remove Fontshare link**

Replace the current `layout.tsx` content with:

```tsx
import type { Metadata } from "next";
import "@fontsource-variable/sora";
import "@fontsource-variable/dm-sans";
import "@fontsource-variable/jetbrains-mono";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "CompGraph Eval",
  description: "Evaluation dashboard for CompGraph enrichment prompts",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-lg"
        >
          Skip to main content
        </a>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
        >
          <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

Changes from current:
- `@fontsource-variable/rethink-sans` → `@fontsource-variable/sora`
- Added `@fontsource-variable/dm-sans` import
- Removed the `<head>` block with Fontshare Satoshi CDN link (DM Sans replaces Satoshi, loaded via @fontsource)

**Step 3: Run typecheck to verify**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 4: Commit**

```bash
git add package.json package-lock.json src/app/layout.tsx
git commit -m "feat: swap fonts to Sora + DM Sans + JetBrains Mono"
```

---

### Task 3: Update chart-utils.ts to use brand palette

**Files:**
- Modify: `compgraph-eval/web/src/lib/chart-utils.ts`

**Step 1: Replace chart color definitions with brand palette**

Replace the `chartColors` object and `focusRing` with:

```typescript
export type ColorUtility = "bg" | "stroke" | "fill" | "text"

export const chartColors = {
  coral: {
    bg: "bg-chart-1",
    stroke: "stroke-chart-1",
    fill: "fill-chart-1",
    text: "text-chart-1",
  },
  teal: {
    bg: "bg-chart-2",
    stroke: "stroke-chart-2",
    fill: "fill-chart-2",
    text: "text-chart-2",
  },
  slate: {
    bg: "bg-chart-3",
    stroke: "stroke-chart-3",
    fill: "fill-chart-3",
    text: "text-chart-3",
  },
  gold: {
    bg: "bg-chart-4",
    stroke: "stroke-chart-4",
    fill: "fill-chart-4",
    text: "text-chart-4",
  },
  chestnut: {
    bg: "bg-chart-5",
    stroke: "stroke-chart-5",
    fill: "fill-chart-5",
    text: "text-chart-5",
  },
} as const satisfies {
  [color: string]: {
    [key in ColorUtility]: string
  }
}

export type AvailableChartColorsKeys = keyof typeof chartColors

export const AvailableChartColors: AvailableChartColorsKeys[] = Object.keys(
  chartColors,
) as Array<AvailableChartColorsKeys>

export const constructCategoryColors = (
  categories: string[],
  colors: AvailableChartColorsKeys[],
): Map<string, AvailableChartColorsKeys> => {
  const categoryColors = new Map<string, AvailableChartColorsKeys>()
  categories.forEach((category, index) => {
    categoryColors.set(category, colors[index % colors.length])
  })
  return categoryColors
}

export const getColorClassName = (
  color: AvailableChartColorsKeys,
  type: ColorUtility,
): string => {
  const fallbackColor = {
    bg: "bg-muted",
    stroke: "stroke-muted",
    fill: "fill-muted",
    text: "text-muted-foreground",
  }
  return chartColors[color]?.[type] ?? fallbackColor[type]
}

export const getYAxisDomain = (
  autoMinValue: boolean,
  minValue: number | undefined,
  maxValue: number | undefined,
) => {
  const minDomain = autoMinValue ? "auto" : (minValue ?? 0)
  const maxDomain = maxValue ?? "auto"
  return [minDomain, maxDomain]
}

export const hasOnlyOneValueForKey = (
  array: Record<string, unknown>[],
  keyToCheck: string,
): boolean => {
  const val: unknown[] = []

  for (const obj of array) {
    if (Object.prototype.hasOwnProperty.call(obj, keyToCheck)) {
      val.push(obj[keyToCheck])
      if (val.length > 1) {
        return false
      }
    }
  }

  return true
}

export const focusRing = [
  "outline outline-offset-2 outline-0 focus-visible:outline-2",
  "outline-ring dark:outline-ring",
]
```

**Step 2: Verify types compile**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add src/lib/chart-utils.ts
git commit -m "feat: map chart colors to brand palette tokens"
```

---

### Task 4: Update badge.tsx to use semantic tokens

**Files:**
- Modify: `compgraph-eval/web/src/components/ui/badge.tsx`

**Step 1: Replace hardcoded Tailwind colors with semantic tokens**

Replace the `badgeVariants` definition:

```typescript
const badgeVariants = cva(
  "inline-flex items-center gap-x-1 whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      variant: {
        default: [
          "bg-accent text-accent-foreground ring-primary/20",
          "dark:bg-accent dark:text-accent-foreground dark:ring-primary/30",
        ],
        neutral: [
          "bg-muted text-muted-foreground ring-border/30",
          "dark:bg-muted dark:text-muted-foreground dark:ring-border/20",
        ],
        success: [
          "bg-success-muted text-success ring-success/30",
          "dark:bg-success-muted dark:text-success dark:ring-success/20",
        ],
        error: [
          "bg-error-muted text-error ring-error/20",
          "dark:bg-error-muted dark:text-error dark:ring-error/20",
        ],
        warning: [
          "bg-warning-muted text-warning-foreground ring-warning/30",
          "dark:bg-warning-muted dark:text-warning dark:ring-warning/20",
        ],
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)
```

**Step 2: Verify types compile**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add src/components/ui/badge.tsx
git commit -m "feat: badge uses semantic color tokens instead of Tailwind defaults"
```

---

### Task 5: Update bar-list.tsx to use brand tokens

**Files:**
- Modify: `compgraph-eval/web/src/components/ui/bar-list.tsx`

**Step 1: Replace hardcoded gray/blue classes with token references**

In `bar-list.tsx`, make these replacements:

1. Line 76: `"hover:bg-gray-50 dark:hover:bg-gray-900"` → `"hover:bg-muted/30 dark:hover:bg-muted/30"`
2. Line 84: `"bg-blue-200 dark:bg-blue-900"` → `"bg-primary/20 dark:bg-primary/20"`
3. Line 86: `"group-hover:bg-blue-300 dark:group-hover:bg-blue-800"` → `"group-hover:bg-primary/30 dark:group-hover:bg-primary/30"`
4. Lines 101, 113: `"text-gray-900 dark:text-gray-50"` → `"text-foreground"` (both occurrences)
5. Line 139: `"text-gray-900 dark:text-gray-50"` → `"text-foreground"`

**Step 2: Verify types compile**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add src/components/ui/bar-list.tsx
git commit -m "feat: bar-list uses token colors instead of hardcoded blue/gray"
```

---

### Task 6: Update sidebar.tsx logo accent color

**Files:**
- Modify: `compgraph-eval/web/src/components/sidebar.tsx`

**Step 1: Replace brand-accent references with primary token**

The sidebar currently uses `text-brand-accent` and `bg-brand-accent` for the active indicator and logo. The `--brand-accent` token is being removed. Replace:

1. Line 59: `"text-brand-accent"` → `"text-sidebar-primary"`
2. Line 67: `"bg-brand-accent"` → `"bg-sidebar-primary"`
3. Line 72: `"text-brand-accent"` → `"text-sidebar-primary"`
4. Line 129: `"bg-brand-accent"` → `"bg-sidebar-primary"`
5. Line 131: `"text-[#111100]"` → `"text-sidebar-primary-foreground"`

**Step 2: Verify types compile**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 3: Commit**

```bash
git add src/components/sidebar.tsx
git commit -m "feat: sidebar uses sidebar-primary token instead of brand-accent"
```

---

### Task 7: Run full test suite and build

**Files:** None (validation only)

**Step 1: Run linter**

Run: `cd compgraph-eval/web && npm run lint`
Expected: 0 warnings, 0 errors

**Step 2: Run type checker**

Run: `cd compgraph-eval/web && npm run typecheck`
Expected: No errors

**Step 3: Run tests**

Run: `cd compgraph-eval/web && npm test`
Expected: All tests pass

**Step 4: Run production build**

Run: `cd compgraph-eval/web && npm run build`
Expected: Build succeeds with no errors

**Step 5: Commit any test fixes if needed**

If tests fail due to snapshot changes or hardcoded color assertions, update them.

---

### Task 8: Visual verification in browser

**Files:** None

**Step 1: Start dev server**

Run: `cd compgraph-eval/web && npm run dev`

**Step 2: Verify light mode**

Open `http://localhost:3000` and check:
- Sidebar is jet-black (#2D3142), not deep indigo (#110055)
- Active sidebar item uses coral (#EF8354) indicator, not yellow (#FCED39)
- Logo pill is coral, not yellow
- Page background is warm off-white (#F4F4F0)
- KPI card icons sit on gray (#E8E8E3) background
- Headings use Sora font, body uses DM Sans
- Chart bars are coral (#EF8354), not indigo

**Step 3: Verify dark mode**

Toggle to dark mode and check:
- Background is deep blue-gray (#1A1B26), not olive-black (#0A0A00)
- Primary accent stays coral (not yellow flip)
- Sidebar doesn't change (already dark)
- Charts use brightened coral/teal palette

**Step 4: Stop dev server**

---

## Files Changed Summary

| File | Action | What Changes |
|------|--------|--------------|
| `src/app/globals.css` | Replace | All design tokens (colors, fonts, radius) |
| `src/app/layout.tsx` | Modify | Font imports, remove Fontshare CDN link |
| `package.json` | Modify | Add `@fontsource-variable/sora`, `@fontsource-variable/dm-sans`, remove `@fontsource-variable/rethink-sans` |
| `src/lib/chart-utils.ts` | Replace | Chart color definitions → brand palette tokens |
| `src/components/ui/badge.tsx` | Modify | Hardcoded blue/gray/emerald/red → semantic tokens |
| `src/components/ui/bar-list.tsx` | Modify | Hardcoded blue/gray → primary/foreground tokens |
| `src/components/sidebar.tsx` | Modify | `brand-accent` → `sidebar-primary` |
