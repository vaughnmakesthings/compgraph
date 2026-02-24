# CompGraph Design Token Specification

## For: Claude Code Frontend Agent
## Stack: Next.js 16 App Router · Tailwind CSS v4 (inline @theme) · shadcn/ui · Tremor-inspired data viz · @tailwindcss/typography

---

## 1. Source Palette (7 Hand-Picked Colors)

These are the **only** brand colors. Everything else is derived.

| Token Name | Hex | Role |
|---|---|---|
| `jet-black` | `#2D3142` | Dark base, sidebar, dark mode surfaces |
| `coral-glow` | `#EF8354` | Primary accent, CTAs, active/selected states |
| `blue-slate` | `#4F5D75` | Secondary text, muted UI, labels |
| `silver` | `#BFC0C0` | Borders, dividers, subtle separators |
| `teal-jade` | `#1B998B` | Success, positive signals, growth indicators |
| `chestnut` | `#8C2C23` | Error, danger, destructive actions, decline indicators |
| `warm-gold` | `#DCB256` | Warning, caution, stale data, low confidence |

---

## 2. Derived Neutrals

Generate these from `jet-black` (#2D3142) by adjusting lightness. Do NOT use Tailwind gray/slate/zinc defaults.

### Light Mode Neutrals
| Token | Value | Usage |
|---|---|---|
| `--background` | `#F4F4F0` | Page background (warm off-white, slight warm cast) |
| `--surface` | `#FFFFFF` | Card/panel backgrounds |
| `--surface-raised` | `#FAFAF7` | Hover states on cards, elevated surfaces |
| `--foreground` | `#2D3142` | Primary body text (jet-black itself) |
| `--muted` | `#E8E8E3` | Muted backgrounds, empty states, skeleton fills |
| `--muted-foreground` | `#4F5D75` | Secondary text (blue-slate) |

### Dark Mode Neutrals
| Token | Value | Usage |
|---|---|---|
| `--background` | `#1A1B26` | Page background (derived from jet-black, deeper) |
| `--surface` | `#2D3142` | Card/panel backgrounds (jet-black itself) |
| `--surface-raised` | `#363B4D` | Hover states on cards, elevated surfaces |
| `--foreground` | `#E8E8E3` | Primary body text |
| `--muted` | `#363B4D` | Muted backgrounds |
| `--muted-foreground` | `#9CA3B4` | Secondary text (lightened blue-slate) |

---

## 3. Semantic Token Map

### Light Mode
```
--primary:            #EF8354   /* coral-glow */
--primary-foreground: #FFFFFF
--secondary:          #4F5D75   /* blue-slate */
--secondary-foreground: #FFFFFF
--accent:             #EF8354   /* coral-glow at 10% opacity for accent backgrounds */
--accent-foreground:  #2D3142
--border:             #BFC0C0   /* silver */
--input:              #BFC0C0
--ring:               #EF8354   /* focus rings use coral */

/* Semantic states */
--success:            #1B998B   /* teal-jade */
--success-foreground: #FFFFFF
--success-muted:      #1B998B1A /* 10% opacity for bg fills */
--warning:            #DCB256   /* warm-gold */
--warning-foreground: #2D3142   /* dark text on gold */
--warning-muted:      #DCB2561A
--error:              #8C2C23   /* chestnut */
--error-foreground:   #FFFFFF
--error-muted:        #8C2C231A
```

### Dark Mode
```
--primary:            #EF8354   /* coral stays consistent */
--primary-foreground: #1A1B26
--secondary:          #9CA3B4   /* lightened blue-slate */
--secondary-foreground: #1A1B26
--accent:             #EF83541A
--accent-foreground:  #E8E8E3
--border:             #4F5D75   /* blue-slate as border in dark */
--input:              #4F5D75
--ring:               #EF8354

/* Semantic states — brighter in dark mode for contrast */
--success:            #22C4A8   /* brightened teal */
--success-foreground: #1A1B26
--success-muted:      #22C4A81A
--warning:            #E8C76A   /* brightened gold */
--warning-foreground: #1A1B26
--warning-muted:      #E8C76A1A
--error:              #D4453A   /* brightened chestnut */
--error-foreground:   #FFFFFF
--error-muted:        #D4453A1A
```

---

## 4. Sidebar (Invariant — Always Dark)

The sidebar does NOT respond to light/dark theme toggle. It uses a 3-tier collapsible nav pattern.

```
--sidebar-bg:              #2D3142   /* jet-black */
--sidebar-bg-active:       #363B4D   /* raised surface */
--sidebar-text:            #D0D1D1   /* bright enough to read easily */
--sidebar-text-muted:      #B0B1B5   /* sub-items, tier labels */
--sidebar-text-active:     #FFFFFF
--sidebar-accent:          #EF8354   /* coral for active indicator + active leaf text */
--sidebar-border:          #4F5D75   /* blue-slate */
--sidebar-section-label:   rgba(191, 192, 192, 0.5)  /* uppercase section headers */
```

Width: 280px expanded, 64px collapsed. Persist state via localStorage.

### 3-Tier Nav Hierarchy

| Level | Class | Font | Size | Indent | Example |
|---|---|---|---|---|---|
| Parent | `sidebar-item` | DM Sans | 14px | 20px left | Competitors |
| Tier group | `sidebar-sub-item` | DM Sans | 13px | 52px left | Tier 1 — Direct |
| Leaf entity | `sidebar-leaf` | DM Sans | 13px | 68px left | BDS Connected Solutions |

- Parents have 18×18 Heroicon + chevron that rotates 90° on open
- Tier groups show a count badge + mini chevron
- Leaf entities show a colored dot (chart palette colors) + posting count
- Active leaf: coral text + coral dot with glow shadow
- Active parent: coral left border indicator (3px)

---

## 5. Chart & Data Visualization Palette

Five colors for charts, ordered for maximum visual differentiation:

```
--chart-1: #EF8354  /* coral-glow — primary series */
--chart-2: #1B998B  /* teal-jade — secondary series */
--chart-3: #4F5D75  /* blue-slate — tertiary */
--chart-4: #DCB256  /* warm-gold — quaternary */
--chart-5: #8C2C23  /* chestnut — quinary */
```

For comparative charts (competitor vs competitor), use `chart-1` through `chart-5` in sequence. Never assign chart colors semantically (don't use teal=good, red=bad in charts — that's what the status tokens are for).

---

## 6. Typography

Geometric/technical personality. Three intentional font families:

| Role | Font | Usage |
|---|---|---|
| Body | DM Sans | All body text, UI labels, table cells (--font-sans) |
| Display | Sora | Section headings, page titles (.font-display) |
| Mono | JetBrains Mono | Data values, metrics, costs, durations (.font-mono) |

Scale:
- Table headers: `text-[12px]` uppercase, `tracking-wider`, `text-muted-foreground/50`
- Body data: `text-sm` (14px)
- Subtext/labels: `text-[13px]`
- KPI values: `text-[28px] font-semibold tracking-tight`
- All numeric data: `tabular-nums`
- Minimum font size: 11px (annotations only). All reading text 12px+.

---

## 7. Tailwind CSS v4 Implementation

Place this in your root CSS file (e.g., `app/globals.css`). Tailwind v4 uses `@theme` inline — no `tailwind.config.ts` file.

```css
@import "tailwindcss";
@import "@tailwindcss/typography";

@theme {
  /* Fonts */
  --font-sans: 'DM Sans', sans-serif;
  --font-display: 'Sora', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Border radius scale */
  --radius-sm: 0.375rem;
  --radius-md: 0.4375rem;
  --radius-lg: 0.625rem;
  --radius-xl: 0.875rem;
  --radius-2xl: 1.125rem;

  /* Chart colors */
  --color-chart-1: #EF8354;
  --color-chart-2: #1B998B;
  --color-chart-3: #4F5D75;
  --color-chart-4: #DCB256;
  --color-chart-5: #8C2C23;
}

/* ─── Light Mode (default) ─── */
:root {
  --background: #F4F4F0;
  --surface: #FFFFFF;
  --surface-raised: #FAFAF7;
  --foreground: #2D3142;
  --muted: #E8E8E3;
  --muted-foreground: #4F5D75;

  --primary: #EF8354;
  --primary-foreground: #FFFFFF;
  --secondary: #4F5D75;
  --secondary-foreground: #FFFFFF;
  --accent: rgba(239, 131, 84, 0.10);
  --accent-foreground: #2D3142;
  --border: #BFC0C0;
  --input: #BFC0C0;
  --ring: #EF8354;

  --success: #1B998B;
  --success-foreground: #FFFFFF;
  --success-muted: rgba(27, 153, 139, 0.10);
  --warning: #DCB256;
  --warning-foreground: #2D3142;
  --warning-muted: rgba(220, 178, 86, 0.10);
  --error: #8C2C23;
  --error-foreground: #FFFFFF;
  --error-muted: rgba(140, 44, 35, 0.10);

  /* Sidebar — invariant */
  --sidebar-bg: #2D3142;
  --sidebar-bg-active: #363B4D;
  --sidebar-text: #D0D1D1;
  --sidebar-text-muted: #B0B1B5;
  --sidebar-text-active: #FFFFFF;
  --sidebar-accent: #EF8354;
  --sidebar-border: #4F5D75;
}

/* ─── Dark Mode ─── */
.dark {
  --background: #1A1B26;
  --surface: #2D3142;
  --surface-raised: #363B4D;
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

  --success: #22C4A8;
  --success-foreground: #1A1B26;
  --success-muted: rgba(34, 196, 168, 0.10);
  --warning: #E8C76A;
  --warning-foreground: #1A1B26;
  --warning-muted: rgba(232, 199, 106, 0.10);
  --error: #D4453A;
  --error-foreground: #FFFFFF;
  --error-muted: rgba(212, 69, 58, 0.10);

  /* Sidebar tokens don't change — already dark */
}

/* ─── Body transitions ─── */
body {
  background-color: var(--background);
  color: var(--foreground);
  transition: background-color 150ms ease-in-out, color 150ms ease-in-out;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

---

## 8. shadcn/ui Component Token Mapping

When installing shadcn/ui components, map to these tokens:

| shadcn token | CompGraph value |
|---|---|
| `--background` | `var(--background)` |
| `--foreground` | `var(--foreground)` |
| `--card` | `var(--surface)` |
| `--card-foreground` | `var(--foreground)` |
| `--popover` | `var(--surface)` |
| `--popover-foreground` | `var(--foreground)` |
| `--primary` | `var(--primary)` |
| `--primary-foreground` | `var(--primary-foreground)` |
| `--secondary` | `var(--secondary)` |
| `--secondary-foreground` | `var(--secondary-foreground)` |
| `--muted` | `var(--muted)` |
| `--muted-foreground` | `var(--muted-foreground)` |
| `--accent` | `var(--accent)` |
| `--accent-foreground` | `var(--accent-foreground)` |
| `--destructive` | `var(--error)` |
| `--destructive-foreground` | `var(--error-foreground)` |
| `--border` | `var(--border)` |
| `--input` | `var(--input)` |
| `--ring` | `var(--ring)` |

---

## 9. Content Layer (Prose + Callouts)

### @tailwindcss/typography customization

Override the default `prose` classes to use CompGraph tokens:

```css
.prose {
  --tw-prose-body: var(--foreground);
  --tw-prose-headings: var(--foreground);
  --tw-prose-lead: var(--muted-foreground);
  --tw-prose-links: var(--primary);
  --tw-prose-bold: var(--foreground);
  --tw-prose-counters: var(--muted-foreground);
  --tw-prose-bullets: var(--muted-foreground);
  --tw-prose-hr: var(--border);
  --tw-prose-quotes: var(--foreground);
  --tw-prose-quote-borders: var(--primary);
  --tw-prose-captions: var(--muted-foreground);
  --tw-prose-code: var(--foreground);
  --tw-prose-pre-code: var(--foreground);
  --tw-prose-pre-bg: var(--muted);
  --tw-prose-th-borders: var(--border);
  --tw-prose-td-borders: var(--border);
}

/* Dark mode prose inherits automatically via CSS vars */
```

Use `prose` on all LLM-generated insight text, competitor summaries, and narrative content blocks.

### Callout Components

Build these three callout variants using shadcn Alert as the base:

```
/* Finding — key intelligence insight */
.callout-finding {
  border-left: 3px solid var(--primary);    /* coral */
  background: var(--accent);                /* coral at 10% */
}

/* Positive signal — growth, expansion, new client */
.callout-positive {
  border-left: 3px solid var(--success);    /* teal */
  background: var(--success-muted);
}

/* Risk/decline signal */
.callout-risk {
  border-left: 3px solid var(--error);      /* chestnut */
  background: var(--error-muted);
}

/* Low confidence / stale data */
.callout-caution {
  border-left: 3px solid var(--warning);    /* warm gold */
  background: var(--warning-muted);
}
```

---

## 10. Component Patterns Quick Reference

| Component | Background | Border | Hover | Radius |
|---|---|---|---|---|
| Card | `var(--surface)` | `var(--border)` | `border-opacity-80` | `--radius-lg` |
| Table row | transparent | none | `var(--muted)` at 30% | none |
| Input | `var(--surface)` | `var(--input)` | `var(--ring)` focus | `--radius-sm` |
| Button (primary) | `var(--primary)` | none | darken 10% | `--radius-md` |
| Button (secondary) | `var(--surface)` | `var(--border)` | `var(--surface-raised)` | `--radius-md` |
| Badge (success) | `var(--success-muted)` | none | n/a | `--radius-sm` |
| Badge (warning) | `var(--warning-muted)` | none | n/a | `--radius-sm` |
| Badge (error) | `var(--error-muted)` | none | n/a | `--radius-sm` |
| Sidebar | `var(--sidebar-bg)` | `var(--sidebar-border)` | `var(--sidebar-bg-active)` | n/a |

---

## 11. Anti-Patterns (Enforce These)

- ❌ No purple/indigo/violet anywhere — it's gone from this palette entirely
- ❌ No gradient hero sections
- ❌ No glassmorphism (backdrop-blur + transparency) on cards
- ❌ No `transition-all` — specify exact properties
- ❌ No uniform `rounded-xl` — use the radius scale above
- ❌ No Tailwind default gray/slate/zinc — use derived neutrals only
- ❌ No decorative icons — every icon (Heroicons) must communicate meaning. Never use emoji.
- ❌ No "AI-powered" badges or sparkle icons
- ❌ Do not use chart colors for semantic meaning (success/error) — use status tokens
- ❌ Do not accept default shadcn/ui colors — always override with this token system

---

## 12. Noise Texture (Optional Enhancement)

Subtle SVG fractal noise overlay on content areas:

```css
.noise-overlay::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}

.dark .noise-overlay::before {
  opacity: 0.04;
}
```

---

## Summary

Seven source colors → full token system with light/dark modes, semantic states, chart palette, sidebar, typography, prose layer, and callout components. No Tailwind defaults survive. Hand this file to the frontend agent as the single source of truth for all visual decisions.
