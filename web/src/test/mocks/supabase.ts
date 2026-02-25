import type { Session, User } from "@supabase/supabase-js";

export const mockUser: User = {
  id: "user-123",
  aud: "authenticated",
  role: "authenticated",
  email: "test@example.com",
  email_confirmed_at: "2026-01-01T00:00:00Z",
  phone: "",
  confirmed_at: "2026-01-01T00:00:00Z",
  last_sign_in_at: "2026-02-25T12:00:00Z",
  app_metadata: { provider: "email", providers: ["email"], role: "admin" },
  user_metadata: {},
  identities: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-02-25T12:00:00Z",
};

export const mockSession: Session = {
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  expires_in: 3600,
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  token_type: "bearer",
  user: mockUser,
};

export function createMockSupabaseAuth(options?: {
  session?: Session | null;
  signInError?: { message: string };
  updateUserError?: { message: string };
}) {
  const session = options?.session ?? null;
  const unsubscribe = vi.fn();

  return {
    auth: {
      getSession: vi
        .fn()
        .mockResolvedValue({ data: { session }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe } },
      }),
      signInWithPassword: options?.signInError
        ? vi.fn().mockResolvedValue({
            data: { user: null, session: null },
            error: { message: options.signInError.message },
          })
        : vi.fn().mockResolvedValue({
            data: { user: mockUser, session: mockSession },
            error: null,
          }),
      signInWithOtp: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
      updateUser: options?.updateUserError
        ? vi.fn().mockResolvedValue({
            data: { user: null },
            error: { message: options.updateUserError.message },
          })
        : vi.fn().mockResolvedValue({
            data: { user: mockUser },
            error: null,
          }),
      resetPasswordForEmail: vi
        .fn()
        .mockResolvedValue({ data: {}, error: null }),
    },
    _unsubscribe: unsubscribe,
  };
}
