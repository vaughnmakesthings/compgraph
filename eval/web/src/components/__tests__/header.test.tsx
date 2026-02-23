import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";

// Mock next-themes (required by ThemeToggle child component)
vi.mock("next-themes", () => ({
  useTheme: () => ({
    setTheme: vi.fn(),
    resolvedTheme: "light",
    theme: "light",
  }),
}));

import { Header } from "@/components/header";

describe("Header", () => {
  it("renders <header> with role='banner'", () => {
    render(<Header title="Test" />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("renders title text", () => {
    render(<Header title="Evaluation Dashboard" />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Evaluation Dashboard" })
    ).toBeInTheDocument();
  });

  it("renders subtitle and breadcrumb separator when subtitle is provided", () => {
    render(<Header title="Dashboard" subtitle="Overview" />);
    expect(screen.getByText("Overview")).toBeInTheDocument();

    // The separator "/" should be aria-hidden
    const separator = screen.getByText("/");
    expect(separator).toHaveAttribute("aria-hidden", "true");
  });

  it("omits subtitle and separator when subtitle is not provided", () => {
    render(<Header title="Dashboard" />);
    expect(screen.queryByText("/")).not.toBeInTheDocument();
  });

  it("contains ThemeToggle button", () => {
    render(<Header title="Dashboard" />);
    expect(
      screen.getByRole("button", { name: "Toggle theme" })
    ).toBeInTheDocument();
  });

  it("renders avatar with role='img' and aria-label", () => {
    render(<Header title="Dashboard" />);
    const avatar = screen.getByRole("img", { name: "Signed in as VM" });
    expect(avatar).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<Header title="Dashboard" subtitle="Sub" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
