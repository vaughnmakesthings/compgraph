# Gen-Test (Frontend)

Generate Vitest + React Testing Library tests for a given component or module, following CompGraph patterns.

**Invocation:** Both — Claude or user can invoke `/gen-test <path>` to generate tests for a file.

## When to Use

- Adding tests for a new component or page
- Expanding coverage for an existing module
- Creating api-client tests for new API methods
- Following established patterns from `web/src/test/`

## CompGraph Test Patterns

### API Client Tests (`api-client.test.ts`)

- Mock `global.fetch` with `vi.fn()`
- Use `vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => data })`
- Assert URL construction, query params, and response handling
- Test error paths (non-ok responses, network errors)
- `beforeEach` / `afterEach` for mock setup/teardown

### Page Tests (`pages.test.tsx`)

- Use `@testing-library/react` — `render`, `screen`, `waitFor`, `userEvent`
- Mock API via `vi.mocked(fetch)` or module mocks
- Test loading states, error states, and success rendering
- Use `vi.hoisted()` for mock data shared across tests

### Component Tests

- Render with required props
- Query by role, label, or test-id
- Assert user-visible behavior, not implementation details
- Follow `web/src/test/setup.ts` (jsdom, @testing-library/jest-dom)

### Coverage Thresholds

- Statements: 50%
- Functions: 50%
- Lines: 50%
- Branches: 30%

## Usage

```
/gen-test web/src/app/dashboard/page.tsx
/gen-test web/src/components/SomeComponent.tsx
/gen-test web/src/lib/api-client.ts  # for new API methods
```

## Output

Generates a test file at the corresponding path:

- `web/src/app/dashboard/page.tsx` → `web/src/test/pages.test.tsx` (append or create section)
- `web/src/components/X.tsx` → `web/src/components/X.test.tsx` or `web/src/test/components.test.tsx`
- `web/src/lib/api-client.ts` → `web/src/test/api-client.test.ts` (append describe block)

## Implementation Notes

When generating tests:

1. Read existing tests in `web/src/test/` to match structure
2. Use `describe`/`it` blocks with clear names
3. Mock external dependencies (fetch, router, etc.)
4. Prefer `screen.getByRole`, `getByLabelText` over `getByTestId`
5. Use `waitFor` for async assertions
6. Keep tests focused — one behavior per `it`
