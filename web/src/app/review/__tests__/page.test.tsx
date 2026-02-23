import React from "react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen, waitFor } from "@/__tests__/helpers/render";
import userEvent from "@testing-library/user-event";

// --- Hoisted mocks ---
const { mockCreateComparison } = vi.hoisted(() => ({
  mockCreateComparison: vi.fn().mockResolvedValue({ id: 99 }),
}));

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/review",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

// --- Mock next/link (required by Sidebar) ---
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

// --- Mock next-themes (required by Header > ThemeToggle) ---
vi.mock("next-themes", () => ({
  useTheme: () => ({
    setTheme: vi.fn(),
    resolvedTheme: "light",
    theme: "light",
  }),
}));

// --- Mock api-client ---
vi.mock("@/lib/api-client", () => ({
  getRuns: vi.fn().mockResolvedValue([
    {
      id: 1,
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
    {
      id: 2,
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
  ]),
  getRunResults: vi.fn().mockImplementation((id: number) =>
    Promise.resolve([
      {
        id: id === 1 ? 101 : 201,
        run_id: id,
        posting_id: "posting-abc",
        raw_response: null,
        parsed_result: JSON.stringify({ role_archetype: "manager" }),
        parse_success: true,
        input_tokens: 100,
        output_tokens: 50,
        cost_usd: 0.001,
        latency_ms: 500,
      },
    ]),
  ),
  getCorpus: vi.fn().mockResolvedValue([
    {
      id: "posting-abc",
      company_slug: "acme",
      title: "Senior Manager",
      location: "Remote",
      full_text: "We are hiring a Senior Manager...",
      reference_pass1: JSON.stringify({ role_archetype: "manager" }),
      reference_pass2: null,
    },
  ]),
  getComparisons: vi.fn().mockResolvedValue([]),
  createComparison: mockCreateComparison,
}));

import ReviewPage from "@/app/review/page";

// Helper: select both runs from dropdowns so comparison UI loads
async function selectBothRuns() {
  const runASelect = (await screen.findByLabelText("Run A")) as HTMLSelectElement;
  const runBSelect = screen.getByLabelText("Run B") as HTMLSelectElement;

  await userEvent.selectOptions(runASelect, "1");
  await userEvent.selectOptions(runBSelect, "2");

  // Wait for comparison content to appear
  await waitFor(() => {
    expect(screen.getByText(/Comparison 1 of/)).toBeInTheDocument();
  });

  // Blur selects so keyboard events are not swallowed
  runASelect.blur();
  runBSelect.blur();
}

describe("ReviewPage", () => {
  it('renders page heading "Review"', async () => {
    render(<ReviewPage />);
    expect(
      await screen.findByRole("heading", { name: /review/i }),
    ).toBeInTheDocument();
  });

  it("shows run selector dropdowns after loading", async () => {
    render(<ReviewPage />);
    // Wait for runs to load so the selectors are enabled
    const runASelect = await screen.findByLabelText("Run A");
    const runBSelect = screen.getByLabelText("Run B");
    expect(runASelect).toBeInTheDocument();
    expect(runBSelect).toBeInTheDocument();
  });

  it("shows empty state text when no runs are selected", async () => {
    render(<ReviewPage />);
    expect(
      await screen.findByText(
        /select two runs above to begin reviewing comparisons/i,
      ),
    ).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<ReviewPage />);
    // Wait for runs to load before running audit
    await screen.findByLabelText("Run A");
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });

  describe("keyboard shortcuts", () => {
    it("pressing A votes 'a'", async () => {
      render(<ReviewPage />);
      await selectBothRuns();

      mockCreateComparison.mockClear();
      await userEvent.keyboard("a");

      await waitFor(() => {
        expect(mockCreateComparison).toHaveBeenCalledWith(
          expect.objectContaining({ winner: "a" }),
        );
      });
    });

    it("pressing B votes 'b'", async () => {
      render(<ReviewPage />);
      await selectBothRuns();

      mockCreateComparison.mockClear();
      await userEvent.keyboard("b");

      await waitFor(() => {
        expect(mockCreateComparison).toHaveBeenCalledWith(
          expect.objectContaining({ winner: "b" }),
        );
      });
    });

    it("pressing T votes 'tie'", async () => {
      render(<ReviewPage />);
      await selectBothRuns();

      mockCreateComparison.mockClear();
      await userEvent.keyboard("t");

      await waitFor(() => {
        expect(mockCreateComparison).toHaveBeenCalledWith(
          expect.objectContaining({ winner: "tie" }),
        );
      });
    });

    it("pressing X votes 'both_bad'", async () => {
      render(<ReviewPage />);
      await selectBothRuns();

      mockCreateComparison.mockClear();
      await userEvent.keyboard("x");

      await waitFor(() => {
        expect(mockCreateComparison).toHaveBeenCalledWith(
          expect.objectContaining({ winner: "both_bad" }),
        );
      });
    });

    it("shows hotkey legend after runs are selected", async () => {
      render(<ReviewPage />);
      await selectBothRuns();

      expect(screen.getByText("A Better")).toBeInTheDocument();
      expect(screen.getByText("B Better")).toBeInTheDocument();
      // "Prev" and "Next" appear both in nav buttons and in kbd legend
      expect(screen.getAllByText("Prev").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Next").length).toBeGreaterThanOrEqual(1);
    });
  });
});
