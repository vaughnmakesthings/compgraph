import { describe, expect, it, vi, beforeEach } from "vitest";

const mockGetUser = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: {
      getUser: mockGetUser,
    },
  }),
}));

vi.mock("next/server", () => {
  class MockNextResponse {
    cookies = {
      set: vi.fn(),
    };
    static next({ request }: { request: MockNextRequest }) {
      const res = new MockNextResponse();
      (res as Record<string, unknown>)._request = request;
      return res;
    }
    static redirect(url: URL) {
      const res = new MockNextResponse();
      (res as Record<string, unknown>)._redirectUrl = url.toString();
      return res;
    }
  }

  class MockNextRequest {
    url: string;
    nextUrl: URL;
    cookies = {
      getAll: vi.fn().mockReturnValue([]),
      set: vi.fn(),
    };
    constructor(url: string) {
      this.url = url;
      this.nextUrl = new URL(url);
    }
  }

  return {
    NextResponse: MockNextResponse,
    NextRequest: MockNextRequest,
  };
});

import { updateSession } from "@/lib/supabase/middleware";
import { NextRequest } from "next/server";

describe("updateSession middleware", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("allows authenticated users to access protected routes", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "user-1", email: "test@example.com" } },
    });

    const request = new NextRequest("http://localhost:3000/");
    const response = await updateSession(request);

    expect(mockGetUser).toHaveBeenCalledOnce();
    expect(response).toBeDefined();
    expect((response as Record<string, unknown>)._redirectUrl).toBeUndefined();
  });

  it("redirects unauthenticated users to /login with expired param", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: null },
    });

    const request = new NextRequest("http://localhost:3000/settings");
    const response = await updateSession(request);

    const redirectUrl = (response as Record<string, unknown>)._redirectUrl as string;
    expect(redirectUrl).toContain("/login");
    expect(redirectUrl).toContain("expired=1");
  });

  it("allows unauthenticated users to access /login", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: null },
    });

    const request = new NextRequest("http://localhost:3000/login");
    const response = await updateSession(request);

    expect((response as Record<string, unknown>)._redirectUrl).toBeUndefined();
  });

  it("allows unauthenticated users to access /setup", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: null },
    });

    const request = new NextRequest("http://localhost:3000/setup?email=test@example.com");
    const response = await updateSession(request);

    expect((response as Record<string, unknown>)._redirectUrl).toBeUndefined();
  });

  it("allows unauthenticated users to access /403", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: null },
    });

    const request = new NextRequest("http://localhost:3000/403");
    const response = await updateSession(request);

    expect((response as Record<string, unknown>)._redirectUrl).toBeUndefined();
  });
});
