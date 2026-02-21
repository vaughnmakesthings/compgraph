# Next.js 15 Testing Patterns with Vitest

*Researched: Feb 20, 2026*

## Research Question

What are the recommended patterns for testing Next.js 15 applications (App Router, Server Components, Server Actions, route handlers) with Vitest?

## Key Findings

### 1. Async Server Components Are NOT Supported by Vitest

This is the single most important constraint. From the [official Next.js docs](https://nextjs.org/docs/app/guides/testing/vitest):

> Since `async` Server Components are new to the React ecosystem, Vitest currently does not support them. While you can still run **unit tests** for synchronous Server and Client Components, we recommend using **E2E tests** for `async` components.

**Workaround (React 19 Canary):** Wrap async components in `<Suspense>` and use `findBy*` async queries:

```tsx
import { Suspense } from "react";
import { render, screen } from "@testing-library/react";

test("async server component", async () => {
  render(
    <Suspense fallback={<div>Loading...</div>}>
      <AsyncServerComponent />
    </Suspense>
  );
  expect(await screen.findByTestId("result")).toHaveTextContent("expected");
});
```

**Caveat:** This requires React 19 RC and may behave differently than production SSR rendering. E2E tests remain the official recommendation for async components.

### 2. Official Setup (Next.js + Vitest)

#### Required packages

```bash
pnpm add -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom vite-tsconfig-paths
```

#### vitest.config.mts

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["**/*.{test,spec}.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      thresholds: { lines: 50 },
    },
  },
});
```

#### setup.ts

```ts
import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
```

#### package.json scripts

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  }
}
```

### 3. Testing Pyramid for Next.js 15 App Router

| Layer | Tool | What to Test | Example |
|-------|------|-------------|---------|
| **Unit** | Vitest + RTL | Synchronous components, hooks, utilities, Client Components | Button click handlers, form validation, data formatting |
| **Unit (server)** | Vitest (node env) | Server Actions, route handlers, data transformations | Server action input validation, API response shaping |
| **Integration** | Vitest + RTL | Page-level rendering, component composition | Page renders correct heading, link navigation |
| **E2E** | Playwright | Async Server Components, full user flows, SSR behavior | Login flow, data fetching + display, form submission |

### 4. Mocking Patterns for Next.js APIs

#### next/navigation

```ts
import { vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    pathname: "/",
  }),
  useSearchParams: () => new URLSearchParams("tab=home"),
  usePathname: () => "/",
  redirect: vi.fn(),
  notFound: vi.fn(),
}));
```

#### next/headers (Server-side)

```ts
vi.mock("next/headers", () => ({
  cookies: () => ({
    get: vi.fn().mockReturnValue({ value: "mock-token" }),
    set: vi.fn(),
    delete: vi.fn(),
  }),
  headers: () => new Headers({ "content-type": "application/json" }),
}));
```

#### Server Actions

```ts
// actions/submit.ts
"use server";
export async function submitForm(data: FormData) {
  const name = data.get("name") as string;
  if (!name) throw new Error("Name required");
  // ... persist
}

// actions/submit.test.ts
import { describe, it, expect } from "vitest";
import { submitForm } from "./submit";

// Use node environment for server-side code
// @vitest-environment node

describe("submitForm", () => {
  it("rejects empty name", async () => {
    const formData = new FormData();
    formData.set("name", "");
    await expect(submitForm(formData)).rejects.toThrow("Name required");
  });

  it("accepts valid input", async () => {
    const formData = new FormData();
    formData.set("name", "Test User");
    await expect(submitForm(formData)).resolves.not.toThrow();
  });
});
```

#### Route Handlers

```ts
// app/api/health/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ status: "ok" });
}

// app/api/health/route.test.ts
import { describe, it, expect } from "vitest";
import { GET } from "./route";

describe("GET /api/health", () => {
  it("returns ok status", async () => {
    const response = await GET();
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.status).toBe("ok");
  });
});
```

### 5. Next.js 15 Specific Gotchas

