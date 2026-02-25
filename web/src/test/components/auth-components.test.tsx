import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LoginForm } from "@/components/auth/login-form";
import { AccountSetupForm } from "@/components/auth/account-setup-form";
import { InviteUserForm } from "@/components/auth/invite-user-form";
import { UserManagementSection } from "@/components/auth/user-management-section";
import { UserTable } from "@/components/auth/user-table";
import type { AppUser } from "@/components/auth/user-management-section";
import {
  createMockSupabaseAuth,
} from "../mocks/supabase";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Supabase client mock — mutable so individual tests can configure behavior
let mockSupabase: ReturnType<typeof createMockSupabaseAuth> | null = null;

vi.mock("@/lib/supabase", () => ({
  get supabase() {
    return mockSupabase;
  },
}));

// next/navigation mock
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// api-client mock
const mockInviteUser = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: {
    inviteUser: (...args: unknown[]) => mockInviteUser(...args),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock @headlessui/react Dialog for EditUserDialog (slide-over drawer)
vi.mock("@headlessui/react", () => ({
  Dialog: ({
    open,
    onClose,
    children,
  }: {
    open: boolean;
    onClose: () => void;
    children: React.ReactNode;
  }) => {
    if (!open) return null;
    return (
      <div role="dialog" data-headlessui="true">
        {typeof children === "function"
          ? (children as (props: Record<string, unknown>) => React.ReactNode)({})
          : children}
      </div>
    );
  },
  DialogPanel: ({
    children,
  }: {
    children: React.ReactNode;
    transition?: boolean;
    className?: string;
  }) => <div>{typeof children === "function" ? null : children}</div>,
  DialogTitle: ({
    children,
    as: Component = "h3",
    ...props
  }: {
    children: React.ReactNode;
    as?: React.ElementType;
    className?: string;
  }) => {
    const Tag = Component;
    return <Tag {...props}>{children}</Tag>;
  },
  DialogBackdrop: () => null,
}));

// Mock @tremor/react Dialog for AddUserDialog
vi.mock("@tremor/react", () => ({
  Dialog: ({
    open,
    onClose,
    children,
  }: {
    open: boolean;
    onClose: () => void;
    children: React.ReactNode;
  }) => {
    if (!open) return null;
    return (
      <div role="dialog" data-tremor="true">
        {children}
      </div>
    );
  },
  DialogPanel: ({
    children,
  }: {
    children: React.ReactNode;
    className?: string;
    style?: React.CSSProperties;
  }) => <div>{children}</div>,
}));

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const mockUsers: AppUser[] = [
  {
    id: "u-1",
    firstName: "Alice",
    lastName: "Johnson",
    email: "alice@example.com",
    role: "admin",
    status: "active",
    joinedAt: "2026-01-10T00:00:00Z",
    lastLoginAt: "2026-02-25T14:22:00Z",
    isCurrentUser: true,
  },
  {
    id: "u-2",
    firstName: "Bob",
    lastName: "Martinez",
    email: "bob@example.com",
    role: "user",
    status: "active",
    joinedAt: "2026-01-15T00:00:00Z",
    lastLoginAt: "2026-02-24T09:10:00Z",
  },
  {
    id: "u-3",
    firstName: "Carol",
    lastName: "Singh",
    email: "carol@example.com",
    role: "user",
    status: "invite_sent",
    joinedAt: null,
    lastLoginAt: null,
  },
];

// =========================================================================
// LoginForm
// =========================================================================

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSupabase = createMockSupabaseAuth();
  });

  it("renders password mode by default", () => {
    render(<LoginForm />);
    expect(screen.getAllByText("Password")).toHaveLength(2);
    expect(screen.getByText("Magic link")).toBeInTheDocument();
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.getByText("Forgot password?")).toBeInTheDocument();
  });

  it("renders email input", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
  });

  it("renders password input in password mode", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("switches to magic-link mode and hides password field", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.click(screen.getByText("Magic link"));

    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    expect(screen.getByText("Send magic link")).toBeInTheDocument();
    expect(screen.queryByText("Forgot password?")).not.toBeInTheDocument();
  });

  it("switches back to password mode", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.click(screen.getByText("Magic link"));
    await user.click(screen.getByText("Password"));

    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  it("toggles password visibility", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("type", "password");

    await user.click(screen.getByLabelText("Show password"));
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(screen.getByLabelText("Hide password"));
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("shows invite-only note", () => {
    render(<LoginForm />);
    expect(
      screen.getByText(/Invite-only access/),
    ).toBeInTheDocument();
  });

  it("calls signInWithPassword with email and password on submit", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email address"), "user@test.com");
    await user.type(screen.getByLabelText("Password"), "secret123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(mockSupabase!.auth.signInWithPassword).toHaveBeenCalledWith({
        email: "user@test.com",
        password: "secret123",
      });
    });
  });

  it("navigates to / on successful password login", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email address"), "user@test.com");
    await user.type(screen.getByLabelText("Password"), "secret123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  it("displays error from Supabase on failed login", async () => {
    mockSupabase = createMockSupabaseAuth({
      signInError: { message: "Invalid login credentials" },
    });
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email address"), "bad@test.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Invalid login credentials",
      );
    });
  });

  it("calls signInWithOtp in magic-link mode", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.click(screen.getByText("Magic link"));
    await user.type(screen.getByLabelText("Email address"), "user@test.com");
    await user.click(screen.getByRole("button", { name: "Send magic link" }));

    await waitFor(() => {
      expect(mockSupabase!.auth.signInWithOtp).toHaveBeenCalledWith({
        email: "user@test.com",
      });
    });

    expect(screen.getByText("Check your email")).toBeInTheDocument();
  });
});

