# Tremor Adoption Design

**Date:** 2026-02-21
**Status:** Approved

## Decision

Adopt Tremor as the dashboard component layer for CompGraph Eval, installed via shadcn CLI copy-paste model alongside existing shadcn/ui components.

## Rationale

- Tremor is built on Radix + Tailwind + Recharts — the same stack we already use
- Copy-paste model gives full source ownership; brand tokens apply directly
- 35+ dashboard-specific components (KPI cards, trackers, category bars) that shadcn/ui doesn't offer
- Acquired by Vercel — long-term maintenance aligned with Next.js

## Core Component Set (Phase 1)

| Component | Primary Pages |
|---|---|
| BarChart | Leaderboard, Accuracy, Prompt Diff |
| AreaChart | Dashboard, Accuracy |
| DonutChart | Dashboard, Review |
| BarList | Leaderboard |
| CategoryBar | Accuracy Review |
| Tracker | Run Tests |
| SparkChart | Dashboard, Leaderboard |
| ProgressBar | Dashboard, Review |
| ProgressCircle | Run Tests |
| Badge | All pages |

## Dependencies

- `recharts` — peer dependency for chart components
- No npm package for Tremor itself (copy-paste model)

## Token Compatibility

Tremor chart `colors` prop resolves CSS variables: `colors={["chart-1"]}` → `var(--chart-1)`.
Our existing `--chart-1` through `--chart-5` and `--status-*` tokens work directly.

## What Stays Unchanged

- `globals.css` (brand tokens, dark mode, fonts)
- Layout shell (app-shell, sidebar, header)
- Existing shadcn components (button, input, tooltip, sheet, separator, avatar)
- Custom components (data-table, status-badge) — replace later when Tremor equivalents needed
