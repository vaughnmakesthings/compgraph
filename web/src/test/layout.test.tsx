import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Sidebar } from "../components/layout/sidebar";
import { Header } from "../components/layout/header";
import Shell from "../components/layout/shell";

const mockUsePathname = vi.fn(() => "/");

vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// Stub localStorage — jsdom's localstorage may not be available depending on
// the vitest jsdom build. Using a minimal in-memory stub is reliable.
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value;
  },
  removeItem: (key: string) => {
    delete localStorageStore[key];
  },
  clear: () => {
    for (const key of Object.keys(localStorageStore)) {
      delete localStorageStore[key];
    }
  },
};

Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  writable: true,
});

beforeEach(() => {
  localStorageMock.clear();
  mockUsePathname.mockReturnValue("/");
});

describe("Sidebar", () => {
  it("renders all nav items", () => {
    render(<Sidebar />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Competitors")).toBeInTheDocument();
    expect(screen.getByText("Market Overview")).toBeInTheDocument();
    expect(screen.getByText("Job Feed")).toBeInTheDocument();
    expect(screen.getByText("Eval Tool")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("has accessible navigation landmark", () => {
    render(<Sidebar />);
    expect(
      screen.getByRole("navigation", { name: /main navigation/i })
    ).toBeInTheDocument();
  });

  it("marks the active Dashboard link with aria-current when on /", () => {
    mockUsePathname.mockReturnValue("/");
    render(<Sidebar />);
    const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });

  it("does not mark Dashboard as active when on /competitors", () => {
    mockUsePathname.mockReturnValue("/competitors");
    render(<Sidebar />);
    const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
    expect(dashboardLink).not.toHaveAttribute("aria-current", "page");
  });

  it("marks the Competitors button as expanded by default", () => {
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    expect(competitorsButton).toHaveAttribute("aria-expanded", "true");
  });

  it("collapses a parent nav item when clicked", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    await user.click(competitorsButton);
    expect(competitorsButton).toHaveAttribute("aria-expanded", "false");
  });

  it("re-expands a collapsed parent nav item when clicked again", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    await user.click(competitorsButton);
    await user.click(competitorsButton);
    expect(competitorsButton).toHaveAttribute("aria-expanded", "true");
  });

  it("persists collapse state to localStorage", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    await user.click(competitorsButton);

    const stored = JSON.parse(
      localStorageMock.getItem("cg-sidebar-state") ?? "{}"
    ) as Record<string, boolean>;
    expect(stored["competitors"]).toBe(false);
  });

  it("restores collapse state from localStorage on mount", async () => {
    localStorageMock.setItem(
      "cg-sidebar-state",
      JSON.stringify({ competitors: false })
    );
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    await waitFor(() => {
      expect(competitorsButton).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("toggle buttons have aria-controls pointing to their collapsible region", () => {
    render(<Sidebar />);
    const competitorsButton = screen.getByRole("button", {
      name: /competitors/i,
    });
    expect(competitorsButton).toHaveAttribute("aria-controls", "nav-sub-competitors");
  });
});

describe("Header", () => {
  it("renders the CompGraph wordmark", () => {
    render(<Header />);
    expect(screen.getByText("CompGraph")).toBeInTheDocument();
  });

  it("renders the API connection status label", () => {
    render(<Header />);
    expect(screen.getByText(/api connected/i)).toBeInTheDocument();
  });

  it("renders as a header landmark", () => {
    render(<Header />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });
});

describe("Shell", () => {
  it("renders sidebar and header together", () => {
    render(
      <Shell>
        <div>page content</div>
      </Shell>
    );
    expect(
      screen.getByRole("navigation", { name: /main navigation/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("renders children inside main", () => {
    render(
      <Shell>
        <div>page content</div>
      </Shell>
    );
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByText("page content")).toBeInTheDocument();
  });

  it("renders the CompGraph wordmark via the header", () => {
    render(
      <Shell>
        <div>content</div>
      </Shell>
    );
    expect(screen.getByText("CompGraph")).toBeInTheDocument();
  });
});
