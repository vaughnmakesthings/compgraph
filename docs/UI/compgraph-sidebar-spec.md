# Sidebar Navigation — Component Spec

## Overview

Fixed left sidebar (280px) with 3-tier collapsible navigation. The sidebar background is always dark (`--sidebar-bg: #2D3142`) regardless of light/dark mode.

## Layout

```
┌─────────────────────────┐
│ [CG] CompGraph          │  ← Logo (Sora 17px 600)
├─────────────────────────┤  ← 1px border rgba(79,93,117,0.4)
│ ▪ Dashboard             │  ← Simple nav item
│ ▪ Market Overview       │  ← Simple nav item
│                         │
│ INTELLIGENCE            │  ← Section label (DM Sans 12px uppercase)
│ ▪ Competitors        ▸  │  ← Tier 0: Parent (toggles open/close)
│   By tier               │  ← Sub-label (12px uppercase)
│   Tier 1 — Direct  5 ▸  │  ← Tier 1: Category group (toggles nested)
│     ● BDS Connected 247 │  ← Tier 2: Leaf entity
│     ● MarketSource  312 │  ← Tier 2: Leaf entity (active state)
│     ● Premium Rtl   191 │
│   Tier 2 — Adjacent 4 ▸ │  ← Tier 1: Collapsed
│   View All Competitors  │  ← Action link
│ ▪ Hiring Intel       ▸  │  ← Tier 0: Collapsed
│                         │
│ SYSTEM                  │  ← Section label
│ ▪ Scrape History        │  ← Simple nav item
│ ▪ Settings              │  ← Simple nav item
└─────────────────────────┘
```

## Tier 0 — Parent Items

Clickable parent items that toggle a submenu.

**Examples:** Competitors, Hiring Intel

```tsx
// React component structure
<button
  className="sidebar-parent"
  onClick={() => setOpen(!open)}
  aria-expanded={open}
>
  <UserGroupIcon className="sidebar-icon" />  {/* Heroicons 18px */}
  <span>Competitors</span>
  <ChevronRightIcon className="sidebar-chevron" />  {/* rotates 90° when open */}
</button>

{/* Submenu container — animate max-height */}
<div className={cn("sidebar-sub", open && "sidebar-sub--open")}>
  {/* Tier 1 items go here */}
</div>
```

