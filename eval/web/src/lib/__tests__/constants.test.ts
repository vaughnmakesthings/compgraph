import { describe, it, expect } from "vitest";
import { SIDEBAR_WIDTH, SIDEBAR_WIDTH_COLLAPSED } from "@/lib/constants";

describe("constants", () => {
  it("SIDEBAR_WIDTH is 240", () => {
    expect(SIDEBAR_WIDTH).toBe(240);
  });

  it("SIDEBAR_WIDTH_COLLAPSED is 60", () => {
    expect(SIDEBAR_WIDTH_COLLAPSED).toBe(60);
  });
});
