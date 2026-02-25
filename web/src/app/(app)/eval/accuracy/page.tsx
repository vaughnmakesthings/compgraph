"use client";

import { Suspense, useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api-client";
import type { EvalRun, EvalResult } from "@/lib/types";

const REVIEWABLE_FIELDS = [
  "role_archetype",
  "role_level",
  "employment_type",
  "pay_type",
  "pay_frequency",
  "pay_min",
  "pay_max",
  "has_commission",
  "has_benefits",
  "travel_required",
  "store_count",
  "tools_mentioned",
  "kpis_mentioned",
] as const;

type ReviewOutcome = "correct" | "incorrect" | "cant_assess" | "pending";

interface FieldReviewState {
  outcome: ReviewOutcome;
  note?: string;
}

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "\u2014";
  if (Array.isArray(value))
    return value.length === 0 ? "\u2014" : value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getParsedResult(result: EvalResult): Record<string, unknown> {
  if (!result.parsed_result) return {};
  if (typeof result.parsed_result === "object")
    return result.parsed_result as Record<string, unknown>;
  try {
    return JSON.parse(String(result.parsed_result)) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function accuracyColor(pct: number): string {
  if (pct >= 80) return "#1B998B";
  if (pct >= 50) return "#A07D28";
  return "#8C2C23";
}

function outcomeColor(outcome: ReviewOutcome): string {
  if (outcome === "correct") return "#1B998B";
  if (outcome === "incorrect") return "#8C2C23";
  if (outcome === "cant_assess") return "#4F5D75";
  return "#BFC0C0";
}

function outcomeLabel(outcome: ReviewOutcome): string {
  if (outcome === "correct") return "Correct";
  if (outcome === "incorrect") return "Incorrect";
  if (outcome === "cant_assess") return "Can't Assess";
  return "Pending";
}

function formatRunLabel(run: EvalRun): string {
  return `${run.model} / ${run.prompt_version} \u00B7 Pass ${run.pass_number}`;
}

interface FieldAccuracyRow {
  field: string;
  correct: number;
  incorrect: number;
  cantAssess: number;
  total: number;
}

function AccuracyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    () => searchParams.get("run"),
  );
  const [results, setResults] = useState<EvalResult[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // Local review state: result_id -> field -> outcome
  const [reviewMap, setReviewMap] = useState<
    Record<string, Record<string, FieldReviewState>>
  >({});

  const [postingIdx, setPostingIdx] = useState(0);
  const [focusedFieldIdx, setFocusedFieldIdx] = useState(0);
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [savedField, setSavedField] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listEvalRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingRuns(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    let cancelled = false;
    setLoadingData(true);
    setPostingIdx(0);
    api
      .getEvalResults(selectedRunId)
      .then((data) => {
        if (!cancelled) setResults(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingData(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  useEffect(() => {
    setFocusedFieldIdx(0);
  }, [postingIdx]);

  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  const currentResult: EvalResult | undefined = results[postingIdx];
  const parsedResult = useMemo(
    () => (currentResult ? getParsedResult(currentResult) : {}),
    [currentResult],
  );

  const currentReviews = useMemo(() => {
    if (!currentResult) return {} as Record<string, FieldReviewState>;
    return reviewMap[currentResult.id] ?? {};
  }, [reviewMap, currentResult]);

  const handleJudgment = useCallback(
    async (field: string, outcome: ReviewOutcome) => {
      if (!currentResult) return;
      const key = `${currentResult.id}-${field}`;
      setReviewError(null);
      setSubmitting((p) => ({ ...p, [key]: true }));

      const isCorrect =
        outcome === "correct" ? 1 : outcome === "cant_assess" ? -1 : 0;

      try {
        await api.upsertFieldReview({
          result_id: currentResult.id,
          field_name: field,
          is_correct: isCorrect,
        });

        setReviewMap((prev) => ({
          ...prev,
          [currentResult.id]: {
            ...(prev[currentResult.id] ?? {}),
            [field]: { outcome },
          },
        }));

        if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
        setSavedField(field);
        savedTimerRef.current = setTimeout(() => setSavedField(null), 600);
      } catch (err) {
        setReviewError(
          err instanceof Error ? err.message : "Failed to save review",
        );
      } finally {
        setSubmitting((p) => ({ ...p, [key]: false }));
      }
    },
    [currentResult],
  );

  // Aggregate accuracy across all reviewed results
  const fieldAccuracyRows: FieldAccuracyRow[] = useMemo(() => {
    const counters: Record<
      string,
      { correct: number; incorrect: number; cantAssess: number }
    > = {};
    for (const field of REVIEWABLE_FIELDS) {
      counters[field] = { correct: 0, incorrect: 0, cantAssess: 0 };
    }
    for (const result of results) {
      const rMap = reviewMap[result.id] ?? {};
      for (const field of REVIEWABLE_FIELDS) {
        const r = rMap[field];
        if (!r) continue;
        if (r.outcome === "correct") counters[field].correct += 1;
        else if (r.outcome === "incorrect") counters[field].incorrect += 1;
        else if (r.outcome === "cant_assess") counters[field].cantAssess += 1;
      }
    }
    return REVIEWABLE_FIELDS.map((field) => ({
      field,
      correct: counters[field].correct,
      incorrect: counters[field].incorrect,
      cantAssess: counters[field].cantAssess,
      total:
        counters[field].correct +
        counters[field].incorrect +
        counters[field].cantAssess,
    }));
  }, [results, reviewMap]);

  const handleRunChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    setSelectedRunId(val);
    const params = new URLSearchParams(searchParams.toString());
    if (val) params.set("run", val);
    else params.delete("run");
    router.replace(`${pathname}?${params.toString()}`);
  };

  useEffect(() => {
    if (!selectedRunId || results.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "SELECT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "INPUT"
      )
        return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const field = REVIEWABLE_FIELDS[focusedFieldIdx];

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          setFocusedFieldIdx((p) => Math.max(0, p - 1));
          break;
        case "ArrowDown":
          e.preventDefault();
          setFocusedFieldIdx((p) =>
            Math.min(REVIEWABLE_FIELDS.length - 1, p + 1),
          );
          break;
        case "ArrowLeft":
          e.preventDefault();
          if (postingIdx > 0) setPostingIdx((p) => p - 1);
          break;
        case "ArrowRight":
          e.preventDefault();
          if (postingIdx < results.length - 1) setPostingIdx((p) => p + 1);
          break;
        case "c":
          if (field) void handleJudgment(field, "correct");
          break;
        case "i":
          if (field) void handleJudgment(field, "incorrect");
          break;
        case "n":
          if (field) void handleJudgment(field, "cant_assess");
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [
    selectedRunId,
    results.length,
    focusedFieldIdx,
    postingIdx,
    handleJudgment,
  ]);

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          }}
        >
          Accuracy
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          Field-level extraction review and accuracy metrics
        </p>
      </div>

      {/* Run selector */}
      <div
        className="rounded-lg border p-5"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
          borderRadius: "var(--radius-lg, 8px)",
        }}
      >
        <label
          htmlFor="run-select"
          className="mb-2 block"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            fontWeight: 500,
            color: "#4F5D75",
          }}
        >
          Select Run
        </label>
        <select
          id="run-select"
          value={selectedRunId ?? ""}
          onChange={handleRunChange}
          disabled={loadingRuns}
          className="w-full rounded border px-3 py-2 focus:outline-none"
          style={{
            borderColor: "#BFC0C0",
            backgroundColor: "#FFFFFF",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#2D3142",
            borderRadius: "var(--radius-sm, 4px)",
          }}
        >
          <option value="">
            {loadingRuns ? "Loading runs\u2026" : "Choose a run\u2026"}
          </option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {formatRunLabel(run)}
            </option>
          ))}
        </select>
      </div>

      {loadingData && (
        <div
          className="mt-6 flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          Loading results\u2026
        </div>
      )}

      {!selectedRunId && !loadingData && (
        <div
          className="mt-6 flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          Select a run to begin reviewing field accuracy.
        </div>
      )}

      {selectedRunId && !loadingData && results.length > 0 && (
        <>
          {/* Navigation */}
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setPostingIdx((p) => Math.max(0, p - 1))}
              disabled={postingIdx === 0}
              className="rounded border px-3 py-1.5 font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                borderColor: "#BFC0C0",
                backgroundColor: "#FFFFFF",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#2D3142",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-sm, 4px)",
              }}
            >
              &larr; Prev
            </button>
            <span
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                color: "#4F5D75",
              }}
            >
              Posting {postingIdx + 1} of {results.length}
            </span>
            <button
              onClick={() =>
                setPostingIdx((p) => Math.min(results.length - 1, p + 1))
              }
              disabled={postingIdx >= results.length - 1}
              className="rounded border px-3 py-1.5 font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                borderColor: "#BFC0C0",
                backgroundColor: "#FFFFFF",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#2D3142",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-sm, 4px)",
              }}
            >
              Next &rarr;
            </button>
          </div>

          {/* Field judgment panel */}
          <div
            className="mt-4 rounded-lg border"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
              borderRadius: "var(--radius-lg, 8px)",
            }}
          >
            <div className="border-b border-[#BFC0C0] px-5 py-3">
              <h3
                className="font-semibold"
                style={{
                  fontFamily:
                    "var(--font-display, 'Sora Variable', sans-serif)",
                  fontSize: "14px",
                  color: "#2D3142",
                }}
              >
                Field Judgments
              </h3>
              {currentResult && (
                <p
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    color: "#4F5D75",
                    marginTop: "2px",
                  }}
                >
                  Result {currentResult.id}
                </p>
              )}
            </div>

            {reviewError && (
              <div
                className="mx-3 mt-2 rounded border px-3 py-1.5"
                style={{
                  backgroundColor: "#8C2C231A",
                  borderColor: "#8C2C2330",
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "12px",
                  color: "#8C2C23",
                  borderRadius: "var(--radius-sm, 4px)",
                }}
              >
                {reviewError}
              </div>
            )}

            <div>
              {REVIEWABLE_FIELDS.map((field, idx) => {
                const modelVal = parsedResult[field];
                const review = currentReviews[field];
                const outcome: ReviewOutcome = review?.outcome ?? "pending";
                const isFocused = focusedFieldIdx === idx;
                const subKey = currentResult
                  ? `${currentResult.id}-${field}`
                  : field;
                const isBusy = submitting[subKey] ?? false;

                return (
                  <div
                    key={field}
                    onClick={() => setFocusedFieldIdx(idx)}
                    className="flex cursor-pointer items-center gap-3 border-b border-[#BFC0C033] px-4 py-2.5 last:border-0"
                    style={{
                      borderLeftWidth: "2px",
                      borderLeftStyle: "solid",
                      borderLeftColor: isFocused ? "#EF8354" : "transparent",
                      backgroundColor: isFocused ? "#EF83540A" : undefined,
                    }}
                  >
                    <div className="w-[22%] shrink-0">
                      <span
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          fontSize: "11px",
                          color: "#4F5D75",
                        }}
                      >
                        {field}
                      </span>
                      {isFocused && (
                        <div className="flex gap-0.5 mt-0.5">
                          {["c", "i", "n"].map((k) => (
                            <span
                              key={k}
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "9px",
                                color: "#4F5D7540",
                              }}
                            >
                              [{k}]
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <span
                        className="block truncate"
                        style={{
                          fontFamily:
                            "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                          fontSize: "12px",
                          color: "#2D3142",
                        }}
                      >
                        {formatFieldValue(modelVal)}
                      </span>
                    </div>

                    <div className="flex shrink-0 gap-1">
                      {(
                        [
                          { key: "correct", label: "C" },
                          { key: "incorrect", label: "I" },
                          { key: "cant_assess", label: "N/A" },
                        ] as const
                      ).map(({ key, label }) => (
                        <button
                          key={key}
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleJudgment(field, key);
                          }}
                          disabled={isBusy}
                          className="rounded px-1.5 py-0.5 font-medium transition-colors duration-150 disabled:opacity-40"
                          style={{
                            fontFamily:
                              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                            fontSize: "10px",
                            backgroundColor:
                              outcome === key ? outcomeColor(key) + "20" : "#E8E8E4",
                            color:
                              outcome === key ? outcomeColor(key) : "#4F5D75",
                            border: `1px solid ${outcome === key ? outcomeColor(key) + "40" : "#BFC0C0"}`,
                            borderRadius: "var(--radius-sm, 4px)",
                          }}
                        >
                          {label}
                        </button>
                      ))}
                    </div>

                    <div className="shrink-0 w-14 text-right">
                      {savedField === field ? (
                        <span
                          className="animate-pulse"
                          style={{
                            fontFamily:
                              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                            fontSize: "11px",
                            fontWeight: 500,
                            color: "#1B998B",
                          }}
                        >
                          &#x2713;
                        </span>
                      ) : (
                        <span
                          style={{
                            fontFamily:
                              "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "10px",
                            color: outcomeColor(outcome),
                          }}
                        >
                          {outcomeLabel(outcome)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="border-t border-[#BFC0C0] px-4 py-2">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {[
                  ["C", "Correct"],
                  ["I", "Incorrect"],
                  ["N", "N/A"],
                  ["\u2191\u2193", "Field"],
                  ["\u2190\u2192", "Posting"],
                ].map(([key, lbl]) => (
                  <span
                    key={key}
                    className="flex items-center gap-1"
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "10px",
                      color: "#4F5D7580",
                    }}
                  >
                    <kbd
                      className="rounded border px-1 py-0.5"
                      style={{
                        borderColor: "#BFC0C080",
                        backgroundColor: "#E8E8E4",
                        fontFamily:
                          "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                        fontSize: "10px",
                        color: "#4F5D75",
                      }}
                    >
                      {key}
                    </kbd>
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Accuracy summary table */}
          {fieldAccuracyRows.some((r) => r.total > 0) && (
            <div
              className="mt-6 rounded-lg border"
              style={{
                backgroundColor: "#FFFFFF",
                borderColor: "#BFC0C0",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-lg, 8px)",
              }}
            >
              <div className="border-b border-[#BFC0C0] px-5 py-3">
                <h3
                  className="font-semibold"
                  style={{
                    fontFamily:
                      "var(--font-display, 'Sora Variable', sans-serif)",
                    fontSize: "14px",
                    color: "#2D3142",
                  }}
                >
                  Accuracy Summary
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Field accuracy summary">
                  <thead>
                    <tr className="border-b border-[#BFC0C0]">
                      {[
                        "Field",
                        "Correct",
                        "Incorrect",
                        "Can't Assess",
                        "Accuracy %",
                      ].map((h) => (
                        <th
                          key={h}
                          className="pb-3 pl-5 pt-4 pr-4 text-left last:text-right"
                          style={{
                            fontFamily:
                              "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "11px",
                            fontWeight: 500,
                            color: "#4F5D75",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {fieldAccuracyRows
                      .filter((r) => r.total > 0)
                      .map((row) => {
                        const pct = Math.round(
                          (row.correct / row.total) * 100,
                        );
                        return (
                          <tr
                            key={row.field}
                            className="border-b border-[#BFC0C0] last:border-0"
                          >
                            <td
                              className="py-2.5 pl-5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "12px",
                                color: "#4F5D75",
                              }}
                            >
                              {row.field}
                            </td>
                            <td
                              className="py-2.5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                color: "#1B998B",
                              }}
                            >
                              {row.correct}
                            </td>
                            <td
                              className="py-2.5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                color: "#8C2C23",
                              }}
                            >
                              {row.incorrect}
                            </td>
                            <td
                              className="py-2.5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                color: "#4F5D75",
                              }}
                            >
                              {row.cantAssess}
                            </td>
                            <td
                              className="py-2.5 pl-4 pr-5 text-right"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                fontWeight: 600,
                                color: accuracyColor(pct),
                              }}
                            >
                              {pct}%
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {selectedRunId && !loadingData && results.length === 0 && (
        <div
          className="mt-6 flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          No results found for this run.
        </div>
      )}
    </div>
  );
}

export default function AccuracyPage() {
  return (
    <Suspense fallback={<div style={{ padding: "24px", color: "#4F5D75" }}>Loading&hellip;</div>}>
      <AccuracyContent />
    </Suspense>
  );
}