**Styles:**
| Property | Value |
|---|---|
| Font | DM Sans 14px |
| Color | `--sidebar-text` (#D0D1D1) |
| Padding | 10px 20px |
| Gap | 12px between icon and label |
| Hover | bg `--sidebar-bg-active` (#363B4D), color #F0F0ED |
| Active | color #fff, bg `--sidebar-bg-active`, 3px coral left bar |
| Icon | 18×18px, opacity 0.7 default → 0.9 hover → 1.0 active |
| Chevron | 18×18px, opacity 0.45 default → 0.7 when open |
| Chevron animation | `transform: rotate(90deg)`, 150ms ease |

**Submenu container:**
| Property | Value |
|---|---|
| Closed | `max-height: 0; overflow: hidden` |
| Open | `max-height: 800px` |
| Transition | `max-height 200ms ease-out` |

## Tier 1 — Category Groups

Groups within a parent submenu. Each toggles its own nested list.

**Examples:** "Tier 1 — Direct", "Tier 2 — Adjacent"

```tsx
<button
  className="sidebar-sub-item"
  onClick={() => setGroupOpen(!groupOpen)}
  aria-expanded={groupOpen}
>
  <span>Tier 1 — Direct</span>
  <span className="sidebar-sub-count">5</span>
  <ChevronRightIcon className="sidebar-sub-chevron" />
</button>

<div className={cn("sidebar-sub-nested", groupOpen && "sidebar-sub-nested--open")}>
  {/* Tier 2 leaf items go here */}
</div>
```

**Styles:**
| Property | Value |
|---|---|
| Font | DM Sans 13px |
| Color | `--sidebar-text-muted` (#B0B1B5) |
| Padding | 8px 20px 8px 52px (indented under parent icon) |
| Layout | `display: flex; justify-content: space-between` |
| Hover | bg rgba(54,59,77,0.4), color #E8E8E3 |
| Active | color #fff, font-weight 500, 4px coral dot at left |
| Count badge | JetBrains Mono 11px, color rgba(191,192,192,0.4), margin-right 6px |
| Chevron | 14×14px, opacity 0.4 → 0.6 open, rotate 90° |

**Sub-label** (e.g., "By tier"):
| Property | Value |
|---|---|
| Font | DM Sans 12px uppercase, letter-spacing 0.06em |
| Color | rgba(191,192,192,0.4) |
| Padding | 12px 20px 6px 52px |

**Nested container:**
| Property | Value |
|---|---|
| Closed | `max-height: 0; overflow: hidden` |
| Open | `max-height: 500px` |
| Transition | `max-height 200ms ease-out` |

## Tier 2 — Leaf Entities

Individual items (competitor names, job feed entries, etc.) that navigate to detail pages.

**Examples:** "BDS Connected Solutions", "MarketSource"

```tsx
<Link
  href={`/competitors/${competitor.slug}`}
  className={cn("sidebar-leaf", isActive && "sidebar-leaf--active")}
>
  <span
    className="sidebar-leaf-dot"
    style={{ backgroundColor: chartColors[index % 5] }}
  />
  <span>{competitor.name}</span>
  <span className="sidebar-leaf-count">{competitor.postingCount}</span>
</Link>
```

**Styles:**
| Property | Value |
|---|---|
| Font | DM Sans 13px |
| Color | #A0A1A8 |
| Padding | 7px 20px 7px 68px (further indented under tier 1) |
| Gap | 10px between dot and name |
| Hover | bg rgba(54,59,77,0.3), color #E8E8E3 |
| Active | color #fff, font-weight 500 |

**Dot indicator:**
| Property | Value |
|---|---|
| Size | 7×7px circle |
| Color | Assigned from chart palette in order (coral, teal, blue-slate, gold, chestnut) |
| Opacity | 0.7 default → 1.0 active |
| Active glow | `box-shadow: 0 0 4px currentColor` |

**Count:**
| Property | Value |
|---|---|
| Font | JetBrains Mono 12px |
| Color | rgba(191,192,192,0.45) → rgba(255,255,255,0.5) active |
| Position | `margin-left: auto` |

## Section Labels

Non-interactive category headers.

```tsx
<div className="sidebar-section">Intelligence</div>
```

| Property | Value |
|---|---|
| Font | DM Sans 12px uppercase, letter-spacing 0.06em |
| Color | rgba(191,192,192,0.5) |
| Padding | 18px 20px 8px |

## Logo

```tsx
<div className="sidebar-logo">
  <div className="sidebar-logo-mark">CG</div>
  <span>CompGraph</span>
</div>
```

| Property | Value |
|---|---|
| Text | Sora 17px 600 weight, white |
| Mark | 32×32px, coral bg, rounded 6px, Sora 14px 700 white centered |
| Padding | 0 20px 18px |
| Border-bottom | 1px solid rgba(79,93,117,0.4) |
| Margin-bottom | 14px |

## Data Source

Sidebar navigation items are driven by:
- **Static routes:** Dashboard, Market Overview, Scrape History, Settings
- **Database-driven:** Competitors (grouped by tier), Hiring Intel sub-pages
- **Competitor tiers** come from a `competitor_tiers` table with `tier_number`, `tier_label`, and foreign keys to `competitors`
- **Posting counts** are live aggregates from the `job_postings` table

## Interaction Notes

- Clicking a parent (Tier 0) toggles the entire submenu open/closed
- Clicking a category group (Tier 1) toggles its leaf list open/closed
- Clicking a leaf entity (Tier 2) navigates to its detail page
- Multiple Tier 1 groups can be open simultaneously
- Only one Tier 0 parent should be expanded at a time (accordion behavior)
- Active leaf should be highlighted and its parent chain should be auto-expanded on page load
- URL-based active state detection via `usePathname()`
