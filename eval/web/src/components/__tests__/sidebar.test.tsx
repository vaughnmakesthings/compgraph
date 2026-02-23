import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, userEvent } from "@/__tests__/helpers/render";

// Controllable pathname for tests
let mockPathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
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

import { Sidebar } from "@/components/sidebar";

describe("Sidebar", () => {
  const defaultProps = { collapsed: false, onToggle: vi.fn() };

  beforeEach(() => {
    mockPathname = "/";
    defaultProps.onToggle = vi.fn();
  });

  describe("Structure", () => {
    it("renders <nav> with aria-label 'Main navigation'", () => {
      render(<Sidebar {...defaultProps} />);
      expect(
        screen.getByRole("navigation", { name: "Main navigation" })
      ).toBeInTheDocument();
    });

    it("renders CG logo mark text", () => {
      render(<Sidebar {...defaultProps} />);
      expect(screen.getByText("CG")).toBeInTheDocument();
    });

    it("renders 'CompGraph' wordmark when expanded", () => {
      render(<Sidebar {...defaultProps} collapsed={false} />);
      expect(screen.getByText("CompGraph")).toBeInTheDocument();
    });

    it("renders all 7 navigation links", () => {
      render(<Sidebar {...defaultProps} />);
      const expectedLabels = [
        "Dashboard",
        "Run Tests",
        "A/B Compare",
        "Leaderboard",
        "Accuracy Review",
        "Run Diff",
        "Settings",
      ];
      for (const label of expectedLabels) {
        expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
      }
    });

    it("renders group headings 'Analysis' and 'Management' when expanded", () => {
      render(<Sidebar {...defaultProps} collapsed={false} />);
      expect(screen.getByText("Analysis")).toBeInTheDocument();
      expect(screen.getByText("Management")).toBeInTheDocument();
    });

    it("does not render group headings when collapsed", () => {
      render(<Sidebar {...defaultProps} collapsed={true} />);
      expect(screen.queryByText("Analysis")).not.toBeInTheDocument();
      expect(screen.queryByText("Management")).not.toBeInTheDocument();
    });

    it("collapse button has aria-label 'Collapse sidebar'", () => {
      render(<Sidebar {...defaultProps} collapsed={false} />);
      expect(
        screen.getByRole("button", { name: "Collapse sidebar" })
      ).toBeInTheDocument();
    });
  });

  describe("Active state detection", () => {
    it("Dashboard is active when pathname is exactly '/'", () => {
      mockPathname = "/";
      render(<Sidebar {...defaultProps} />);
      const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
      expect(dashboardLink).toHaveClass("font-semibold");
    });

    it("Dashboard is NOT active when pathname is '/runs'", () => {
      mockPathname = "/runs";
      render(<Sidebar {...defaultProps} />);
      const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
      expect(dashboardLink).not.toHaveClass("font-semibold");
    });

    it("'Run Tests' is active when pathname is '/runs'", () => {
      mockPathname = "/runs";
      render(<Sidebar {...defaultProps} />);
      const runTestsLink = screen.getByRole("link", { name: "Run Tests" });
      expect(runTestsLink).toHaveClass("font-semibold");
    });

    it("'Run Tests' is active for sub-path '/runs/123'", () => {
      mockPathname = "/runs/123";
      render(<Sidebar {...defaultProps} />);
      const runTestsLink = screen.getByRole("link", { name: "Run Tests" });
      expect(runTestsLink).toHaveClass("font-semibold");
    });

    it("'A/B Compare' is active when pathname starts with '/review'", () => {
      mockPathname = "/review";
      render(<Sidebar {...defaultProps} />);
      const abCompareLink = screen.getByRole("link", { name: "A/B Compare" });
      expect(abCompareLink).toHaveClass("font-semibold");
    });

    it("'Run Diff' is active when pathname starts with '/prompt-diff'", () => {
      mockPathname = "/prompt-diff";
      render(<Sidebar {...defaultProps} />);
      const runDiffLink = screen.getByRole("link", { name: "Run Diff" });
      expect(runDiffLink).toHaveClass("font-semibold");
    });

    it("Settings is active when pathname starts with '/settings'", () => {
      mockPathname = "/settings";
      render(<Sidebar {...defaultProps} />);
      const settingsLink = screen.getByRole("link", { name: "Settings" });
      expect(settingsLink).toHaveClass("font-semibold");
    });
  });

  describe("Collapsed state", () => {
    it("collapse button label changes to 'Expand sidebar' when collapsed", () => {
      render(<Sidebar {...defaultProps} collapsed={true} />);
      expect(
        screen.getByRole("button", { name: "Expand sidebar" })
      ).toBeInTheDocument();
    });

    it("onToggle is called when collapse button is clicked", async () => {
      const onToggle = vi.fn();
      render(<Sidebar collapsed={false} onToggle={onToggle} />);

      const user = userEvent.setup();
      await user.click(
        screen.getByRole("button", { name: "Collapse sidebar" })
      );

      expect(onToggle).toHaveBeenCalledOnce();
    });

    it("aside width is 60px collapsed and 240px expanded", () => {
      const { rerender } = render(
        <Sidebar collapsed={false} onToggle={vi.fn()} />
      );
      const aside = screen.getByRole("complementary");
      expect(aside).toHaveStyle({ width: "240px" });

      rerender(<Sidebar collapsed={true} onToggle={vi.fn()} />);
      expect(aside).toHaveStyle({ width: "60px" });
    });
  });

  describe("Accessibility", () => {
    it("active indicator span has aria-hidden='true'", () => {
      mockPathname = "/";
      render(<Sidebar {...defaultProps} />);
      // The active indicator is a span inside the active link
      const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
      const indicator = dashboardLink.querySelector("span[aria-hidden='true']");
      expect(indicator).toBeInTheDocument();
    });
  });
});
