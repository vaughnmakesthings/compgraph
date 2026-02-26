import { render } from "@testing-library/react";

const mockRole = vi.fn(() => "admin");
const mockLoading = vi.fn(() => false);

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    session: { access_token: "t" },
    user: { email: "test@example.com" },
    role: mockRole(),
    loading: mockLoading(),
    signOut: vi.fn(),
  }),
}));

const mockRedirect = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => {
    mockRedirect(...args);
  },
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/settings",
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

vi.mock("@/lib/api-client", () => ({
  api: {
    getScrapeHistory: vi.fn().mockResolvedValue([]),
    getEnrichmentHistory: vi.fn().mockResolvedValue([]),
    getPipelineRuns: vi.fn().mockResolvedValue({ scrape_runs: [], enrichment_runs: [] }),
    getSchedulerStatus: vi.fn().mockResolvedValue({
      enabled: true,
      schedules: [],
      last_pipeline_finished_at: null,
      last_pipeline_success: null,
      missed_run: false,
    }),
    getScrapeStatus: vi.fn().mockResolvedValue({ status: "idle", run_id: null, company: null }),
    getEnrichStatus: vi.fn().mockResolvedValue({ status: "idle", run_id: null }),
    health: vi.fn().mockResolvedValue({ status: "ok", version: "1.0.0" }),
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@headlessui/react", () => ({
  Dialog: ({ open, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) => {
    if (!open) return null;
    return <div role="dialog">{typeof children === "function" ? null : children}</div>;
  },
  DialogPanel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children, as: Component = "h3", ...props }: { children: React.ReactNode; as?: React.ElementType; className?: string }) => {
    const Tag = Component;
    return <Tag {...props}>{children}</Tag>;
  },
  DialogBackdrop: () => null,
}));

vi.mock("@tremor/react", () => ({
  Dialog: ({ open, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) => {
    if (!open) return null;
    return <div role="dialog">{children}</div>;
  },
  DialogPanel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import SettingsPage from "@/app/(app)/settings/page";

describe("Settings page admin guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRole.mockReturnValue("admin");
    mockLoading.mockReturnValue(false);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "ok", version: "1.0.0" }),
      }),
    );
  });

  it("redirects viewer-role users to /403", () => {
    mockRole.mockReturnValue("viewer");
    render(<SettingsPage />);
    expect(mockRedirect).toHaveBeenCalledWith("/403");
  });

  it("redirects user-role users to /403", () => {
    mockRole.mockReturnValue("user");
    render(<SettingsPage />);
    expect(mockRedirect).toHaveBeenCalledWith("/403");
  });

  it("does not redirect while auth is loading", () => {
    mockRole.mockReturnValue("viewer");
    mockLoading.mockReturnValue(true);
    render(<SettingsPage />);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("does not redirect admin users", () => {
    mockRole.mockReturnValue("admin");
    render(<SettingsPage />);
    expect(mockRedirect).not.toHaveBeenCalled();
  });
});
