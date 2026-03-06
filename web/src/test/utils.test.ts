import { formatDuration } from "@/lib/utils";

describe("formatDuration", () => {
  it("formats seconds only", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(59)).toBe("59s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(60)).toBe("1m 0s");
    expect(formatDuration(202)).toBe("3m 22s");
    expect(formatDuration(3599)).toBe("59m 59s");
  });

  it("formats hours and minutes", () => {
    expect(formatDuration(3600)).toBe("1h 0m");
    expect(formatDuration(5400)).toBe("1h 30m");
    expect(formatDuration(35929)).toBe("9h 58m");
    expect(formatDuration(55194)).toBe("15h 19m");
  });

  it("handles negative input", () => {
    expect(formatDuration(-1)).toBe("—");
  });
});
