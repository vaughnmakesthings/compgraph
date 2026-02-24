# Component Patterns — Implementation Spec

## Typography Scale

All font sizes are **minimum floors**. Never go below these values.

### Display (Sora)
| Use | Size | Weight | Tracking |
|---|---|---|---|
| Page title (h1) | 24px | 700 | -0.01em |
| Section title (h2) | 20px | 600 | -0.01em |
| Card title (h3) | 16px | 600 | normal |
| Overline / eyebrow | 11px | 600 | 0.06em (uppercase) |

### Body (DM Sans)
| Use | Size | Weight |
|---|---|---|
| Body text | 14px | 400 |
| Body emphasis | 14px | 500 |
| UI labels | 13px | 500 |
| Table headers | 12px | 600 (uppercase, 0.04em tracking) |
| Table body | 14px | 400 |
| Small labels / badges | 12px | 500 |
| Annotations (absolute minimum) | 11px | 400 |

### Data (JetBrains Mono)
| Use | Size | Weight |
|---|---|---|
| KPI hero value | 28px | 500 |
| KPI secondary | 18px | 400 |
| Table data cells | 13px | 400 |
| Inline code | 13px | 400 |
| Axis labels / legends | 11px | 400 |
| Micro counts (badges) | 11px | 400 |

---

## KPI Cards

```tsx
<Card>
  <div className="flex items-center gap-2 mb-2">
    <ChartBarIcon className="w-4 h-4 text-muted-foreground" />
    <span className="font-body text-xs font-medium uppercase tracking-wide text-muted-foreground">
      Total Postings
    </span>
  </div>
  <div className="font-mono text-[28px] font-medium text-foreground">
    1,247
  </div>
  <div className="flex items-center gap-1.5 mt-1">
    <ArrowUpIcon className="w-3.5 h-3.5 text-success" />
    <span className="font-mono text-sm text-success">+12.4%</span>
    <span className="text-xs text-muted-foreground">vs last month</span>
  </div>
</Card>
```

| Element | Font | Size | Color |
|---|---|---|---|
| Label | DM Sans uppercase | 12px | `--muted-foreground` |
| Value | JetBrains Mono | 28px | `--foreground` |
| Trend (positive) | JetBrains Mono | 14px | `--success` |
| Trend (negative) | JetBrains Mono | 14px | `--error` |
| Period label | DM Sans | 12px | `--muted-foreground` |

**Card container:**
- Background: `var(--surface)`
- Border: 1px `var(--border)`
- Radius: `var(--radius-lg)` (8px)
- Padding: 20px
- Hover: border opacity 80%

---

## Data Tables

```tsx
<table className="w-full">
  <thead>
    <tr className="border-b border-border">
      <th className="font-body text-xs font-semibold uppercase tracking-wide text-muted-foreground text-left py-3 px-4">
        Company
      </th>
      {/* ... */}
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-border/50 hover:bg-muted/30 transition-colors duration-100">
      <td className="font-body text-sm text-foreground py-3 px-4">
        BDS Connected Solutions
      </td>
      <td className="font-mono text-[13px] text-foreground py-3 px-4">
        247
      </td>
      {/* ... */}
    </tr>
  </tbody>
</table>
```

| Element | Font | Size | Color |
|---|---|---|---|
| Header | DM Sans uppercase | 12px 600 | `--muted-foreground` |
| Body text | DM Sans | 14px 400 | `--foreground` |
| Body numeric | JetBrains Mono | 13px 400 | `--foreground` |
| Row border | — | 1px | `--border` at 50% |
| Row hover | — | — | `--muted` at 30% |

---

## Badges

Semantic status badges. Use status tokens, never chart colors.

```tsx
// Success
<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-success-muted text-success font-body text-xs font-medium">
  <ArrowTrendingUpIcon className="w-3 h-3" />
  Growing
</span>

// Warning
<span className="... bg-warning-muted text-warning ...">Stale</span>

// Error
<span className="... bg-error-muted text-error ...">Declining</span>

// Neutral
<span className="... bg-muted text-muted-foreground ...">Pending</span>
```

| Property | Value |
|---|---|
| Font | DM Sans 12px 500 |
| Padding | 2px 8px |
| Radius | `var(--radius-sm)` (4px) |
| Background | `var(--{status}-muted)` (10% opacity fill) |
| Text | `var(--{status})` |

---