| Gotcha | Detail | Mitigation |
|--------|--------|------------|
| **Async params** | `params` in route handlers is now a Promise in Next.js 15 | Always `await params` before assertions |
| **Async Server Components** | Not supported by Vitest unit tests | Use E2E (Playwright) or Suspense workaround |
| **Server/Client boundary** | `"use client"` / `"use server"` directives affect test environment | Use `@vitest-environment node` for server code |
| **next-test-api-route-handler** | Must be first import in test files | Import before any other modules |
| **React 19 features** | Some testing patterns require React 19 RC | Pin React version consistently |

### 6. File Organization

Recommended for App Router projects:

```
src/
├── app/
│   ├── page.tsx
│   ├── __tests__/
│   │   └── page.test.tsx          # Page integration tests
│   └── api/
│       └── health/
│           ├── route.ts
│           └── route.test.ts      # Co-located route tests
├── components/
│   ├── button.tsx
│   └── button.test.tsx            # Co-located component tests
├── lib/
│   ├── utils.ts
│   └── utils.test.ts              # Co-located utility tests
├── actions/
│   ├── submit.ts
│   └── submit.test.ts             # Co-located action tests
└── test/
    └── setup.ts                   # Global test setup
```

### 7. Testing Architecture Decision

**The recommended split for Next.js 15:**

- **Vitest** → Client Components, hooks, utilities, synchronous Server Components, Server Actions (validation logic), route handlers (unit-level)
- **Playwright** → Async Server Components, full page rendering with data fetching, SSR behavior, user flows across pages, form submissions end-to-end

This isn't a limitation — it's a natural separation. Vitest handles fast, isolated tests. Playwright catches integration issues that only manifest in a real browser with real SSR.

## Relevance to CompGraph

For the compgraph-eval Next.js dashboard and future CompGraph Next.js frontend (M7):

- **Most dashboard components are Client Components** (data tables, charts, filters) → Vitest covers these well
- **Data fetching pages are async Server Components** → Use Playwright for these
- **API route handlers** (if any) → Testable directly with Vitest, no HTTP server needed
- **Server Actions** (form submissions) → Test validation logic with Vitest in node env, full flow with Playwright

## Recommended Actions

- [ ] Set up Vitest with the official config pattern for compgraph-eval Next.js dashboard
- [ ] Use `jsdom` environment (official recommendation) despite happy-dom being faster — Next.js integration is better tested with jsdom
- [ ] Add Playwright for async Server Component and E2E testing
- [ ] Configure dual environments: `jsdom` default for components, `@vitest-environment node` per-file for server code
- [ ] Pin React 19 + Vitest versions to avoid compatibility issues

## Open Questions

- Will Vitest add native async Server Component support? (No timeline from Vitest team as of Feb 2026)
- How does `next-test-api-route-handler` perform with Next.js 15's async params vs direct handler invocation?
- Best pattern for testing Server Components that use `cookies()` or `headers()` from `next/headers`?

## Sources

- [Next.js Official: Testing with Vitest](https://nextjs.org/docs/app/guides/testing/vitest)
- [Next.js Official: Testing Guides](https://nextjs.org/docs/app/guides/testing)
- [Setting up Vitest for Next.js 15 — Wisp CMS](https://www.wisp.blog/blog/setting-up-vitest-for-nextjs-15)
- [Testing Async RSC with RTL and Vitest — Aurora Scharff](https://aurorascharff.no/posts/running-tests-with-rtl-and-vitest-on-internationalized-react-server-components-in-nextjs-app-router/)
- [Test Strategy in Next.js App Router Era — Shinagawa Labs](https://shinagawa-web.com/en/blogs/nextjs-app-router-testing-setup)
- [API Testing with Vitest in Next.js — Medium](https://medium.com/@sanduni.s/api-testing-with-vitest-in-next-js-a-practical-guide-to-mocking-vs-spying-5e5b37677533)
- [next-test-api-route-handler — npm](https://www.npmjs.com/package/next-test-api-route-handler)
- [How to unit test Next.js API route — Nico's Blog](https://www.nico.fyi/blog/how-to-unit-test-nextjs-api-route)
