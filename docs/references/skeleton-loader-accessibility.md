# Skeleton Loader Accessibility

Reference for implementing accessible skeleton loaders that prevent layout shift while being screen reader compatible.

**CompGraph context:** Data-dense dashboard pages (Pipeline Health, Posting Explorer, Brand Intel) replacing generic spinners with content-aware skeletons. Stack: Tailwind CSS v4, Next.js 16 App Router, React 19. Existing `SkeletonBox` component in `web/src/components/ui/skeleton.tsx` uses inline styles with `aria-hidden="true"`.

---

## Quick Reference

| Attribute | Where | Purpose |
|-----------|-------|---------|
| `aria-busy="true"` | Container wrapping skeleton + content | Tells AT "content is updating, wait" |
| `aria-busy="false"` | Same container, after load | Triggers AT to announce new content |
| `aria-live="polite"` | Same container (set once, not toggled) | Enables AT to watch for content changes |
| `aria-hidden="true"` | Each skeleton placeholder element | Hides decorative shapes from AT |
| `role="status"` | Loading announcement element | Implicit `aria-live="polite"` |
| `sr-only` text | Inside container | "Loading pipeline data..." for context |

**Key pattern:** `aria-busy` goes on the **container**, not on individual skeleton elements. Individual skeletons are `aria-hidden="true"` (decorative).

---

## The Recommended Pattern

Based on Adrian Roselli's [More Accessible Skeletons](https://adrianroselli.com/2020/11/more-accessible-skeletons.html):

```tsx
// SkeletonContainer.tsx
"use client";

import { type ReactNode } from "react";

interface SkeletonContainerProps {
  loading: boolean;
  skeleton: ReactNode;
  children: ReactNode;
  label?: string;  // e.g., "Pipeline health data"
}

export function SkeletonContainer({
  loading,
  skeleton,
  children,
  label = "Content",
}: SkeletonContainerProps) {
  return (
    <div aria-live="polite" aria-busy={loading}>
      {loading ? (
        <>
          <span className="sr-only">Loading {label}...</span>
          <div aria-hidden="true">{skeleton}</div>
        </>
      ) : (
        children
      )}
    </div>
  );
}
```

### Why This Works

1. `aria-live="polite"` is set once on the container --- AT watches for content changes
2. While `aria-busy="true"`, screen readers suppress intermediate updates (avoids reading each skeleton element)
3. When `loading` flips to `false`, `aria-busy="false"` + content swap triggers AT announcement
4. Individual skeleton shapes are `aria-hidden="true"` --- purely decorative
5. `sr-only` text provides meaningful context during loading

### Anti-Pattern: `role="alert"` + `aria-live="polite"`

Do NOT combine `role="alert"` (implies `aria-live="assertive"`) with `aria-live="polite"` --- contradictory semantics. Vuetify [filed a bug](https://github.com/vuetifyjs/vuetify/issues/10999) for this exact issue.

---

## Updated SkeletonBox Component

The existing `SkeletonBox` has correct `aria-hidden` but uses inline styles. Upgraded version with Tailwind v4 and motion safety:

```tsx
// web/src/components/ui/skeleton.tsx
import React from "react";

interface SkeletonBoxProps {
  className?: string;
  style?: React.CSSProperties;
}

export function SkeletonBox({ className = "", style }: SkeletonBoxProps) {
  return (
    <div
      className={`bg-[#E8E8E4] rounded-lg animate-pulse motion-reduce:animate-none ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

// Content-aware skeleton variants
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-4 bg-[#E8E8E4] rounded-md animate-pulse motion-reduce:animate-none"
          style={{ width: i === lines - 1 ? "60%" : "100%" }}
        />
      ))}
    </div>
  );
}

