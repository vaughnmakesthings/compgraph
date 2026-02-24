import { render, screen } from "@testing-library/react";
import { Suspense } from "react";

// ---------------------------------------------------------------------------
// Mock next/navigation — required for any component using useSearchParams,
// useRouter, or usePathname.
// ---------------------------------------------------------------------------
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: () => null,
    toString: () => "",
  }),
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
  usePathname: () => "/eval/review",
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
    getEvalModels: vi.fn().mockResolvedValue([
      { id: "claude-haiku-4-5-20251001", label: "Haiku 4.5 (fast, cheap)" },
      { id: "claude-sonnet-4-5-20251001", label: "Sonnet 4.5 (balanced)" },
      { id: "claude-sonnet-4-6", label: "Sonnet 4.6 (latest)" },
      { id: "claude-opus-4-6", label: "Opus 4.6 (highest quality)" },
    ]),
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
    getEvalResults: vi.fn().mockResolvedValue([]),
    getEvalLeaderboard: vi.fn().mockResolvedValue({
      runs: [
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
      ],
      elo: { "claude-haiku-4-5/pass1_v1": 1500 },
      comparisons: [],
      field_accuracy: {},
    }),
    listComparisons: vi.fn().mockResolvedValue([]),
    recordComparison: vi.fn().mockResolvedValue({ id: "cmp-1" }),
    upsertFieldReview: vi.fn().mockResolvedValue({ id: "rev-1" }),
    getEvalCorpus: vi.fn().mockResolvedValue([
      { id: "posting-1", title: "Field Rep - Miami", content: "..." },
    ]),
  },
}));

// ---------------------------------------------------------------------------
// Import pages under test (after mocks are set up).
// ---------------------------------------------------------------------------
import EvalRunsPage from "@/app/eval/runs/page";
import LeaderboardPage from "@/app/eval/leaderboard/page";
import AccuracyPage from "@/app/eval/accuracy/page";
import ReviewPage from "@/app/eval/review/page";
import PromptDiffPage from "@/app/eval/prompt-diff/page";

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

// ---------------------------------------------------------------------------
// Leaderboard page
// ---------------------------------------------------------------------------

describe("Leaderboard page", () => {
  it("renders the Leaderboard heading", () => {
    render(<LeaderboardPage />);
    expect(
      screen.getByRole("heading", { name: /leaderboard/i }),
    ).toBeInTheDocument();
  });

  it("renders Pass filter buttons", () => {
    render(<LeaderboardPage />);
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Pass 1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Pass 2" }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Accuracy page — renders Suspense boundary (useSearchParams requirement)
// ---------------------------------------------------------------------------

describe("Accuracy page", () => {
  it("renders the Suspense fallback without crashing", () => {
    render(
      <Suspense fallback={<div>Loading…</div>}>
        <AccuracyPage />
      </Suspense>,
    );
    expect(document.body).toBeInTheDocument();
  });

  it("renders without throwing", () => {
    expect(() => render(<AccuracyPage />)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Review page
// ---------------------------------------------------------------------------

describe("Review page", () => {
  it("renders without crashing", () => {
    expect(() => render(<ReviewPage />)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Prompt Diff page
// ---------------------------------------------------------------------------

describe("Prompt Diff page", () => {
  it("renders without crashing", () => {
    expect(() => render(<PromptDiffPage />)).not.toThrow();
  });
});
