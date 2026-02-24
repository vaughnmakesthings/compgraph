# CompGraph — Claude Code Agent Instructions

## What Is This

CompGraph is a B2B competitive intelligence platform for the field marketing industry. It scrapes job postings from competing agencies, enriches them with LLM entity extraction, and surfaces hiring patterns, client relationships, pay benchmarking, and market positioning data.

## Stack

- **Framework:** Next.js 16 (App Router)
- **Styling:** Tailwind CSS v4 (inline `@theme` directive — no `tailwind.config.js`)
- **Components:** shadcn/ui (override all default colors with CompGraph tokens)
- **Data Viz:** Tremor-inspired patterns (custom-built, not the Tremor package)
- **Icons:** Heroicons Outline only (`@heroicons/react/24/outline`)
- **Fonts:** Sora (display), DM Sans (body), JetBrains Mono (data/code)
- **Database:** Supabase (Postgres + Auth + Edge Functions)

## Design System Files

Read these before writing any frontend code:

| File | Purpose |
|---|---|
| `design-system/theme.css` | Drop-in Tailwind v4 theme with all CSS custom properties |
| `design-system/tokens.md` | Full token specification with semantic mappings, typography scale, chart palette |
| `design-system/reference.html` | Visual reference — open in browser to see every component rendered |
| `specs/sidebar-navigation.md` | 3-tier collapsible sidebar component spec |
| `specs/component-patterns.md` | Implementation patterns for cards, tables, charts, badges, callouts |

## Critical Rules

### Colors
- **Only 7 source colors exist.** All UI derives from them. See `tokens.md` §1.
- **Never use Tailwind default grays** (slate, zinc, gray, neutral). Use derived neutrals from `#2D3142`.
- **Never use purple, indigo, or violet.** They don't exist in this system.
- **shadcn/ui colors must be overridden.** Map every shadcn token to CompGraph equivalents per `tokens.md` §8.

### Typography
- **Display/headings:** Sora (600–700 weight)
- **Body/UI:** DM Sans (400–600 weight)
- **Data/code/metrics:** JetBrains Mono (400–500 weight)
- **Minimum sizes:** 11px annotations only, 12px+ all reading text, 14px body minimum
- **Never mix font roles.** Don't use Sora for body text or DM Sans for KPI values.

### Icons
- **Heroicons Outline 24px only.** No solid, no mini, no other icon libraries.
- **Every icon must communicate meaning.** No decorative icons. No emoji.
- **Stroke width 1.5** (Heroicons default).

### Anti-Patterns (Do NOT)
- No gradient hero sections
- No glassmorphism (backdrop-blur + transparency) on cards
- No `transition-all` — specify exact properties
- No uniform `rounded-xl` — use the radius scale (sm: 4px, md: 6px, lg: 8px, xl: 12px)
- No "AI-powered" badges or sparkle icons
- No chart colors for semantic meaning — use status tokens (success/warning/error)

### Sidebar
- Fixed left sidebar, 280px wide, dark background (`#2D3142`)
- 3-tier collapsible navigation pattern. See `specs/sidebar-navigation.md`.
- Chevron rotation animation on toggle (150ms ease)

### Data Visualization
- 5-color chart palette (in order): Coral `#EF8354`, Teal `#1B998B`, Blue-Slate `#4F5D75`, Gold `#DCB256`, Chestnut `#8C2C23`
- Always use this order. First series = coral, second = teal, etc.
- Gridlines: 1px, use `--border` token at 30% opacity
- Axis labels: DM Sans 11px, `--muted-foreground`
- Tooltips: `--surface` background, `--border` border, 8px radius, subtle shadow

### Accessibility
- All interactive elements must have visible focus states (2px coral ring)
- Color alone must not convey meaning — pair with icons or text labels
- Minimum contrast: 4.5:1 for body text, 3:1 for large text / UI elements
