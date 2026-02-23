import { describe, it, expect, vi } from "vitest";
import { renderToString } from "react-dom/server";

// Mock font CSS imports (side-effect-only modules)
vi.mock("@fontsource-variable/sora", () => ({}));
vi.mock("@fontsource-variable/dm-sans", () => ({}));
vi.mock("@fontsource-variable/jetbrains-mono", () => ({}));

// Mock ThemeProvider — pass children through
vi.mock("@/components/theme-provider", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

// Mock TooltipProvider — pass children through
vi.mock("@/components/ui/tooltip", () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

import RootLayout from "@/app/layout";

describe("RootLayout", () => {
  it("HTML output contains lang='en'", () => {
    const html = renderToString(
      <RootLayout>
        <p>Test child</p>
      </RootLayout>
    );
    expect(html).toContain('lang="en"');
  });

  it("skip-nav link has href='#main-content'", () => {
    const html = renderToString(
      <RootLayout>
        <p>Test child</p>
      </RootLayout>
    );
    expect(html).toContain('href="#main-content"');
    expect(html).toContain("Skip to main content");
  });

  it("skip-nav link has sr-only class", () => {
    const html = renderToString(
      <RootLayout>
        <p>Test child</p>
      </RootLayout>
    );
    expect(html).toContain("sr-only");
  });

  it("children are rendered within the provider tree", () => {
    const html = renderToString(
      <RootLayout>
        <p data-testid="child-marker">Hello from child</p>
      </RootLayout>
    );
    expect(html).toContain("Hello from child");
    expect(html).toContain("child-marker");
  });

  it("suppressHydrationWarning is set on the html element", () => {
    // suppressHydrationWarning is a React-only prop stripped by renderToString.
    // Verify by calling the component function directly and inspecting the element tree.
    const tree = RootLayout({ children: <p>Test child</p> });
    // tree is the <html> element returned by the component
    expect(tree.props.suppressHydrationWarning).toBe(true);
  });
});
