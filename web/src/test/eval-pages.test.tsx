import { screen } from "@testing-library/react";
import { Suspense } from "react";
import { renderWithQueryClient } from "./test-utils";

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
// Mock the api client react-query options
// ---------------------------------------------------------------------------
vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

// ---------------------------------------------------------------------------
// Import pages under test (after mocks are set up).
// ---------------------------------------------------------------------------
import {
  getRunsApiV1EvalRunsGetOptions,
  listModelsApiV1EvalModelsGetOptions,
} from "@/api-client/@tanstack/react-query.gen";
import EvalRunsPage from "@/app/(app)/eval/runs/page";
import LeaderboardPage from "@/app/(app)/eval/leaderboard/page";
import AccuracyPage from "@/app/(app)/eval/accuracy/page";
import ReviewPage from "@/app/(app)/eval/review/page";
import PromptDiffPage from "@/app/(app)/eval/prompt-diff/page";

// ---------------------------------------------------------------------------
// Eval Runs page
// ---------------------------------------------------------------------------

describe("Eval Runs page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getRunsApiV1EvalRunsGetOptions).mockReturnValue({
      queryKey: ["evalRuns"],
      queryFn: vi.fn().mockResolvedValue([
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
    vi.mocked(listModelsApiV1EvalModelsGetOptions).mockReturnValue({
      queryKey: ["evalModels"],
      queryFn: vi.fn().mockResolvedValue([
        { id: "claude-haiku-4-5-20251001", label: "Haiku 4.5 (fast, cheap)" },
      ]),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
  });

  it("renders the Eval Runs heading", () => {
    renderWithQueryClient(<EvalRunsPage />);
    expect(
      screen.getByRole("heading", { name: /evaluation runs/i }),
    ).toBeInTheDocument();
  });

  it("renders the New Run button", () => {
    renderWithQueryClient(<EvalRunsPage />);
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
    renderWithQueryClient(<LeaderboardPage />);
    expect(
      screen.getByRole("heading", { name: /leaderboard/i }),
    ).toBeInTheDocument();
  });

  it("renders Pass filter buttons", () => {
    renderWithQueryClient(<LeaderboardPage />);
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
    renderWithQueryClient(
      <Suspense fallback={<div>Loading…</div>}>
        <AccuracyPage />
      </Suspense>,
    );
    expect(document.body).toBeInTheDocument();
  });

  it("renders without throwing", () => {
    expect(() => renderWithQueryClient(<AccuracyPage />)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Review page
// ---------------------------------------------------------------------------

describe("Review page", () => {
  it("renders without crashing", () => {
    expect(() => renderWithQueryClient(<ReviewPage />)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Prompt Diff page
// ---------------------------------------------------------------------------

describe("Prompt Diff page", () => {
  it("renders without crashing", () => {
    expect(() => renderWithQueryClient(<PromptDiffPage />)).not.toThrow();
  });
});
