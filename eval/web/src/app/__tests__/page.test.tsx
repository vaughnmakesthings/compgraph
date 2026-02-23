import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
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
}));

import DashboardPage from "@/app/page";

describe("DashboardPage", () => {
  it('renders page heading "Dashboard"', async () => {
    render(<DashboardPage />);
    expect(
      await screen.findByRole("heading", { name: /dashboard/i }),
    ).toBeInTheDocument();
  });

  it("shows KPI cards after loading", async () => {
    render(<DashboardPage />);
    expect(await screen.findByText("Total Runs")).toBeInTheDocument();
    expect(screen.getByText("Unique Models")).toBeInTheDocument();
    expect(screen.getByText("Avg Cost")).toBeInTheDocument();
    expect(screen.getByText("Avg Latency")).toBeInTheDocument();
  });

  it("renders recent runs table with model names", async () => {
    render(<DashboardPage />);
    expect(await screen.findByText("deepseek-v3")).toBeInTheDocument();
    expect(screen.getByText("gpt-4.1-mini")).toBeInTheDocument();
  });

  it("shows Cost per Run section", async () => {
    render(<DashboardPage />);
    expect(await screen.findByText("Cost per Run")).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<DashboardPage />);
    // Wait for data to load before running audit
    await screen.findByText("Total Runs");
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
