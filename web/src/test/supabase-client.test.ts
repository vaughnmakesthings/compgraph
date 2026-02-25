describe("supabase client", () => {
  const ORIGINAL_ENV = { ...process.env };

  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it("exports null when window is undefined (SSR)", async () => {
    const originalWindow = globalThis.window;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).window = undefined;
    try {
      const mod = await import("@/lib/supabase");
      expect(mod.supabase).toBeNull();
    } finally {
      globalThis.window = originalWindow;
    }
  });

  it("exports a SupabaseClient when window exists", async () => {
    const mod = await import("@/lib/supabase");
    expect(mod.supabase).not.toBeNull();
    expect(mod.supabase).toHaveProperty("auth");
  });
});
