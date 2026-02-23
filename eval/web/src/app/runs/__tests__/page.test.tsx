import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/runs",
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
  getModels: vi
    .fn()
    .mockResolvedValue({
      "haiku-3.5": "openrouter/...",
      "deepseek-v3": "openrouter/...",
    }),
  getPrompts: vi.fn().mockResolvedValue(["pass1_v1"]),
  createRun: vi.fn(),
  getProgress: vi.fn(),
}));

import RunsPage from "@/app/runs/page";

describe("RunsPage", () => {
  it('renders page heading "Run Tests"', async () => {
    render(<RunsPage />);
    expect(
      await screen.findByRole("heading", { name: /run tests/i }),
    ).toBeInTheDocument();
  });

  it("shows model names in table after loading", async () => {
    render(<RunsPage />);
    expect(await screen.findByText("deepseek-v3")).toBeInTheDocument();
    expect(screen.getByText("gpt-4.1-mini")).toBeInTheDocument();
  });

  it('has a "New Run" button', async () => {
    render(<RunsPage />);
    const button = await screen.findByRole("button", { name: /new run/i });
    expect(button).toBeInTheDocument();
  });

  it("renders run rows in the table", async () => {
    render(<RunsPage />);
    // Wait for the table to appear with data
    const table = await screen.findByRole("table", {
      name: "Evaluation runs",
    });
    const tbody = table.querySelector("tbody")!;
    const rows = tbody.querySelectorAll("tr");
    expect(rows).toHaveLength(2);
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<RunsPage />);
    // Wait for data to load before running audit
    await screen.findByText("deepseek-v3");
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
