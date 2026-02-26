import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { getAuthToken, setAuthToken } from "@/lib/auth-token";
import { createMockSupabaseAuth, mockSession } from "./mocks/supabase";

let mockSupabase: ReturnType<typeof createMockSupabaseAuth> | null = null;

vi.mock("@/lib/supabase", () => ({
  get supabase() {
    return mockSupabase;
  },
}));

const mockRouter = { replace: vi.fn(), push: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/",
}));

function AuthDisplay() {
  const { session, user, role, loading, signOut } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!session) return <div>Not authenticated</div>;
  return (
    <div>
      <span>User: {user?.email}</span>
      <span>Role: {role}</span>
      <button onClick={() => void signOut()}>Sign out</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
  });

  it("shows loading initially then resolves session", async () => {
    mockSupabase = createMockSupabaseAuth({ session: mockSession });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("User: test@example.com")).toBeInTheDocument();
    });
  });

  it("shows no user when session is null", async () => {
    mockSupabase = createMockSupabaseAuth({ session: null });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Not authenticated")).toBeInTheDocument();
    });
  });

  it("defaults role to viewer when app_metadata.role is missing", async () => {
    const sessionNoRole = {
      ...mockSession,
      user: {
        ...mockSession.user,
        app_metadata: { provider: "email", providers: ["email"] },
      },
    };
    mockSupabase = createMockSupabaseAuth({ session: sessionNoRole });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Role: viewer")).toBeInTheDocument();
    });
  });

  it("reads role from app_metadata.role", async () => {
    mockSupabase = createMockSupabaseAuth({ session: mockSession });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Role: admin")).toBeInTheDocument();
    });
  });

  it("calls setAuthToken with token on session load", async () => {
    mockSupabase = createMockSupabaseAuth({ session: mockSession });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(getAuthToken()).toBe("mock-access-token");
    });
  });

  it("clears auth token on signOut", async () => {
    const user = userEvent.setup();
    mockSupabase = createMockSupabaseAuth({ session: mockSession });

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("User: test@example.com")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(getAuthToken()).toBeNull();
  });

  it("sets loading to false when supabase is null (SSR)", async () => {
    mockSupabase = null;

    render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Not authenticated")).toBeInTheDocument();
    });
  });

  it("unsubscribes from auth state changes on unmount", async () => {
    mockSupabase = createMockSupabaseAuth({ session: null });
    const unsubscribe = mockSupabase._unsubscribe;

    const { unmount } = render(
      <AuthProvider>
        <AuthDisplay />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Not authenticated")).toBeInTheDocument();
    });

    unmount();
    expect(unsubscribe).toHaveBeenCalled();
  });
});