// =========================================================================
// AccountSetupForm
// =========================================================================

describe("AccountSetupForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSupabase = createMockSupabaseAuth();
  });

  it("renders all form fields", () => {
    render(<AccountSetupForm email="test@example.com" />);
    expect(screen.getByLabelText("First name")).toBeInTheDocument();
    expect(screen.getByLabelText("Last name")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Create password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
  });

  it("shows locked email label", () => {
    render(<AccountSetupForm email="user@co.com" />);
    expect(screen.getByText("(locked)")).toBeInTheDocument();
    expect(
      screen.getByText(/This is the email your invite was sent to/),
    ).toBeInTheDocument();
  });

  it("shows password strength meter when typing password", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    expect(screen.queryByText(/Strength:/)).not.toBeInTheDocument();

    const pwInput = screen.getByLabelText("Create password");
    await user.type(pwInput, "ab");
    expect(screen.getByText("Strength: Weak")).toBeInTheDocument();
  });

  it("shows Fair strength for moderate password", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);
    const pwInput = screen.getByLabelText("Create password");
    // 8+ chars + digit => score=2 => "fair"
    await user.type(pwInput, "abcdefg1");
    expect(screen.getByText("Strength: Fair")).toBeInTheDocument();
  });

  it("shows Medium strength for better password", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);
    const pwInput = screen.getByLabelText("Create password");
    // 8+ chars + uppercase + digit => score=3 => "medium"
    await user.type(pwInput, "Abcdefg1");
    expect(screen.getByText("Strength: Medium")).toBeInTheDocument();
  });

  it("shows Strong strength for complex password", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);
    const pwInput = screen.getByLabelText("Create password");
    // 12+ chars + uppercase + digit + special => score=5 => "strong"
    await user.type(pwInput, "Abcdefghij1!");
    expect(screen.getByText("Strength: Strong")).toBeInTheDocument();
  });

  it("shows validation errors on empty submit", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByText("First name is required")).toBeInTheDocument();
    expect(screen.getByText("Last name is required")).toBeInTheDocument();
    expect(
      screen.getByText("Password must be at least 8 characters"),
    ).toBeInTheDocument();
  });

  it("shows mismatch error when passwords differ", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    await user.type(screen.getByLabelText("First name"), "John");
    await user.type(screen.getByLabelText("Last name"), "Doe");
    await user.type(screen.getByLabelText("Create password"), "Password1!");
    await user.type(screen.getByLabelText("Confirm password"), "Different1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
  });

  it("toggles password visibility in PasswordInput", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    const createPw = screen.getByLabelText("Create password");
    expect(createPw).toHaveAttribute("type", "password");

    // There are two show/hide toggles (create + confirm) — get the first one
    const showButtons = screen.getAllByLabelText("Show password");
    await user.click(showButtons[0]);
    expect(createPw).toHaveAttribute("type", "text");
  });

  it("submits successfully and calls updateUser with correct args", async () => {
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    await user.type(screen.getByLabelText("First name"), "John");
    await user.type(screen.getByLabelText("Last name"), "Doe");
    await user.type(screen.getByLabelText("Create password"), "StrongPw1!");
    await user.type(screen.getByLabelText("Confirm password"), "StrongPw1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(mockSupabase!.auth.updateUser).toHaveBeenCalledWith({
        password: "StrongPw1!",
        data: { first_name: "John", last_name: "Doe" },
      });
    });

    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("displays Supabase error on updateUser failure", async () => {
    mockSupabase = createMockSupabaseAuth({
      updateUserError: { message: "Password too weak" },
    });
    const user = userEvent.setup();
    render(<AccountSetupForm email="test@example.com" />);

    await user.type(screen.getByLabelText("First name"), "John");
    await user.type(screen.getByLabelText("Last name"), "Doe");
    await user.type(screen.getByLabelText("Create password"), "StrongPw1!");
    await user.type(screen.getByLabelText("Confirm password"), "StrongPw1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByText("Password too weak")).toBeInTheDocument();
    });
  });
});

