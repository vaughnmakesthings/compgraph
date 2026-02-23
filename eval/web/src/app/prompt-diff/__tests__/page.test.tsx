import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen, waitFor } from "@/__tests__/helpers/render";

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/prompt-diff",
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
  getRunResults: vi.fn().mockResolvedValue([]),
}));

import PromptDiffPage from "@/app/prompt-diff/page";

describe("PromptDiffPage", () => {
  it('renders page heading "Run Diff"', () => {
    render(<PromptDiffPage />);
    expect(
      screen.getByRole("heading", { name: "Run Diff" }),
    ).toBeInTheDocument();
  });

  it("shows baseline and candidate labels after loading", async () => {
    render(<PromptDiffPage />);
    const baselineLabel = await screen.findByText("Baseline Run");
    expect(baselineLabel).toBeInTheDocument();
    expect(screen.getByText("Candidate Run")).toBeInTheDocument();
  });

  it("shows run selector dropdowns", async () => {
    render(<PromptDiffPage />);
    const baselineSelect = await screen.findByLabelText("Baseline Run");
    const candidateSelect = screen.getByLabelText("Candidate Run");
    expect(baselineSelect.tagName).toBe("SELECT");
    expect(candidateSelect.tagName).toBe("SELECT");
  });

  it("shows empty state when no runs selected", async () => {
    render(<PromptDiffPage />);
    const emptyMsg = await screen.findByText(
      /select both a baseline and candidate run to compare/i,
    );
    expect(emptyMsg).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<PromptDiffPage />);
    await waitFor(() => {
      expect(screen.getByLabelText("Baseline Run")).toBeInTheDocument();
    });
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
