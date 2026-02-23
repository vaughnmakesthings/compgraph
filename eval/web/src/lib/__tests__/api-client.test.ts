import { describe, it, expect, vi, beforeEach } from "vitest";
import { getRuns, getModels, createComparison } from "../api-client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api-client", () => {
  it("getRuns fetches from /api/runs", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, model: "haiku-3.5" }],
    });
    const runs = await getRuns();
    expect(runs).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/runs",
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it("getModels fetches from /api/config/models", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ "haiku-3.5": "openrouter/..." }),
    });
    const models = await getModels();
    expect(models).toHaveProperty("haiku-3.5");
  });

  it("createComparison POSTs to /api/comparisons", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 42 }),
    });
    const result = await createComparison({
      posting_id: "p1",
      result_a_id: 1,
      result_b_id: 2,
      winner: "a",
    });
    expect(result.id).toBe(42);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/comparisons",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: async () => "Not found",
    });
    await expect(getRuns()).rejects.toThrow("API 404");
  });
});
