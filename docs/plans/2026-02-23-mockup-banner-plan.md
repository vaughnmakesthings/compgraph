# MockupBanner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a persistent amber "MOCKUP" banner to three pages that contain only placeholder data, so stakeholders never mistake mock content for live data.

**Architecture:** Create a single self-contained `MockupBanner` component with no props, then insert one `<MockupBanner />` call at the top of each affected page. No state, no logic, no tests needed — pure presentational JSX.

**Tech Stack:** Next.js 16, React, inline styles (matching project convention — no Tailwind class-based color tokens, all colors are hex literals).

---

### Task 1: Create the MockupBanner component

**Files:**
- Create: `web/src/components/content/mockup-banner.tsx`

**Step 1: Create the component file**

```tsx
// web/src/components/content/mockup-banner.tsx
export function MockupBanner() {
  return (
    <div
      style={{
        borderTop: "2px solid #DCB256",
        border: "1px solid #DCB25640",
        borderTopWidth: "2px",
        borderTopColor: "#DCB256",
        backgroundColor: "#DCB2560D",
        borderRadius: "var(--radius-lg, 8px)",
        padding: "12px 16px",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
      }}
    >
      <span
        style={{
          display: "inline-block",
          backgroundColor: "#DCB2561A",
          color: "#A07D28",
          border: "1px solid #DCB25640",
          borderRadius: "var(--radius-sm, 4px)",
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          padding: "3px 8px",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Mockup
      </span>
      <span
        style={{
          fontSize: "13px",
          color: "#2D3142",
          lineHeight: "1.5",
        }}
      >
        This section contains placeholder data for design review. It does not reflect live system data.
      </span>
    </div>
  );
}
```

**Step 2: Verify the file exists and has no syntax errors**

```bash
cd web && npm run typecheck 2>&1 | head -20
```

Expected: No errors referencing `mockup-banner.tsx`.

**Step 3: Commit**

```bash
git add web/src/components/content/mockup-banner.tsx
git commit -m "feat: add MockupBanner component for mock-data pages"
```

---

### Task 2: Add MockupBanner to /competitors/[slug]

**Files:**
- Modify: `web/src/app/competitors/[slug]/page.tsx` (top of the return block)

**Step 1: Add the import**

Find the existing imports at the top of the file (they include `Callout`, `BarChart`, etc.) and add:

```tsx
import { MockupBanner } from "@/components/content/mockup-banner";
```

**Step 2: Insert `<MockupBanner />` as the first element in the return**

The page's return currently opens with something like:

```tsx
return (
  <div>
    {/* back button or header */}
```

Insert `<MockupBanner />` immediately after the opening `<div>`:

```tsx
return (
  <div>
    <MockupBanner />
    {/* rest of existing content unchanged */}
```

**Step 3: Run typecheck**

```bash
cd web && npm run typecheck 2>&1 | grep -E "error|warning" | head -20
```

Expected: No new errors.

**Step 4: Commit**

```bash
git add web/src/app/competitors/[slug]/page.tsx
git commit -m "feat: show MockupBanner on competitor dossier pages"
```

---

### Task 3: Add MockupBanner to /prospects (list)

**Files:**
- Modify: `web/src/app/prospects/page.tsx` (top of the return block)

**Step 1: Add the import**

```tsx
import { MockupBanner } from "@/components/content/mockup-banner";
```

**Step 2: Insert `<MockupBanner />` as the first element in the return**

The page's return currently opens with:

```tsx
return (
  <div>
    {/* Page header */}
    <div className="mb-6">
      <h1 ...>Sales Prospects</h1>
```

Insert `<MockupBanner />` immediately after the opening `<div>`:

```tsx
return (
  <div>
    <MockupBanner />
    {/* Page header */}
    <div className="mb-6">
```

**Step 3: Run typecheck**

```bash
cd web && npm run typecheck 2>&1 | grep -E "error|warning" | head -20
```

Expected: No new errors.

**Step 4: Commit**

```bash
git add web/src/app/prospects/page.tsx
git commit -m "feat: show MockupBanner on prospects list page"
```

---

### Task 4: Add MockupBanner to /prospects/[slug]

**Files:**
- Modify: `web/src/app/prospects/[slug]/page.tsx` (top of the return block)

**Step 1: Add the import**

```tsx
import { MockupBanner } from "@/components/content/mockup-banner";
```

**Step 2: Insert `<MockupBanner />` as the first element in the return**

Same pattern — find the page component's return statement, insert after the opening `<div>`:

```tsx
return (
  <div>
    <MockupBanner />
    {/* rest of existing content unchanged */}
```

**Step 3: Run full lint + typecheck + test**

```bash
cd web && npm run lint && npm run typecheck && npm test
```

Expected: All pass, 0 warnings.

**Step 4: Commit**

```bash
git add web/src/app/prospects/[slug]/page.tsx
git commit -m "feat: show MockupBanner on prospect dossier pages"
```

---

### Task 5: Visual verification

**Step 1: Start the dev server**

```bash
cd web && npm run dev
```

**Step 2: Visit each page and confirm the banner appears**

- http://localhost:3000/competitors/bds (or any valid slug)
- http://localhost:3000/prospects
- http://localhost:3000/prospects/keurig-dr-pepper (or any valid slug)

Expected: Amber "MOCKUP" pill + description text visible at the top of each page, above the page heading.

**Step 3: Confirm /competitors (list) does NOT show the banner**

- http://localhost:3000/competitors

Expected: No banner visible.

**Step 4: Create PR**

Use `/pr` skill to open a pull request.
