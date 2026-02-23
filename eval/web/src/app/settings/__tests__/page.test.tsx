import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
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

import SettingsPage from "@/app/settings/page";

describe("SettingsPage", () => {
  it("renders page heading", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: "Settings" })
    ).toBeInTheDocument();
  });

  it("shows read-only notice", () => {
    render(<SettingsPage />);
    expect(
      screen.getByText("Read-only during evaluation phase")
    ).toBeInTheDocument();
  });

  it('displays API Provider section with "OpenRouter"', () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: "API Provider" })
    ).toBeInTheDocument();
    expect(screen.getByText("OpenRouter")).toBeInTheDocument();
  });

  it('displays Models section with "haiku-3.5" and "sonnet-4"', () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: "Models" })
    ).toBeInTheDocument();
    expect(screen.getByText("haiku-3.5")).toBeInTheDocument();
    expect(screen.getByText("sonnet-4")).toBeInTheDocument();
  });

  it('displays Prompt Versions with "pass1_v1" and "pass2_v1"', () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: "Prompt Versions" })
    ).toBeInTheDocument();
    expect(screen.getByText("pass1_v1")).toBeInTheDocument();
    expect(screen.getByText("pass2_v1")).toBeInTheDocument();
  });

  it('displays Defaults with "5" and "50"', () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: "Defaults" })
    ).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<SettingsPage />);
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });
});
