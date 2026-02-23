import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@/__tests__/helpers/render";

// --- Mock next/navigation (required by Sidebar) ---
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

import { AppShell } from "@/components/app-shell";
import { SIDEBAR_WIDTH, SIDEBAR_WIDTH_COLLAPSED } from "@/lib/constants";

// Helper: create a real Storage-like object for localStorage mocking
function createMockStorage(data: Record<string, string> = {}): Storage {
  const store: Record<string, string> = { ...data };
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const key of Object.keys(store)) delete store[key];
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
}

/** Find the content div (the one with paddingLeft style, sibling of <main>) */
function getContentArea(container: HTMLElement): HTMLElement {
  // The content area div wraps Header + main, and has paddingLeft style
  const main = container.querySelector("main#main-content")!;
  return main.parentElement as HTMLElement;
}

describe("AppShell", () => {
  beforeEach(() => {
    mockPathname = "/";
  });

  describe("Rendering", () => {
    it("renders Sidebar with main navigation", () => {
      render(
        <AppShell title="Test Title">
          <p>Content</p>
        </AppShell>
      );
      expect(
        screen.getByRole("navigation", { name: "Main navigation" })
      ).toBeInTheDocument();
    });

    it("main element has id='main-content'", () => {
      render(
        <AppShell title="Test Title">
          <p>Content</p>
        </AppShell>
      );
      const main = screen.getByRole("main");
      expect(main).toHaveAttribute("id", "main-content");
    });

    it("passes title and subtitle to Header", () => {
      render(
        <AppShell title="Dashboard" subtitle="Overview">
          <p>Content</p>
        </AppShell>
      );
      expect(
        screen.getByRole("heading", { level: 1, name: "Dashboard" })
      ).toBeInTheDocument();
      expect(screen.getByText("Overview")).toBeInTheDocument();
    });
  });

  describe("Hydration guard", () => {
    it("after hydration, aria-busy is not 'true'", () => {
      const { container } = render(
        <AppShell title="Test">
          <p>Content</p>
        </AppShell>
      );
      // After useEffect fires, hydrated=true so aria-busy should be false
      const shell = container.firstElementChild as HTMLElement;
      expect(shell).not.toHaveAttribute("aria-busy", "true");
    });

    it("after hydration, opacity-0 class is not present", () => {
      const { container } = render(
        <AppShell title="Test">
          <p>Content</p>
        </AppShell>
      );
      const shell = container.firstElementChild as HTMLElement;
      expect(shell.className).not.toContain("opacity-0");
    });
  });

  describe("localStorage integration", () => {
    it("reads 'sidebar-collapsed' from localStorage on mount", () => {
      const mockStorage = createMockStorage({
        "sidebar-collapsed": "true",
      });
      vi.stubGlobal("localStorage", mockStorage);

      const { container } = render(
        <AppShell title="Test">
          <p>Content</p>
        </AppShell>
      );

      const contentArea = getContentArea(container);
      expect(contentArea.style.paddingLeft).toBe(
        `${SIDEBAR_WIDTH_COLLAPSED}px`
      );

      vi.unstubAllGlobals();
    });

    it("defaults to expanded when localStorage is empty", () => {
      const mockStorage = createMockStorage();
      vi.stubGlobal("localStorage", mockStorage);

      const { container } = render(
        <AppShell title="Test">
          <p>Content</p>
        </AppShell>
      );

      const contentArea = getContentArea(container);
      expect(contentArea.style.paddingLeft).toBe(`${SIDEBAR_WIDTH}px`);

      vi.unstubAllGlobals();
    });

    it("handles localStorage errors gracefully", () => {
      const throwingStorage = createMockStorage();
      throwingStorage.getItem = () => {
        throw new DOMException("SecurityError");
      };
      vi.stubGlobal("localStorage", throwingStorage);

      const { container } = render(
        <AppShell title="Test">
          <p>Content</p>
        </AppShell>
      );

      // Should still render expanded (default) despite localStorage error
      const contentArea = getContentArea(container);
      expect(contentArea.style.paddingLeft).toBe(`${SIDEBAR_WIDTH}px`);

      vi.unstubAllGlobals();
    });
  });
});
