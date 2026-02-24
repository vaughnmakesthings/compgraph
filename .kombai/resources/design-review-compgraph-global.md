# CompGraph — Global Design Review
**Date:** 2026-02-24  
**Scope:** All pages — UX/Usability + Consistency  
**Benchmark:** `docs/UI/compgraph-design-handoff/compgraph-handoff/design-system/reference.html`

---

## Executive Summary

The current implementation has drifted significantly from the design specification. The most critical gaps are in the **Sidebar** (missing logo, section labels, 3-tier hierarchy), the **Callout component** (wrong color for the `finding` variant — blue-slate instead of coral), and the absence of a **shared Button component**. Several components exist with the right API but their props are never exercised (KPI icon, trend delta). Two non-brand colors (`#3CA060`, `#D64045`) appear in the codebase, violating the 7-color constraint.

---

## Part 1 — UX / Usability Issues

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| U1 | Dashboard KPI grid renders **nothing** when API is unreachable — no fallback "—" values, no retained skeleton | 🔴 Critical | `app/page.tsx:183–211` |
| U2 | Error banner shows raw API path: `Network error: /api/pipeline/status` — exposes implementation detail | 🟠 High | `app/page.tsx:163–176`, `hiring/page.tsx:202–214`, `eval/runs/page.tsx:521–533` |
| U3 | Job Feed filter bar: Tremor `<Select>` grows full-width while native `<input>`/`<select>` stay narrow — 4 controls wrap inconsistently at any viewport | 🔴 Critical | `hiring/page.tsx:217–288` |
| U4 | Settings "Pipeline Controls" buttons have `width:100%; textAlign:'left'` — visually they look like nav list items, not actionable controls | 🟠 High | `settings/page.tsx:53–93` (`OutlineButton`) |
| U5 | Header "API connected" dot is hardcoded `bg-success` green — never reacts to actual fetch failures (confirmed: both API calls fail yet dot stays green) | 🟡 Medium | `header.tsx:22–33` |
| U6 | Competitor and prospect detail pages have no breadcrumb — user has no navigational anchor back to the list | 🟠 High | `competitors/[slug]/page.tsx` |
| U7 | Prospects page info box is static above-the-fold text, pushing prospect cards out of view on load | 🟡 Medium | `prospects/page.tsx:178–219` |
| U8 | All empty states are bare centered text with no icon or CTA (`No velocity data available`, `No postings match your filters`, etc.) | ⚪ Low | Dashboard, Market, Hiring, Eval pages |
| U9 | No logo or wordmark in the sidebar — no brand anchor on any page | 🟠 High | `sidebar.tsx:405–431` |
| U10 | Eval has 5 sub-pages in the sidebar but no in-content tab bar — feels disconnected from the navigation | 🟡 Medium | `app/eval/` |
| U11 | Header never reflects active page — always reads "CompGraph" regardless of route | 🟡 Medium | `header.tsx` |

---

## Part 2 — Consistency / Spec-Drift Issues

### 2a. Sidebar (`sidebar.tsx`)

| Gap | Reference Spec | Current |
|-----|---------------|---------|
| Logo | `[CG]` coral 32×32px mark (Sora 14px/700 white) + "CompGraph" Sora 17px/600 white, separated by `1px solid rgba(79,93,117,0.4)` | **Absent** — nav starts immediately with items; Next.js badge at bottom |
| Section labels | "INTELLIGENCE" and "SYSTEM" in DM Sans 12px uppercase, `rgba(191,192,192,0.5)`, padding `18px 20px 8px` | **Absent** — no section grouping |
| Chevron icon | `ChevronRightIcon` — right-facing, rotates 90° when open | `ChevronDownIcon` — down-facing, rotates to point up |
| Tier 1 category groups | `Tier 1 — Direct  5 ›` — indent 52px, DM Sans 13px, count in JM Mono 11px rgba count | Styled as `text-xs font-semibold uppercase tracking-wider` at `pl-9` (36px) — wrong size, wrong indent |
| "BY TIER" sub-label | Uppercase 12px, rgba(191,192,192,0.4), padding `12px 20px 6px 52px` | **Absent** |
| Tier 2 leaf indent | 68px left padding | `pl-9` = 36px — **32px too shallow** |
| Leaf dot size | 7×7px circle | 6×6px (`h-1.5 w-1.5`) |
| "View All Competitors" link | Present at bottom of Competitors submenu | **Absent** |

### 2b. Header (`header.tsx`)

| Gap | Reference Spec | Current |
|-----|---------------|---------|
| Left content | Breadcrumb: `Dashboard › Pipeline Health`, DM Sans 13px muted | Static `<span>CompGraph</span>` Sora 18px/600 |
| API status dot | Reacts to live fetch state | Hardcoded `var(--color-success)` — never updates |

