import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen, waitFor } from "@/__tests__/helpers/render";

vi.mock("next/navigation", () => ({
  usePathname: () => "/leaderboard",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next-themes", () => ({
  useTheme: () => ({
    setTheme: vi.fn(),
    resolvedTheme: "light",
    theme: "light",
  }),
}));

// --- Mock api-client ---
vi.mock("@/lib/api-client", () => ({
  getLeaderboardData: vi.fn().mockResolvedValue({
    runs: [
      {
        id: 1,
        created_at: "2026-02-18T00:00:00",
        pass_number: 1,
        model: "gpt-4.1-mini",
        prompt_version: "pass1_v1",
        corpus_size: 50,
        total_input_tokens: 800,
        total_output_tokens: 400,
        total_cost_usd: 0.027,
        total_duration_ms: 85000,
      },
      {
        id: 2,
        created_at: "2026-02-18T00:00:00",
        pass_number: 1,
        model: "deepseek-v3",
        prompt_version: "pass1_v1",
        corpus_size: 50,
        total_input_tokens: 1000,
        total_output_tokens: 500,
        total_cost_usd: 0.054,
        total_duration_ms: 72000,
      },
    ],
    elo: {
      "gpt-4.1-mini/pass1_v1": 1580,
      "deepseek-v3/pass1_v1": 1490,
    },
    comparisons: [],
    field_accuracy: { "1": {}, "2": {} },
    results: { "1": [], "2": [] },
  }),
}));

import LeaderboardPage from "@/app/leaderboard/page";

describe("LeaderboardPage", () => {
  it("renders page heading", () => {
    render(<LeaderboardPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Leaderboard" }),
    ).toBeInTheDocument();
  });

  it("shows Elo Rankings section heading after loading", async () => {
    render(<LeaderboardPage />);
    const heading = await screen.findByText("Elo Rankings");
    expect(heading).toBeInTheDocument();
  });

  it("shows pass filter buttons", () => {
    render(<LeaderboardPage />);
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pass 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pass 2" })).toBeInTheDocument();
  });

  it("shows model names in table after loading", async () => {
    render(<LeaderboardPage />);
    // Model names appear in both the filter buttons and the table rows
    await screen.findAllByText("gpt-4.1-mini");
    expect(screen.getAllByText("gpt-4.1-mini").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("deepseek-v3").length).toBeGreaterThanOrEqual(1);
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<LeaderboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Elo Rankings")).toBeInTheDocument();
    });
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
