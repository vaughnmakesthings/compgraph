---
name: frontend-design
description: Use when building or modifying any frontend component, page, or layout. Enforces CompGraph design language, drives creative direction, and rejects AI-default patterns. Triggers on Next.js, React, CSS, Tailwind, component, UI, dashboard, page, layout work.
---

# Frontend Design

Build distinctive, production-grade interfaces for CompGraph. Every component must pass the "would a designer ship this?" test — and be memorable enough that someone could identify it as intentionally designed.

## Phase 1: Design Thinking

Before writing any code, commit to a clear aesthetic direction:

- **Purpose**: What problem does this interface solve? CompGraph is a B2B intelligence platform — users are analysts making decisions from data, not consumers browsing a landing page.
- **Tone**: Choose an intentional aesthetic. For CompGraph, lean toward: industrial/utilitarian, editorial/magazine, refined minimalism, or geometric precision. Reject: playful/toy-like, maximalist chaos, or generic SaaS.
- **Differentiation**: What makes this component UNFORGETTABLE? What's the one detail someone will remember? One strong choice beats five safe ones.
- **Constraints**: Framework (Next.js/React), performance budget, accessibility requirements.

**Match implementation complexity to the vision.** A dense data table needs restraint and precision. A brand intelligence dashboard can afford more visual personality. Execute the chosen direction fully — half-committed design is worse than no design.

## Phase 2: Pre-Flight Checklist

Before writing any JSX/TSX:

1. **Read the design tokens** — check `globals.css` or the design token file. If none exists, create one before building components.
2. **Check for existing components** — search the codebase for similar components before creating new ones.
3. **Confirm the layout context** — dashboard overview, detail view, data table, form, or settings? Layout strategy varies (see Layout Patterns below).

## Phase 3: The AI Antipattern Detector

Run every generated component through this checklist. If 3+ items match, the component needs a design pass:

| # | Check | AI Default (REJECT) | CompGraph Standard |
|---|-------|--------------------|--------------------|
| 1 | Primary color | Purple, indigo, violet | Brand palette from tokens |
| 2 | Gradients | Purple->blue hero gradient | Solid colors; gradients only with brand colors + clear purpose |
| 3 | Border radius | `rounded-xl` / `rounded-2xl` on everything | Varied: buttons `rounded-md`, cards `rounded-lg`, inputs `rounded` |
| 4 | Shadows | Dramatic shadows everywhere, glassmorphism | Scale: `shadow-sm` (subtle), `shadow-md` (cards), `shadow-lg` (modals only) |
| 5 | Typography | Inter, Roboto, Arial, system-ui | Intentional font pairing: distinctive display + refined body. Vary across projects — never converge on the same "safe" choice |
| 6 | Spacing | Identical gaps everywhere | Visual rhythm: tight data areas, airy navigation/headers |
| 7 | Layout | Centered hero -> 3-col features -> CTA | Data-dense layouts for B2B intelligence |
| 8 | Icons | Lucide/Heroicons scattered decoratively | Every icon communicates meaning; no filler |
| 9 | Animation | Fade-in-on-scroll, hover-scale on everything | Purpose-driven (see Motion section) |
| 10 | Transitions | `transition-all` | Targeted: `transition-colors`, `transition-opacity`, `transition-transform` |
| 11 | Copy | "Revolutionize" / "AI-powered" / sparkle emoji | Specific, concrete language describing what the feature does |
| 12 | Color variety | Single accent for everything | Semantic roles: success, warning, error, info, muted, accent |
| 13 | Backgrounds | Flat white or flat dark | Atmosphere: subtle textures, noise, or tonal variation where appropriate |
| 14 | Composition | Symmetrical grid, everything centered | Intentional hierarchy — asymmetry and density variation create interest |

## Design Token Requirements

Every frontend project must define these before building UI:

