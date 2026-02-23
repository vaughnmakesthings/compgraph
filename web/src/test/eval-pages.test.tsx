import { render, screen } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mock next/navigation — required for any component using useSearchParams,
// useRouter, or usePathname.
// ---------------------------------------------------------------------------
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (_key: string) => null,
    toString: () => "",
  }),
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
  usePathname: () => "/eval/runs",
  redirect: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Mock next/link — render plain <a> elements in jsdom.
// ---------------------------------------------------------------------------
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    style,
  }: {
    href: string;
    children: React.ReactNode;
    style?: React.CSSProperties;
  }) => (
    <a href={href} style={style}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Mock the api client. All data must be inline — vi.mock factories are hoisted
// above variable declarations so external variables cannot be referenced.
// ---------------------------------------------------------------------------
vi.mock("@/lib/api-client", () => ({
  api: {
    listEvalRuns: vi.fn().mockResolvedValue([
      {
        id: "run-abc123",
        pass_number: 1,
        model: "claude-haiku-4-5",
        prompt_version: "pass1_v1",
        status: "completed",
        created_at: "2026-02-22T10:00:00Z",
        completed_at: "2026-02-22T10:05:00Z",
        total_items: 100,
        completed_items: 100,
      },
    ]),
    createEvalRun: vi.fn().mockResolvedValue({
      run_id: "new-run",
      tracking_id: 1,
    }),
  },
}));

// ---------------------------------------------------------------------------
// Import pages under test (after mocks are set up).
// ---------------------------------------------------------------------------
import EvalRunsPage from "@/app/eval/runs/page";

// ---------------------------------------------------------------------------
// Eval Runs page
// ---------------------------------------------------------------------------

describe("Eval Runs page", () => {
  it("renders the Eval Runs heading", () => {
    render(<EvalRunsPage />);
    expect(
      screen.getByRole("heading", { name: /eval runs/i }),
    ).toBeInTheDocument();
  });

  it("renders the New Run button", () => {
    render(<EvalRunsPage />);
    expect(
      screen.getByRole("button", { name: /new run/i }),
    ).toBeInTheDocument();
  });
});
