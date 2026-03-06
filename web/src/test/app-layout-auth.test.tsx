import { screen, waitFor } from "@testing-library/react";
import { createMockSupabaseAuth, mockSession } from "./mocks/supabase";
import { setAuthToken } from "@/lib/auth-token";
import { AuthProvider } from "@/lib/auth-context";
import { renderWithQueryClient } from "./test-utils";

let mockSupabase: ReturnType<typeof createMockSupabaseAuth> | null = null;

vi.mock("@/lib/supabase", () => ({
  get supabase() {
    return mockSupabase;
  },
}));

const mockRedirect = vi.fn();
const mockRouter = { replace: vi.fn(), push: vi.fn() };
vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => {
    mockRedirect(...args);
  },
  useRouter: () => mockRouter,
  usePathname: () => "/",
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

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

import AppLayout from "@/app/(app)/layout";

function renderWithAuth(ui: React.ReactElement) {
  return renderWithQueryClient(
    <AuthProvider>{ui}</AuthProvider>,
  );
}

describe("AppLayout auth guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true }),
    );
  });

  it("shows loading skeleton while auth is resolving", () => {
    mockSupabase = createMockSupabaseAuth({ session: null });
    mockSupabase.auth.getSession = vi
      .fn()
      .mockReturnValue(new Promise(() => {}));

    renderWithAuth(
      <AppLayout>
        <div>Protected content</div>
      </AppLayout>,
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("redirects to /login when no session", async () => {
    mockSupabase = createMockSupabaseAuth({ session: null });

    renderWithAuth(
      <AppLayout>
        <div>Protected content</div>
      </AppLayout>,
    );

    await waitFor(() => {
      expect(mockRedirect).toHaveBeenCalledWith("/login");
    });
  });

  it("renders Shell with children when authenticated", async () => {
    mockSupabase = createMockSupabaseAuth({ session: mockSession });

    renderWithAuth(
      <AppLayout>
        <div>Protected content</div>
      </AppLayout>,
    );

    await waitFor(() => {
      expect(screen.getByText("Protected content")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("navigation", { name: /main navigation/i }),
    ).toBeInTheDocument();
  });
});
