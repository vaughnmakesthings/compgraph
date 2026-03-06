import {
  setAuthToken,
  getAuthToken,
  isAuthReady,
  waitForAuth,
  resetAuthState,
} from "@/lib/auth-token";

describe("auth-token bridge", () => {
  afterEach(() => {
    resetAuthState();
  });

  it("returns null by default", () => {
    expect(getAuthToken()).toBeNull();
  });

  it("returns token after setAuthToken", () => {
    setAuthToken("test-jwt-token");
    expect(getAuthToken()).toBe("test-jwt-token");
  });

  it("clears token when set to null", () => {
    setAuthToken("test-jwt-token");
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });
});

describe("auth readiness gate", () => {
  afterEach(() => {
    resetAuthState();
  });

  it("is not ready before setAuthToken is called", () => {
    expect(isAuthReady()).toBe(false);
  });

  it("becomes ready after setAuthToken is called with a token", () => {
    setAuthToken("token-123");
    expect(isAuthReady()).toBe(true);
  });

  it("becomes ready after setAuthToken is called with null", () => {
    setAuthToken(null);
    expect(isAuthReady()).toBe(true);
  });

  it("waitForAuth resolves after setAuthToken is called", async () => {
    let resolved = false;
    const promise = waitForAuth().then(() => {
      resolved = true;
    });

    expect(resolved).toBe(false);

    setAuthToken("token-abc");

    await promise;
    expect(resolved).toBe(true);
  });

  it("waitForAuth resolves immediately if auth is already ready", async () => {
    setAuthToken("token-xyz");

    let resolved = false;
    await waitForAuth().then(() => {
      resolved = true;
    });

    expect(resolved).toBe(true);
  });

  it("resetAuthState resets readiness for a fresh cycle", () => {
    setAuthToken("token");
    expect(isAuthReady()).toBe(true);

    resetAuthState();

    expect(isAuthReady()).toBe(false);
    expect(getAuthToken()).toBeNull();
  });

  it("waitForAuth works after resetAuthState", async () => {
    setAuthToken("first-token");
    await waitForAuth();

    resetAuthState();

    let resolved = false;
    const promise = waitForAuth().then(() => {
      resolved = true;
    });

    expect(resolved).toBe(false);

    setAuthToken("second-token");
    await promise;

    expect(resolved).toBe(true);
    expect(getAuthToken()).toBe("second-token");
  });
});
