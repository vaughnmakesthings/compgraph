# Mockup Banner — Design Doc

**Date:** 2026-02-23
**Status:** Approved

## Problem

Three pages in the CompGraph frontend (`/competitors/[slug]`, `/prospects`, `/prospects/[slug]`) are populated entirely with static mock data from `@/lib/mock/`. Without a visible indicator, stakeholders reviewing these pages may mistake placeholder content for live data.

## Decision

Add a persistent, always-visible `MockupBanner` component at the top of each affected page. The banner uses the project's amber caution palette and is unambiguous without disrupting the data-dense layout.

## Pages in Scope

| Route | File | Mock source |
|-------|------|-------------|
| `/competitors/[slug]` | `web/src/app/competitors/[slug]/page.tsx` | `DOSSIER_MOCKS` |
| `/prospects` | `web/src/app/prospects/page.tsx` | `PROSPECTS` |
| `/prospects/[slug]` | `web/src/app/prospects/[slug]/page.tsx` | `PROSPECT_MOCKS` |

`/competitors` (list) is excluded — it pulls live API data.

## Component

**File:** `web/src/components/content/mockup-banner.tsx`

**Props:** None. Self-contained, zero config.

**Visual spec:**
- Full-width bar with `mb-6` bottom margin (matches page header convention)
- Background: `#DCB2560D` (amber 5% opacity)
- Border: `1px solid #DCB25640` all sides + `2px solid #DCB256` top edge
- Border-radius: `var(--radius-lg, 8px)`
- Padding: `12px 16px`
- Layout: `flex items-center gap-3`

**Label pill:** "MOCKUP" — uppercase, 10px, weight 700, `#A07D28` text on `#DCB2561A` bg, same pattern as `SignalPip` in prospects page.

**Body text:** "This section contains placeholder data for design review. It does not reflect live system data." — 13px, `#2D3142`, `var(--font-body)`.

## Placement

Inserted as the first element inside each page's root `<div>`, before the page header block.

## Removal Plan

When a page transitions to live data:
1. Delete `<MockupBanner />` from that page's JSX
2. Once all three pages are live, delete `mockup-banner.tsx`
