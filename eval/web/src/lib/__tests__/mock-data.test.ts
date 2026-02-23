import { describe, it, expect } from "vitest";
import {
  EVAL_RUNS,
  LEADERBOARD,
  CORPUS_POSTINGS,
  FIELD_REVIEWS,
  DIFF_ROWS,
  FIELD_POPULATION,
  UNIQUE_MODELS,
} from "@/lib/mock-data";

describe("mock-data", () => {
  it("EVAL_RUNS has 6 entries", () => {
    expect(EVAL_RUNS).toHaveLength(6);
  });

  it("LEADERBOARD is sorted by Elo descending", () => {
    for (let i = 1; i < LEADERBOARD.length; i++) {
      expect(LEADERBOARD[i - 1].elo).toBeGreaterThanOrEqual(LEADERBOARD[i].elo);
    }
  });

  it("CORPUS_POSTINGS has 3 entries with required fields", () => {
    expect(CORPUS_POSTINGS).toHaveLength(3);
    for (const p of CORPUS_POSTINGS) {
      expect(p.id).toBeTruthy();
      expect(p.title).toBeTruthy();
      expect(p.company).toBeTruthy();
    }
  });

  it("FIELD_REVIEWS has 6 entries with valid judgments", () => {
    expect(FIELD_REVIEWS).toHaveLength(6);
    const validJudgments = ["correct", "wrong", "improved", "cant-assess", "pending"];
    for (const r of FIELD_REVIEWS) {
      expect(validJudgments).toContain(r.judgment);
    }
  });

  it("DIFF_ROWS has 6 entries", () => {
    expect(DIFF_ROWS).toHaveLength(6);
  });

  it("FIELD_POPULATION matches LEADERBOARD model count", () => {
    expect(FIELD_POPULATION).toHaveLength(LEADERBOARD.length);
  });

  it("UNIQUE_MODELS derives from EVAL_RUNS without duplicates", () => {
    expect(UNIQUE_MODELS.length).toBeLessThanOrEqual(EVAL_RUNS.length);
    expect(new Set(UNIQUE_MODELS).size).toBe(UNIQUE_MODELS.length);
  });
});
