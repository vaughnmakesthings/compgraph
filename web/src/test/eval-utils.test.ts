import { EVAL_FIELDS, formatRunLabel, getParsedResult, formatFieldValue } from "@/lib/eval-utils";
import type { EvalRun, EvalResult } from "@/lib/types";

function makeRun(overrides: Partial<EvalRun> = {}): EvalRun {
  return {
    id: "run-1",
    pass_number: 1,
    model: "haiku-4.5",
    prompt_version: "v3",
    status: "completed",
    created_at: "2026-03-01T00:00:00Z",
    completed_at: "2026-03-01T00:05:00Z",
    total_items: 100,
    completed_items: 100,
    ...overrides,
  };
}

function makeResult(overrides: Partial<EvalResult> = {}): EvalResult {
  return {
    id: "result-1",
    run_id: "run-1",
    posting_id: "posting-1",
    raw_response: null,
    parsed_result: null,
    parse_success: true,
    input_tokens: null,
    output_tokens: null,
    cost_usd: null,
    latency_ms: null,
    created_at: null,
    ...overrides,
  };
}

describe("EVAL_FIELDS", () => {
  it("contains exactly 13 fields", () => {
    expect(EVAL_FIELDS).toHaveLength(13);
  });

  it("includes known enrichment fields", () => {
    expect(EVAL_FIELDS).toContain("role_archetype");
    expect(EVAL_FIELDS).toContain("pay_type");
    expect(EVAL_FIELDS).toContain("has_commission");
    expect(EVAL_FIELDS).toContain("tools_mentioned");
  });
});

describe("formatRunLabel", () => {
  it("formats a standard run label with model, prompt version, and pass number", () => {
    const run = makeRun({ model: "haiku-4.5", prompt_version: "v3", pass_number: 1 });
    expect(formatRunLabel(run)).toBe("haiku-4.5 / v3 \u00B7 Pass 1");
  });

  it("handles a different model and pass number", () => {
    const run = makeRun({ model: "sonnet-4.5", prompt_version: "v7", pass_number: 2 });
    expect(formatRunLabel(run)).toBe("sonnet-4.5 / v7 \u00B7 Pass 2");
  });
});

describe("getParsedResult", () => {
  it("returns empty object when parsed_result is null", () => {
    const result = makeResult({ parsed_result: null });
    expect(getParsedResult(result)).toEqual({});
  });

  it("passes through an object parsed_result directly", () => {
    const data = { role_archetype: "merchandiser", pay_type: "hourly" };
    const result = makeResult({ parsed_result: data });
    expect(getParsedResult(result)).toEqual(data);
  });

  it("parses a valid JSON string", () => {
    const data = { pay_min: 15, pay_max: 20 };
    const result = makeResult({
      parsed_result: JSON.stringify(data) as unknown as Record<string, unknown>,
    });
    expect(getParsedResult(result)).toEqual(data);
  });

  it("returns empty object for malformed JSON string", () => {
    const result = makeResult({
      parsed_result: "{not valid json" as unknown as Record<string, unknown>,
    });
    expect(getParsedResult(result)).toEqual({});
  });

  it("returns empty object for empty string", () => {
    const result = makeResult({
      parsed_result: "" as unknown as Record<string, unknown>,
    });
    expect(getParsedResult(result)).toEqual({});
  });
});

describe("formatFieldValue", () => {
  it("returns em-dash for null", () => {
    expect(formatFieldValue(null)).toBe("\u2014");
  });

  it("returns em-dash for undefined", () => {
    expect(formatFieldValue(undefined)).toBe("\u2014");
  });

  it('returns "Yes" for true', () => {
    expect(formatFieldValue(true)).toBe("Yes");
  });

  it('returns "No" for false', () => {
    expect(formatFieldValue(false)).toBe("No");
  });

  it("returns em-dash for empty array", () => {
    expect(formatFieldValue([])).toBe("\u2014");
  });

  it("joins non-empty array with comma and space", () => {
    expect(formatFieldValue(["a", "b"])).toBe("a, b");
  });

  it("returns JSON string for plain object", () => {
    expect(formatFieldValue({ key: "val" })).toBe('{"key":"val"}');
  });

  it("passes through a string value", () => {
    expect(formatFieldValue("hourly")).toBe("hourly");
  });

  it("converts a number to string", () => {
    expect(formatFieldValue(42)).toBe("42");
  });
});