## Callout Components

Build on shadcn Alert as base. Four variants:

```tsx
// Finding — key intelligence insight
<Alert variant="finding">  {/* 3px coral left border, coral 10% bg */}
  <LightBulbIcon />
  <AlertTitle>Key Finding</AlertTitle>
  <AlertDescription>BDS is hiring 3× faster in the Midwest...</AlertDescription>
</Alert>

// Positive signal
<Alert variant="positive">  {/* 3px teal left border, teal 10% bg */}

// Risk signal
<Alert variant="risk">  {/* 3px chestnut left border, chestnut 10% bg */}

// Low confidence / stale
<Alert variant="caution">  {/* 3px gold left border, gold 10% bg */}
```

| Variant | Border Color | Background |
|---|---|---|
| `finding` | `var(--primary)` coral | `var(--accent)` |
| `positive` | `var(--success)` teal | `var(--success-muted)` |
| `risk` | `var(--error)` chestnut | `var(--error-muted)` |
| `caution` | `var(--warning)` gold | `var(--warning-muted)` |

Common: `border-left: 3px solid`, `padding: 16px`, `radius: var(--radius-md)`.

---

## Charts (Tremor-Inspired)

Use Recharts or similar. Style with CompGraph tokens.

**Common chart styles:**
| Element | Value |
|---|---|
| Series colors | Chart palette in order: coral → teal → blue-slate → gold → chestnut |
| Gridlines | 1px, `var(--border)` at 30% opacity |
| Axis labels | DM Sans 11px, `var(--muted-foreground)` |
| Axis ticks | `var(--border)` at 50% |
| Legend text | DM Sans 13px, `var(--muted-foreground)` |
| Legend dot | 8px circle, matching series color |
| Tooltip bg | `var(--surface)` |
| Tooltip border | 1px `var(--border)` |
| Tooltip radius | 8px |
| Tooltip shadow | `0 4px 12px rgba(0,0,0,0.08)` light, `rgba(0,0,0,0.3)` dark |
| Tooltip text | DM Sans 13px, values in JetBrains Mono 13px |

**Sparkline (inline mini chart):**
- Height: 32px
- No axes, no labels, no grid
- Single color from chart palette
- Stroke width: 1.5px
- Area fill: same color at 10% opacity

---

## Buttons

```tsx
// Primary
<Button variant="default">Run Scrape</Button>
// → bg coral, text white, hover darken 10%, radius-md

// Secondary
<Button variant="outline">Export CSV</Button>
// → bg surface, border, hover surface-raised, radius-md

// Ghost
<Button variant="ghost">Cancel</Button>
// → no bg, no border, hover muted, radius-md

// Destructive
<Button variant="destructive">Delete</Button>
// → bg error, text white, hover darken 10%, radius-md
```

All buttons: DM Sans 14px 500, padding 8px 16px, transition `background-color 100ms, border-color 100ms`.

---

## Inputs

```tsx
<Input
  className="bg-surface border-input focus:ring-2 focus:ring-ring rounded-sm text-sm"
  placeholder="Search competitors..."
/>
```

| Property | Value |
|---|---|
| Background | `var(--surface)` |
| Border | 1px `var(--input)` |
| Focus ring | 2px `var(--ring)` (coral) |
| Radius | `var(--radius-sm)` (4px) |
| Font | DM Sans 14px |
| Placeholder | `var(--muted-foreground)` |
| Height | 36px |

---

## Component Quick Reference

| Component | Background | Border | Hover | Radius |
|---|---|---|---|---|
| Card | `var(--surface)` | `var(--border)` | border opacity 80% | `--radius-lg` |
| Table row | transparent | none | `var(--muted)` at 30% | none |
| Input | `var(--surface)` | `var(--input)` | `var(--ring)` focus | `--radius-sm` |
| Button primary | `var(--primary)` | none | darken 10% | `--radius-md` |
| Button secondary | `var(--surface)` | `var(--border)` | `var(--surface-raised)` | `--radius-md` |
| Badge success | `var(--success-muted)` | none | — | `--radius-sm` |
| Badge warning | `var(--warning-muted)` | none | — | `--radius-sm` |
| Badge error | `var(--error-muted)` | none | — | `--radius-sm` |
| Sidebar | `var(--sidebar-bg)` | `var(--sidebar-border)` | `var(--sidebar-bg-active)` | — |
