import { describe, it, expect, vi, beforeEach } from "vitest";
import { axe } from "vitest-axe";
import { render, screen, userEvent } from "@/__tests__/helpers/render";

const mockSetTheme = vi.fn();
let mockResolvedTheme = "light";

vi.mock("next-themes", () => ({
  useTheme: () => ({
    setTheme: mockSetTheme,
    resolvedTheme: mockResolvedTheme,
    theme: mockResolvedTheme,
  }),
}));

import { ThemeToggle } from "@/components/theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    mockResolvedTheme = "light";
    mockSetTheme.mockClear();
  });

  it("renders button with accessible name 'Toggle theme'", () => {
    render(<ThemeToggle />);
    expect(
      screen.getByRole("button", { name: "Toggle theme" })
    ).toBeInTheDocument();
  });

  it("calls setTheme('dark') when clicked in light mode", async () => {
    mockResolvedTheme = "light";
    render(<ThemeToggle />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Toggle theme" }));

    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("calls setTheme('light') when clicked in dark mode", async () => {
    mockResolvedTheme = "dark";
    render(<ThemeToggle />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Toggle theme" }));

    expect(mockSetTheme).toHaveBeenCalledWith("light");
  });

  it("contains sr-only text 'Toggle theme'", () => {
    render(<ThemeToggle />);
    const srOnly = screen.getByText("Toggle theme");
    expect(srOnly).toHaveClass("sr-only");
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<ThemeToggle />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
