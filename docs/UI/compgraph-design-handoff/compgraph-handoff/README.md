# CompGraph Design System Handoff

## For: Claude Code Development Agents
## Date: February 2026

---

## Quick Start

1. **Read `CLAUDE.md` first** — it's the top-level instruction file that Claude Code reads automatically. Place it at your project root.

2. **Drop in `design-system/theme.css`** — import it in your global CSS. It contains the full Tailwind v4 `@theme` directive plus all CSS custom properties for light/dark mode and shadcn/ui overrides.

3. **Reference `design-system/tokens.md`** for the complete token specification including the 7 source colors, derived neutrals, semantic states, chart palette, typography scale, and anti-patterns.

4. **Open `design-system/reference.html`** in a browser to see every component visually rendered — colors, typography, sidebar, tables, charts, badges, and callouts.

5. **Build components per `specs/`** — sidebar navigation (3-tier collapsible pattern) and general component patterns (cards, tables, charts, badges, callouts, buttons, inputs).

## File Inventory

```
CLAUDE.md                          → Agent instructions (project root)
design-system/
  theme.css                        → Drop-in Tailwind v4 theme + CSS vars
  tokens.md                        → Full token specification (429 lines)
  reference.html                   → Visual reference (open in browser)
specs/
  sidebar-navigation.md            → 3-tier collapsible sidebar spec
  component-patterns.md            → Cards, tables, charts, badges, etc.
```

## Stack Summary

Next.js 16 · Tailwind v4 · shadcn/ui · Heroicons Outline · Sora + DM Sans + JetBrains Mono · Supabase

## Key Constraints

- Only 7 hand-picked colors — no Tailwind default grays
- No purple/indigo/violet anywhere
- Minimum 12px for reading text, 14px for body
- Heroicons Outline only — no solid, no mini, no other libraries
- Every shadcn/ui default color must be overridden
