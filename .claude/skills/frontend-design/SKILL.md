---
name: frontend-design
description: Use when building or modifying any frontend component, page, or layout. Enforces CompGraph design language and rejects AI-default patterns. Triggers on Next.js, React, CSS, Tailwind, component, UI, dashboard, page, layout work.
---

# Frontend Design

Build distinctive, production-grade interfaces for CompGraph. Every component must pass the "would a designer ship this?" test.

## Pre-Flight Checklist

Before writing any JSX/TSX:

1. **Identify the design tokens** — read the project's `globals.css` or design token file. If none exists yet, create one before building components.
2. **Check for existing components** — search the codebase for similar components before creating new ones.
3. **Confirm the layout context** — is this a data-dense dashboard view, a form, a detail page? Layout strategy varies.

## The AI Antipattern Detector

Run every generated component through this checklist. If 3+ items match, the component needs a design pass:

| # | Check | AI Default (REJECT) | CompGraph Standard |
|---|-------|--------------------|--------------------|
| 1 | Primary color | Purple, indigo, violet | Brand palette (defined in tokens) |
| 2 | Gradients | Purple→blue hero gradient | Solid colors; gradients only with brand colors + purpose |
| 3 | Border radius | `rounded-xl` / `rounded-2xl` on everything | Varied by role: buttons `rounded-md`, cards `rounded-lg`, inputs `rounded` |
| 4 | Shadows | Dramatic shadows everywhere, glassmorphism | Defined scale: `shadow-sm` (subtle), `shadow-md` (cards), `shadow-lg` (modals only) |
| 5 | Typography | Inter, uniform sizing | Intentional font pairing with display/body distinction |
| 6 | Spacing | Identical gaps everywhere | Visual rhythm: tight data areas, airy navigation/headers |
| 7 | Layout | Centered hero → 3-col features → CTA | Data-dense layouts appropriate to B2B intelligence |
| 8 | Icons | Lucide scattered decoratively | Every icon communicates meaning; no filler icons |
| 9 | Animation | Fade-in-on-scroll, hover-scale on cards | Purpose-driven: state feedback, loading, progressive disclosure |
| 10 | Transitions | `transition-all` | Targeted: `transition-colors`, `transition-opacity`, `transition-transform` |
| 11 | Copy | "Revolutionize" / "AI-powered" / sparkle emoji | Specific, concrete language describing what the feature does |
| 12 | Color variety | Single accent color for everything | Semantic color roles: success, warning, error, info, muted, accent |

## Design Token Requirements

Every frontend project must define these tokens before building UI:

```css
/* Required token categories */
:root {
  /* Brand palette — NEVER purple/indigo as primary */
  --color-primary: /* specific hex */;
  --color-primary-foreground: /* contrast text */;

  /* Semantic roles */
  --color-success: /* green family */;
  --color-warning: /* amber family */;
  --color-error: /* red family */;
  --color-info: /* blue family — not indigo */;
  --color-muted: /* neutral gray */;

  /* Surfaces */
  --color-background: /* page bg */;
  --color-surface: /* card bg */;
  --color-surface-raised: /* elevated card bg */;
  --color-border: /* default border */;

  /* Typography */
  --font-display: /* headings — NOT Inter */;
  --font-body: /* body text */;
  --font-mono: /* code/data */;

  /* Spacing scale (not uniform) */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2.5rem;
  --space-2xl: 4rem;

  /* Border radius scale (varied by role) */
  --radius-sm: 0.25rem;   /* inputs, badges */
  --radius-md: 0.375rem;  /* buttons */
  --radius-lg: 0.5rem;    /* cards */
  --radius-xl: 0.75rem;   /* modals, sheets */

  /* Shadow scale */
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px rgb(0 0 0 / 0.07);
  --shadow-lg: 0 10px 15px rgb(0 0 0 / 0.1);
}
```

## Component Authoring Rules

1. **Tokens first** — reference CSS variables, never hardcode colors or spacing
2. **Semantic markup** — use `<table>` for tabular data, `<nav>` for navigation, `<main>` for content, `<aside>` for sidebars
3. **Accessible by default** — `aria-label` on icon-only buttons, `role` attributes where needed, keyboard navigation, focus visible styles
4. **No decorative excess** — if removing an element doesn't reduce clarity, remove it
5. **Data density** — CompGraph is a B2B intelligence tool. Prefer compact, information-rich layouts over spacious marketing layouts
6. **Dark mode parity** — every token must have a dark mode value. Don't just invert — design for both modes intentionally

## Layout Patterns for CompGraph

| Context | Pattern | NOT This |
|---------|---------|----------|
| Dashboard overview | Dense metric grid + data table | Marketing hero + feature cards |
| Detail view | Header + tabbed content + sidebar context | Full-width single column |
| Data table | Sticky header, sortable columns, compact rows | Card grid with large images |
| Form | Labeled fields, inline validation, compact layout | Full-page wizard with illustrations |
| Settings | Grouped sections with descriptions | Dashboard-style cards |

## Review Gate

After generating any component, verify:
- [ ] No items from the Antipattern Detector triggered
- [ ] All colors reference design tokens (no hardcoded hex in JSX)
- [ ] Typography uses the defined font pairing
- [ ] Spacing creates visual rhythm (not metronomic)
- [ ] Semantic HTML elements used
- [ ] Dark mode tested (both modes render correctly)
- [ ] Accessible (keyboard nav, screen reader labels)