export function SkeletonKpi() {
  return (
    <div className="space-y-2" aria-hidden="true">
      <div className="h-3 w-24 bg-[#E8E8E4] rounded-md animate-pulse motion-reduce:animate-none" />
      <div className="h-8 w-16 bg-[#E8E8E4] rounded-md animate-pulse motion-reduce:animate-none" />
    </div>
  );
}
```

### `prefers-reduced-motion` Support

Tailwind v4 `motion-reduce:` variant maps to `@media (prefers-reduced-motion: reduce)`. Two strategies:

| Strategy | Code | Effect |
|----------|------|--------|
| **Stop animation** | `motion-reduce:animate-none` | Static gray block |
| **Slow animation** | Custom keyframe at 4s duration | Gentle pulse |

**Recommendation:** `motion-reduce:animate-none` (static gray) is simplest and safest. Users who set reduced motion want NO animation.

For custom animation in `globals.css` (Tailwind v4 `@theme`):

```css
@theme {
  --animate-skeleton: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Tailwind v4 handles this via motion-reduce: variant,
   but explicit fallback for non-Tailwind contexts: */
@media (prefers-reduced-motion: reduce) {
  .animate-skeleton { animation: none; }
}
```

---

## Layout Shift Prevention

Skeletons must match final content dimensions to avoid CLS (Cumulative Layout Shift).

### Dimension Matching Strategy

| Component | Skeleton Size | Technique |
|-----------|--------------|-----------|
| KPI card (KpiCard) | `h-8 w-16` value + `h-3 w-24` label | Fixed height/width matching rendered KPI |
| Table row | `h-10 w-full` per row | Match `<tr>` height |
| Chart area | `h-64 w-full` | Match Tremor chart container |
| Text paragraph | `h-4 w-full` x N lines | Last line at 60% width |
| Avatar/icon | `h-8 w-8 rounded-full` | Match icon size |

### Implementation Rules

1. **Set explicit `min-h` on container** --- even if skeleton renders, container must not collapse
2. **Use the same grid/flex layout** for skeleton and content --- prevents reflow
3. **Reserve space for filters/controls** --- toolbar skeletons prevent page jump when filters render

```tsx
// Dashboard skeleton matching the real layout grid
function DashboardSkeleton() {
  return (
    <div aria-hidden="true">
      {/* Match the 4-column KPI grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="p-4 bg-white rounded-lg shadow-sm">
            <SkeletonKpi />
          </div>
        ))}
      </div>
      {/* Match chart area height */}
      <SkeletonBox className="h-64 w-full mb-6" />
      {/* Match table rows */}
      <div className="space-y-2">
        {Array.from({ length: 5 }, (_, i) => (
          <SkeletonBox key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}
```

---

## Next.js App Router Integration

### `loading.tsx` vs Manual Suspense

| Approach | When to Use | Accessibility |
|----------|-------------|---------------|
| `loading.tsx` file | Route-level loading (page transitions) | Must add `aria-busy` wrapper yourself |
| `<Suspense fallback={...}>` | Component-level streaming | Same --- wrap in `aria-live` container |
| Manual `useState` + `useEffect` | API-fetched data (current CompGraph pattern) | Full control via `SkeletonContainer` |

**CompGraph today:** All pages use `"use client"` + `useState`/`useEffect`. The `SkeletonContainer` wrapper is the right pattern. When migrating to RSC, move `aria-busy` logic to the Suspense boundary.

### With Current Data Fetching Pattern

```tsx
// Typical CompGraph page with accessible skeleton
"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { SkeletonContainer } from "@/components/ui/skeleton";

export default function PipelineHealthPage() {
  const [data, setData] = useState<PipelineData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPipelineHealth()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <SkeletonContainer
      loading={loading}
      label="pipeline health data"
      skeleton={<DashboardSkeleton />}
    >
      {data && <DashboardContent data={data} />}
    </SkeletonContainer>
  );
}
```

---

## Transition: Skeleton to Content

Smooth fade prevents jarring content pop-in:

```css
/* In globals.css */
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Apply to content after loading */
[aria-busy="false"] > :not([aria-hidden]) {
  animation: fade-in 0.15s ease-out;
}

@media (prefers-reduced-motion: reduce) {
  [aria-busy="false"] > :not([aria-hidden]) {
    animation: none;
  }
}
```

**Keep it fast:** 150ms max. Longer transitions delay perceived load completion.

---

## Testing Accessibility

### vitest-axe Setup

```bash
cd web && npm install -D vitest-axe
```

```typescript
// web/src/test/setup.ts (add to existing)
import "vitest-axe/extend-expect";
```

**Important:** `vitest-axe` requires `jsdom` environment (not `happy-dom` --- [known bug](https://github.com/chaance/vitest-axe) with `isConnected`).

### Test Examples

```typescript
import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import { SkeletonContainer } from "@/components/ui/skeleton";

describe("SkeletonContainer", () => {
  it("has no accessibility violations in loading state", async () => {
    const { container } = render(
      <SkeletonContainer loading={true} skeleton={<div />} label="test data">
        <p>Content</p>
      </SkeletonContainer>
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("sets aria-busy during loading", () => {
    const { container } = render(
      <SkeletonContainer loading={true} skeleton={<div />}>
        <p>Content</p>
      </SkeletonContainer>
    );
    expect(container.firstChild).toHaveAttribute("aria-busy", "true");
  });

  it("clears aria-busy after loading", () => {
    const { container } = render(
      <SkeletonContainer loading={false} skeleton={<div />}>
        <p>Content</p>
      </SkeletonContainer>
    );
    expect(container.firstChild).toHaveAttribute("aria-busy", "false");
  });

  it("hides skeleton elements from screen readers", () => {
    const { container } = render(
      <SkeletonContainer loading={true} skeleton={<div data-testid="skel" />}>
        <p>Content</p>
      </SkeletonContainer>
    );
    const skeleton = container.querySelector("[aria-hidden='true']");
    expect(skeleton).toBeInTheDocument();
  });
});
```

---

## Gotchas & Limitations

| Issue | Mitigation |
|-------|------------|
| `aria-busy` poorly supported in some AT | Always pair with `sr-only` loading text as fallback |
| NVDA ignores `aria-busy` on `<div>` | Use `role="feed"` or `role="region"` on container if needed |
| Skeleton dimensions don't match content | Audit with Chrome DevTools "Layout Shift Regions" overlay |
| `animate-pulse` causes motion sickness | Always add `motion-reduce:animate-none` |
| `vitest-axe` fails with `happy-dom` | Use `jsdom` in vitest config (CompGraph already does) |
| `loading.tsx` doesn't add `aria-busy` | Wrap `loading.tsx` content in `aria-live` container manually |
| Skeleton shows content flash on fast loads | Add 200ms minimum display time or use `startTransition` |
| Multiple `aria-live` regions on page | Limit to one per visible section; nest inside single container |

---

## WCAG Compliance Checklist

| Criterion | Requirement | Implementation |
|-----------|-------------|----------------|
| 1.3.1 Info & Relationships | Loading state communicated to AT | `aria-busy` + `sr-only` text |
| 2.2.1 Timing Adjustable | No time limits on loading | Skeleton stays until data arrives |
| 2.3.1 Three Flashes | Animation below threshold | `animate-pulse` at 1.5s cycle (0.67Hz) --- well below 3Hz |
| 2.3.3 Animation from Interactions | Respect motion preferences | `motion-reduce:animate-none` |
| 4.1.3 Status Messages | Status communicated without focus | `aria-live="polite"` on container |

---

## Sources

- [More Accessible Skeletons --- Adrian Roselli](https://adrianroselli.com/2020/11/more-accessible-skeletons.html)
- [UI Skeletons and aria-busy CodePen (aardrian)](https://codepen.io/aardrian/pen/yLOoOdY)
- [WAI-ARIA Skeleton Loader (egghead.io)](https://egghead.io/lessons/aria-use-wai-aria-attributes-to-improve-web-accessibility-of-your-skeleton-loader)
- [ARIA: aria-busy attribute (MDN)](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-busy)
- [Semrush Intergalactic Skeleton A11y](https://developer.semrush.com/intergalactic/components/skeleton/skeleton-a11y)
- [vitest-axe GitHub (chaance)](https://github.com/chaance/vitest-axe)
- [Tailwind CSS Animation Docs](https://tailwindcss.com/docs/animation)
- [Next.js loading.js Convention](https://nextjs.org/docs/app/api-reference/file-conventions/loading)
- [Accessible Loading Indicators (DockYard)](https://dockyard.com/blog/2020/03/02/accessible-loading-indicatorswith-no-extra-elements)
