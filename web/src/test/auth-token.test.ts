import { setAuthToken, getAuthToken } from "@/lib/auth-token";

describe("auth-token bridge", () => {
  afterEach(() => {
    setAuthToken(null);
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
