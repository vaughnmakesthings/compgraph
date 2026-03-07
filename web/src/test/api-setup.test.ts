vi.mock("@/api-client/client.gen", () => ({
  client: {
    setConfig: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
      error: { use: vi.fn() },
    },
  },
}));

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

vi.mock("@/lib/auth-token", () => ({
  getAuthToken: vi.fn(),
  waitForAuth: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/constants", () => ({ API_BASE: "http://test-api:8000" }));

const originalLocation = window.location;

async function freshImports() {
  const { setupApi } = await import("@/lib/api-setup");
  const { client } = await import("@/api-client/client.gen");
  const { toast } = await import("sonner");
  const { getAuthToken, waitForAuth } = await import("@/lib/auth-token");
  return { setupApi, client, toast, getAuthToken, waitForAuth };
}

describe("setupApi", () => {
  beforeEach(() => {
    vi.resetModules();
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  afterAll(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
  });

  it("calls client.setConfig with API_BASE", async () => {
    const { setupApi, client } = await freshImports();

    setupApi();

    expect(client.setConfig).toHaveBeenCalledWith({
      baseUrl: "http://test-api:8000",
    });
  });

  it("is idempotent — second call does not call setConfig again", async () => {
    const { setupApi, client } = await freshImports();

    setupApi();
    setupApi();

    expect(client.setConfig).toHaveBeenCalledTimes(1);
  });

  it("request interceptor adds Authorization header when token exists", async () => {
    const { setupApi, client, getAuthToken } = await freshImports();
    vi.mocked(getAuthToken).mockReturnValue("test-token-123");

    setupApi();

    const requestCallback = vi.mocked(client.interceptors.request.use).mock
      .calls[0][0] as (request: Request) => Promise<Request>;

    const mockRequest = new Request("http://test-api:8000/v1/companies");
    const result = await requestCallback(mockRequest);

    expect(result.headers.get("Authorization")).toBe("Bearer test-token-123");
  });

  it("request interceptor skips header when no token", async () => {
    const { setupApi, client, getAuthToken } = await freshImports();
    vi.mocked(getAuthToken).mockReturnValue(null);

    setupApi();

    const requestCallback = vi.mocked(client.interceptors.request.use).mock
      .calls[0][0] as (request: Request) => Promise<Request>;

    const mockRequest = new Request("http://test-api:8000/v1/companies");
    const result = await requestCallback(mockRequest);

    expect(result.headers.has("Authorization")).toBe(false);
  });

  it("request interceptor awaits waitForAuth before getting token", async () => {
    const { setupApi, client, waitForAuth, getAuthToken } =
      await freshImports();

    const callOrder: string[] = [];
    vi.mocked(waitForAuth).mockImplementation(async () => {
      callOrder.push("waitForAuth");
    });
    vi.mocked(getAuthToken).mockImplementation(() => {
      callOrder.push("getAuthToken");
      return null;
    });

    setupApi();

    const requestCallback = vi.mocked(client.interceptors.request.use).mock
      .calls[0][0] as (request: Request) => Promise<Request>;

    await requestCallback(new Request("http://test-api:8000/v1/test"));

    expect(callOrder).toEqual(["waitForAuth", "getAuthToken"]);
  });

  it("response interceptor shows toast on 401", async () => {
    const { setupApi, client, toast } = await freshImports();

    setupApi();

    const responseCallback = vi.mocked(client.interceptors.response.use).mock
      .calls[0][0] as (response: Response) => Promise<Response>;

    const mockResponse = new Response(null, { status: 401 });
    await responseCallback(mockResponse);

    expect(toast.error).toHaveBeenCalledWith(
      "Your session expired. Please sign in again.",
    );
  });

  it("response interceptor redirects to /login on 401", async () => {
    const { setupApi, client } = await freshImports();

    setupApi();

    const responseCallback = vi.mocked(client.interceptors.response.use).mock
      .calls[0][0] as (response: Response) => Promise<Response>;

    const mockResponse = new Response(null, { status: 401 });
    await responseCallback(mockResponse);

    expect(window.location.href).toBe("/login");
  });

  it("response interceptor passes through non-401 responses", async () => {
    const { setupApi, client, toast } = await freshImports();

    setupApi();

    const responseCallback = vi.mocked(client.interceptors.response.use).mock
      .calls[0][0] as (response: Response) => Promise<Response>;

    const mockResponse = new Response(JSON.stringify({ data: "ok" }), {
      status: 200,
    });
    const result = await responseCallback(mockResponse);

    expect(toast.error).not.toHaveBeenCalled();
    expect(result).toBe(mockResponse);
  });

  it("error interceptor strips HTML tags from error message", async () => {
    const { setupApi, client } = await freshImports();

    setupApi();

    const errorCallback = vi.mocked(client.interceptors.error.use).mock
      .calls[0][0] as (error: unknown) => Promise<unknown>;

    const error = new Error(
      '<p>Something <strong>went wrong</strong></p><br/>Try again',
    );
    const result = await errorCallback(error);

    expect(result).toBeInstanceOf(Error);
    expect((result as Error).message).toBe("Something went wrongTry again");
  });
});