### 2c. KPI Cards (`kpi-card.tsx` + call sites)

| Gap | Reference Spec | Current |
|-----|---------------|---------|
| Icon | Heroicons outline in 32×32 muted-fg square container, always shown | Prop exists but **never passed** in `page.tsx` or `competitors/[slug]/page.tsx` → icon is always absent |
| Label font size | 10px uppercase | 12px (`fontSize: "12px"` hardcoded in component) |
| Value font size | 24px semibold JM Mono | 28px — 4px over spec |
| Delta/trend row | `▲/▼/—` in JM Mono 10px with teal/chestnut/gold semantic color | Prop exists but **never passed** → trend row never renders |

### 2d. Callout Component (`callout.tsx`)

| Variant | Property | Reference | Current |
|---------|----------|-----------|---------|
| `finding` | Border color | `#EF8354` coral | `#4F5D75` **blue-slate** ← wrong |
| `finding` | Background | `rgba(239,131,84,0.10)` | `#4F5D750D` (blue-slate 5%) ← wrong |
| `finding` | Title color | `#EF8354` coral | `#4F5D75` ← wrong |
| `caution` | Title color | `#DCB256` warm gold | `#A07D28` darkened gold ← off-palette |
| All | Border width | **3px** | **4px** ← 1px over spec |
| All | Background opacity | 10% | ~5% (`0D` hex) ← too faint |

### 2e. Badge Component (`badge.tsx`)

| Gap | Reference Spec | Current |
|-----|---------------|---------|
| Border | **None** — `10% bg + full color text` only | `1px solid ${border}` on every variant |
| `warning` text color | `#DCB256` full warm gold | `#A07D28` darkened ← off-palette |
| `info` variant | Not in spec (4 semantic variants only) | Extra `info` variant with blue-slate exists |

### 2f. Data Table Headers

| Gap | Reference Spec | Current |
|-----|---------------|---------|
| Text case | Uppercase | Hiring table: title-case (`"Title"`, `"Company"`) ← wrong |
| Header text color | `muted-foreground` at **50% opacity** | `#4F5D75` at full opacity |
| Header row background | Transparent | `#E8E8E4` filled row ← wrong |
| Row hover | `bg-muted/30` | No `tr:hover` style on any table |

### 2g. Button System

| Variant | Reference Spec | Current |
|---------|---------------|---------|
| Primary | Coral fill, no border, radius-md (`6px`) | **Not implemented anywhere** — no filled primary button exists |
| Secondary | Surface bg + border, auto-width | `OutlineButton` with `width:100%; textAlign:'left'` — looks like a nav item |
| Destructive | Chestnut **fill** (`#8C2C23`) | `OutlineButton variant=danger` — outline only, not filled |
| Ghost | Transparent, muted text | Ad-hoc inline styles in dialogs |
| Shared abstraction | Single `<Button>` component | 3+ locally-defined: `OutlineButton`, `SmallButton`, ad-hoc `<button>` elements |

### 2h. CSS Variable Naming

The spec (`tokens.md`) defines tokens in `:root {}` without a prefix. The current implementation defines them inside `@theme {}` with `--color-` prefix. While functionally equivalent for Tailwind utilities, the naming diverges from the handoff spec and creates inconsistency if raw CSS vars are referenced in external tools or documentation.

```
Spec              →   Current
--background          --color-background    (in @theme)
--surface             --color-surface
--foreground          --color-foreground
--primary             --color-primary
--border              --color-border
--muted-foreground    --color-muted-foreground
```

### 2i. Off-Palette Colors (Violate 7-Color Constraint)

| Color | Where Used | Correct Replacement |
|-------|-----------|-------------------|
| `#3CA060` | `ReviewCard` — pros label, positive signal ticks | `#1B998B` (teal-jade) |
| `#D64045` | `ReviewCard` — cons label, negative signals | `#8C2C23` (chestnut) |
| `#8A8F98` | `hiring/page.tsx` — status subtext color | `var(--color-muted-foreground)` = `#4F5D75` |
| `#FAFAF9` | `ReviewCard` card background | `#FAFAF7` (surface-raised) |
| `#F9F9F7` | `settings/page.tsx` — `LiveScrapePanel` table header | `#FAFAF7` (surface-raised) |

### 2j. Architectural / Code Quality Issues