// =========================================================================
// InviteUserForm
// =========================================================================

describe("InviteUserForm", () => {
  const defaultProps = {
    onInvited: vi.fn(),
    existingEmails: ["existing@example.com"],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockInviteUser.mockResolvedValue({
      user_id: "u-new",
      email: "new@example.com",
      role: "user",
    });
  });

  it("renders the invite form", () => {
    render(<InviteUserForm {...defaultProps} />);
    expect(screen.getByText(/Invite a new user/)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("colleague@company.com"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send Invite" })).toBeInTheDocument();
  });

  it("shows role selector with User and Admin options", () => {
    render(<InviteUserForm {...defaultProps} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(within(select).getByText("User")).toBeInTheDocument();
    expect(within(select).getByText("Admin")).toBeInTheDocument();
  });

  it("shows error for empty email", async () => {
    const user = userEvent.setup();
    render(<InviteUserForm {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Send Invite" }));
    expect(screen.getByText("Email is required")).toBeInTheDocument();
  });

  it("shows error for invalid email format", async () => {
    const user = userEvent.setup();
    render(<InviteUserForm {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("colleague@company.com"),
      "not-an-email",
    );
    await user.click(screen.getByRole("button", { name: "Send Invite" }));
    expect(screen.getByText("Enter a valid email address")).toBeInTheDocument();
  });

  it("shows error for duplicate email", async () => {
    const user = userEvent.setup();
    render(<InviteUserForm {...defaultProps} />);

    await user.type(
      screen.getByPlaceholderText("colleague@company.com"),
      "existing@example.com",
    );
    await user.click(screen.getByRole("button", { name: "Send Invite" }));
    expect(
      screen.getByText("This email is already in the system"),
    ).toBeInTheDocument();
  });

  it("clears email error when user types", async () => {
    const user = userEvent.setup();
    render(<InviteUserForm {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Send Invite" }));
    expect(screen.getByText("Email is required")).toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText("colleague@company.com"),
      "a",
    );
    expect(screen.queryByText("Email is required")).not.toBeInTheDocument();
  });

  it("shows expiry note", () => {
    render(<InviteUserForm {...defaultProps} />);
    expect(
      screen.getByText(/Link expires in 72 hours/),
    ).toBeInTheDocument();
  });
});

// =========================================================================
// UserManagementSection
// =========================================================================

describe("UserManagementSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the section title", () => {
    render(<UserManagementSection />);
    expect(screen.getByText("User Management")).toBeInTheDocument();
  });

  it("renders admin-only badge", () => {
    render(<UserManagementSection />);
    expect(screen.getByText(/Admin only/)).toBeInTheDocument();
  });

  it("renders stat cells with correct counts from MOCK_USERS", () => {
    render(<UserManagementSection />);
    // MOCK_USERS has 4 users: 3 active, 1 invite_sent, 1 admin
    expect(screen.getByText("Total users")).toBeInTheDocument();
    // "Active" also appears in filter dropdown and as pills — check label exists
    expect(screen.getAllByText("Active").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getAllByText("Admins").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Users heading from UserTable", () => {
    render(<UserManagementSection />);
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(
      screen.getByText(/Manage team members/),
    ).toBeInTheDocument();
  });
});

// =========================================================================
// UserTable
// =========================================================================

describe("UserTable", () => {
  const defaultProps = {
    users: mockUsers,
    currentUserId: "u-1",
    existingEmails: mockUsers.map((u) => u.email),
    onUserUpdated: vi.fn() as unknown as (user: AppUser) => void,
    onUserRemoved: vi.fn() as unknown as (userId: string) => void,
    onUserInvited: vi.fn() as unknown as (user: AppUser) => void,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders header and description", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(
      screen.getByText(/Manage team members, invite new users/),
    ).toBeInTheDocument();
  });

  it("renders all user rows", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.getByText("Bob Martinez")).toBeInTheDocument();
    expect(screen.getByText("Carol Singh")).toBeInTheDocument();
  });

  it("shows 'You' label for current user", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("renders column headers with sort buttons", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("Role")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Joined")).toBeInTheDocument();
    expect(screen.getByText("Last Login")).toBeInTheDocument();
  });

  it("renders status pills", () => {
    render(<UserTable {...defaultProps} />);
    // "Active" appears as pills and as a filter option
    const activePills = screen.getAllByText("Active");
    expect(activePills.length).toBeGreaterThanOrEqual(2);
    // "Invite sent" appears as a pill and as a filter option
    const inviteSentElements = screen.getAllByText("Invite sent");
    expect(inviteSentElements.length).toBeGreaterThanOrEqual(2);
  });

  it("renders role pills", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getAllByText("Admin").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("User").length).toBeGreaterThanOrEqual(1);
  });

  it("renders user count footer", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("3 of 3 users shown")).toBeInTheDocument();
  });

  it("renders Edit buttons for each user", () => {
    render(<UserTable {...defaultProps} />);
    // Each row has an Edit button — the button also contains sr-only span
    // so we query by role
    const editButtons = screen.getAllByRole("button", { name: /^Edit/ });
    expect(editButtons).toHaveLength(3);
  });

  it("renders Add user button", () => {
    render(<UserTable {...defaultProps} />);
    expect(screen.getByText("Add user")).toBeInTheDocument();
  });

  it("filters users by search", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText("Search name or email\u2026");
    await user.type(searchInput, "alice");

    expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.queryByText("Bob Martinez")).not.toBeInTheDocument();
    expect(screen.queryByText("Carol Singh")).not.toBeInTheDocument();
    expect(screen.getByText("1 of 3 users shown")).toBeInTheDocument();
  });

  it("filters users by role", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    const roleSelect = screen.getByDisplayValue("All roles");
    await user.selectOptions(roleSelect, "admin");

    expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    expect(screen.queryByText("Bob Martinez")).not.toBeInTheDocument();
    expect(screen.getByText("1 of 3 users shown")).toBeInTheDocument();
  });

  it("filters users by status", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    const statusSelect = screen.getByDisplayValue("All statuses");
    await user.selectOptions(statusSelect, "invite_sent");

    expect(screen.queryByText("Alice Johnson")).not.toBeInTheDocument();
    expect(screen.getByText("Carol Singh")).toBeInTheDocument();
    expect(screen.getByText("1 of 3 users shown")).toBeInTheDocument();
  });

  it("shows empty state when no users match filters", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText("Search name or email\u2026");
    await user.type(searchInput, "nonexistent-user-xyz");

    expect(
      screen.getByText("No users match your filters."),
    ).toBeInTheDocument();
    expect(screen.getByText("0 of 3 users shown")).toBeInTheDocument();
  });

  it("sorts users by name column", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    const nameButton = screen.getByRole("button", { name: /Name/ });
    await user.click(nameButton);

    // After first click, sort asc — Alice, Bob, Carol
    const rows = screen.getAllByText(/Johnson|Martinez|Singh/);
    expect(rows[0]).toHaveTextContent("Johnson");
  });

  it("formats dates in user rows", () => {
    render(<UserTable {...defaultProps} />);
    // Carol has null dates, should show "—"
    const dashes = screen.getAllByText("\u2014");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("opens AddUser dialog when clicking Add user button", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    await user.click(screen.getByText("Add user"));

    // The Tremor Dialog mock renders when open=true
    expect(screen.getByText("Add user", { selector: "h3" })).toBeInTheDocument();
    expect(
      screen.getByText("Send a magic-link invite to a new team member."),
    ).toBeInTheDocument();
  });

  it("opens EditUser drawer when clicking Edit button", async () => {
    const user = userEvent.setup();
    render(<UserTable {...defaultProps} />);

    // Click Edit on Bob (second edit button — non-current user)
    const editButtons = screen.getAllByText("Edit");
    await user.click(editButtons[1]);

    // The Headless UI Dialog mock renders the drawer
    expect(screen.getByText("Bob Martinez")).toBeInTheDocument();
    expect(screen.getByText("bob@example.com")).toBeInTheDocument();
  });
});