```css
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

  /* Typography — choose distinctive fonts, not defaults */
  --font-display: /* headings */;
  --font-body: /* body text */;
  --font-mono: /* code/data */;

  /* Spacing scale (not uniform — creates rhythm) */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2.5rem;
  --space-2xl: 4rem;

  /* Border radius scale (varied by component role) */
  --radius-sm: 0.25rem;   /* inputs, badges */
  --radius-md: 0.375rem;  /* buttons */
  --radius-lg: 0.5rem;    /* cards */
  --radius-xl: 0.75rem;   /* modals, sheets */

  /* Shadow scale (assigned by importance, not scattered) */
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px rgb(0 0 0 / 0.07);
  --shadow-lg: 0 10px 15px rgb(0 0 0 / 0.1);
}
```

## Component Authoring Rules

1. **Tokens first** — reference CSS variables, never hardcode colors or spacing in JSX
2. **Semantic markup** — `<table>` for tabular data, `<nav>` for navigation, `<main>` for content, `<aside>` for sidebars
3. **Accessible by default** — `aria-label` on icon-only buttons, `role` attributes where needed, keyboard navigation, focus-visible styles
4. **No decorative excess** — if removing an element doesn't reduce clarity, remove it
5. **Data density** — CompGraph is B2B intelligence. Prefer compact, information-rich layouts over spacious marketing layouts
6. **Dark mode parity** — every token must have a dark mode value. Design for both modes intentionally, don't just invert

## Motion & Interaction

Animation must earn its place. Every motion should answer: "what state change am I communicating?"

**Use motion for:**
- Page load orchestration — one staggered reveal sequence (`animation-delay`) creates more impact than scattered micro-interactions
- State change feedback — hover, active, focus, loading, success/error transitions
- Progressive disclosure — expanding sections, tabbed content, tooltip appearance
- Scroll-triggered reveals — sparingly, only for content that benefits from sequenced entry

**Implementation:**
- CSS-only for simple transitions. Use Motion library (Framer Motion) for orchestrated React animations
- Specify exact properties: `transition-colors 150ms`, not `transition-all`
- Keep durations tight: 100-200ms for micro-interactions, 300-500ms for larger reveals
- Easing: `ease-out` for entrances, `ease-in` for exits, `ease-in-out` for state changes

**Never:**
- Hover-scale on every card
- Fade-in-on-scroll for every section
- Bouncing/pulsing attention-grabbers
- Animation that blocks interaction or hides content

## Visual Depth & Atmosphere

Flat backgrounds are a missed opportunity. Create depth appropriate to the context:

- **Subtle tonal variation** — surface colors that shift slightly between sections create hierarchy without borders
- **Noise/grain textures** — a hint of texture at low opacity prevents the sterile "AI-generated" look
- **Layered surfaces** — cards on backgrounds, raised surfaces for active states
- **Controlled shadows** — follow the shadow scale. Shadows communicate elevation, not decoration

**Avoid:** glassmorphism (backdrop-blur + transparency), gradient meshes on data-heavy views, heavy overlays that reduce readability.

## Layout Patterns for CompGraph

| Context | Pattern | NOT This |
|---------|---------|----------|
| Dashboard overview | Dense metric grid + data table | Marketing hero + feature cards |
| Detail view | Header + tabbed content + sidebar context | Full-width single column |
| Data table | Sticky header, sortable columns, compact rows | Card grid with large images |
| Form | Labeled fields, inline validation, compact layout | Full-page wizard with illustrations |
| Settings | Grouped sections with descriptions | Dashboard-style cards |

**Spatial composition:** Don't default to symmetric grids. Use intentional hierarchy — varying column widths, strategic negative space, and density variation (tight data clusters vs. breathing room around navigation) to guide the eye.

## Phase 4: Review Gate

After generating any component, verify:

- [ ] Zero antipattern detector items triggered (checked all 14)
- [ ] All colors reference design tokens (no hardcoded hex in JSX)
- [ ] Typography uses the defined font pairing
- [ ] Spacing creates visual rhythm (not metronomic)
- [ ] Semantic HTML elements used
- [ ] Dark mode tested (both modes render correctly)
- [ ] Accessible (keyboard nav, screen reader labels)
- [ ] Motion is purpose-driven (no decorative animation)
- [ ] Component has a clear aesthetic point-of-view (not generic)
- [ ] Would pass the "is this clearly AI-generated?" test — it shouldn't be obvious