| Issue | Detail | Location |
|-------|--------|----------|
| `SectionCard` duplicated | Settings: `p-5, text-base font-semibold`; Dossier: `p-4, text-sm font-medium` — different padding and heading size | `settings/page.tsx:28–43`, `competitors/[slug]/page.tsx:364–392` |
| `SkeletonBox` duplicated | Identical component defined twice | `app/page.tsx:27–39`, `market/page.tsx:25–33` |
| ~200 redundant `fontFamily` inline styles | `fontFamily: "var(--font-body...)"` repeated on every element despite `body { font-family }` being set globally | All page files |
| `BarList` progress bars — single color | All bars render coral `#EF8354`; reference shows semantic color assignment (coral/teal/gold per metric) | `competitors/[slug]/page.tsx:298–362` |
| Star rating uses `★` character | Spec anti-pattern: "Never use emoji — Heroicons only, functional purpose required" | `competitors/[slug]/page.tsx:33–43` |
| Settings H1 has no subtitle | All other pages follow `h1 + subtitle` pattern | `settings/page.tsx:801–808` |
| Chart section heading font | `text-sm font-medium` DM Sans — spec says `text-base semibold display` (Sora) for section headings | `app/page.tsx:226–229` |

---

## Part 3 — Match Score by Component

| Component | vs Reference | Critical Gaps |
|-----------|-------------|---------------|
| Sidebar | 🔴 ~30% | Logo, section labels, 3rd tier, "BY TIER" sublabel, wrong chevron, wrong indents |
| Header | 🔴 ~20% | Static text, hardcoded API dot |
| KPI Cards | 🟠 ~60% | Icon + trend never passed; label 12px→10px; value 28px→24px |
| Callout | 🔴 ~40% | `finding` uses blue-slate instead of coral; 4px border not 3px |
| Badge | 🟡 ~75% | Extra border on all variants; off-palette warning color |
| Data Table | 🟡 ~65% | Filled header bg; no row hover; opacity mismatch; hiring table not uppercase |
| Buttons | 🔴 ~25% | No filled primary; secondary is full-width list-style |
| CSS Variables | 🟡 Naming drift | `--color-*` prefix vs bare `--*` per spec |
| Off-palette colors | 🟠 | 5 non-brand colors identified |

---

## Part 4 — Prioritized Fix Backlog

### 🔴 Critical — Fix First
1. **Callout `finding` variant**: Change `borderColor` + `bg` + `titleColor` from blue-slate → coral (`callout.tsx:16–22`)
2. **Sidebar logo + section labels**: Add `[CG]` mark, wordmark, "INTELLIGENCE"/"SYSTEM" labels (`sidebar.tsx`)
3. **Sidebar 3rd tier**: Restore "BY TIER" sub-label and correct indents (52px Tier 1, 68px Tier 2)
4. **Shared Button component**: Create `web/src/components/ui/button.tsx` with primary/secondary/destructive/ghost variants; replace all ad-hoc buttons
5. **KPI icon + trend**: Pass `icon` and `trend` props in `page.tsx` and `competitors/[slug]/page.tsx`
6. **Error messages**: Replace raw API paths with user-friendly messages + Retry CTA

### 🟠 High — Address Soon
7. **Header breadcrumb**: Make header route-aware; show page title instead of "CompGraph"
8. **Header API dot**: Connect to actual fetch state (or a global health store)
9. **Hiring filter bar**: Replace native `<select>` + Tremor `<Select>` mix with one consistent control family
10. **Off-palette colors**: Replace `#3CA060`, `#D64045`, `#8A8F98` with brand tokens
11. **Badge borders**: Remove `border` prop from all badge variants
12. **Settings buttons**: Remove `width:100%; textAlign:left` from `OutlineButton`
13. **Competitor breadcrumb**: Add breadcrumb to `competitors/[slug]/page.tsx` and `prospects/[slug]/page.tsx`

### 🟡 Medium — Next Sprint
14. **Callout border/opacity**: Correct to 3px, 10% opacity (`callout.tsx`)
15. **KPI label size**: Change 12px → 10px; value 28px → 24px
16. **Table header styles**: Remove filled bg, set muted-foreground at 50% opacity, add row hover
17. **Hiring table headers**: Uppercase case to match spec
18. **SectionCard**: Extract to shared component in `web/src/components/ui/section-card.tsx`
19. **SkeletonBox**: Extract to shared utility in `web/src/components/ui/skeleton.tsx`
20. **BarList colors**: Assign semantic colors (coral/teal/gold) instead of always coral

### ⚪ Polish
21. **Redundant fontFamily inlines**: Remove from all elements; let `body { font-family }` cascade
22. **Settings H1**: Add subtitle
23. **Star rating**: Replace `★` with Heroicons `StarIcon` filled/outline
24. **Empty states**: Add icon (Heroicons outline) + helper text + optional CTA

---

*Generated from analysis of `reference.html` (v2.0) vs live implementation at `localhost:3000`.*
