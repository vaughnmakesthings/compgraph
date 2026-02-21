# Vitest Infrastructure Best Practices & Practitioner Feedback

*Researched: Feb 20, 2026*

## Research Question

What are current best practices for Vitest test infrastructure setup, and what do practitioners report about real-world usage patterns, pain points, and recommendations?

## Key Findings

### 1. Vitest 4.0 Is Production-Ready (Released Oct 2025)

- **Browser Mode stabilized** — no longer experimental. Requires separate provider packages (`@vitest/browser-playwright`, `@vitest/browser-webdriverio`)
- **Visual regression testing** — built-in `toMatchScreenshot()` assertion for UI comparison
- **Playwright trace support** — `--browser.trace=on` for debugging test failures
- **Reporter changes** — `basic` reporter removed; use `default` with `summary: false`
- **Automated Jest migration** — `npx codemod jest/vitest` handles most API transformations

### 2. Infrastructure Best Practices

| Practice | Detail |
|----------|--------|
| **File organization** | Tests co-located with source: `[module].test.ts` or `[module].spec.ts` |
| **Naming** | `*.test.ts` for unit, `*.spec.ts` for integration, `*.e2e.ts` for end-to-end |
| **Structure** | AAA pattern (Arrange/Act/Assert), `describe` blocks for grouping |
| **Performance** | HMR-based watch mode reruns only affected tests via Vite's module graph |
| **TypeScript/ESM** | Works out-of-box — no plugins or special config needed |
| **Coverage** | Use `@vitest/coverage-v8` (default) or `@vitest/coverage-istanbul` |
| **CI sharding** | `--shard=1/3` for parallel CI runs across matrix jobs |

### 3. Recommended Config Patterns

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,                    // jest-compatible global API
    environment: "jsdom",             // or 'happy-dom' for speed
    include: ["src/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      thresholds: { lines: 80 },     // enforce coverage minimums
    },
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

### 4. Practitioner Pain Points (Real Issues)

| Issue | Severity | Detail |
|-------|----------|--------|
| **V8 coverage regression** | Medium | Vitest 4 + V8 coverage tracks fewer lines than 3.2.4 for React TSX/JSX ([#9457](https://github.com/vitest-dev/vitest/issues/9457)) |
| **jsdom compatibility** | Medium | Latest jsdom breaks some Vitest 4 tests ([#9279](https://github.com/vitest-dev/vitest/issues/9279)) |
| **Patch-version breaking** | Low | 4.0.12 → 4.0.13 broke `waitFor` tests ([#9148](https://github.com/vitest-dev/vitest/issues/9148)) |
| **Browser Mode workspace** | Low | Mixed Node + Browser workspace configs broken since 3.1.3 ([#7964](https://github.com/vitest-dev/vitest/issues/7964)) |
| **Benchmarking** | Low | Still experimental, can't run alongside tests |

### 5. Vitest vs Jest (2026 Landscape)

| Dimension | Vitest | Jest |
|-----------|--------|------|
| **Speed** | 2-10x faster (Vite pipeline, HMR) | Slower cold starts, broader re-runs |
| **ESM/TS** | Native, zero config | Requires babel/ts-jest transforms |
| **Config** | Shares `vite.config.ts` | Separate `jest.config.ts` |
| **Watch mode** | File-system watcher, macOS-optimized | Slower, broader invalidation |
| **Browser testing** | Built-in (Playwright/WebdriverIO) | Requires separate setup |
| **Ecosystem** | Growing, most Jest patterns map 1:1 | Mature, vast plugin ecosystem |
| **Migration** | Automated codemods available | N/A |

**Consensus:** If using Vite, Vitest is the clear default. For non-Vite projects, Vitest still wins on speed and DX but requires evaluating plugin compatibility.

## Relevance to CompGraph

CompGraph's frontend roadmap (M7) targets Next.js. For the compgraph-eval Next.js dashboard already in development:

- **Vitest 4** is the recommended test runner — native ESM/TS, co-located tests, fast watch mode
- **Pin exact versions** to avoid patch-level regressions (e.g., the 4.0.12→4.0.13 issue)
- **Use `happy-dom`** over `jsdom` if no jsdom-specific APIs needed — avoids the jsdom compatibility issue and is faster
- **Coverage threshold** can mirror CompGraph Python's pattern (50%+ enforced via CI)
- **Browser Mode** relevant for testing Streamlit-replacement UI components in real browsers

## Recommended Actions

- [ ] Use Vitest 4.x for compgraph-eval Next.js dashboard test infrastructure
- [ ] Pin Vitest to exact version (`"vitest": "4.0.12"`) until coverage regression is resolved
- [ ] Configure `happy-dom` environment for unit tests, Playwright for component/e2e
- [ ] Set up CI sharding for parallel test runs as test suite grows
- [ ] Add `@vitest/coverage-v8` with threshold enforcement in CI

## Open Questions

- How does Vitest 4 Browser Mode interact with Next.js App Router SSR components? (May need separate node/browser test configs)
- What's the recommended approach for testing Next.js Server Components with Vitest? (Server-side rendering tests may need `environment: 'node'`)

## Sources

- [Vitest 4.0 Announcement](https://vitest.dev/blog/vitest-4)
- [Vitest 4 Adoption Guide — LogRocket](https://blog.logrocket.com/vitest-adoption-guide/)
- [Vitest 2026: Standard for Modern JS Testing](https://jeffbruchado.com.br/en/blog/vitest-2026-standard-modern-javascript-testing)
- [Vitest Best Practices — ProjectRules](https://www.projectrules.ai/rules/vitest)
- [Jest vs Vitest 2025 — Medium](https://medium.com/@ruverd/jest-vs-vitest-which-test-runner-should-you-use-in-2025-5c85e4f2bda9)
- [Vitest Configuration Docs](https://vitest.dev/config/)
