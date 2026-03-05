"use client";

import { Suspense, useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRunsApiV1EvalRunsGetOptions,
  getRunResultsApiV1EvalRunsRunIdResultsGetOptions,
  getRunResultsApiV1EvalRunsRunIdResultsGetQueryKey,
  createFieldReviewApiV1EvalFieldReviewsPostMutation
} from "@/api-client/@tanstack/react-query.gen";
import type { EvalRun, EvalResult } from "@/lib/types";
import {
  EVAL_FIELDS as REVIEWABLE_FIELDS,
  formatFieldValue,
  formatRunLabel,
  getParsedResult,
} from "@/lib/eval-utils";

type ReviewOutcome = "correct" | "incorrect" | "cant_assess" | "pending";

interface FieldReviewState {
  outcome: ReviewOutcome;
}

function accuracyColor(pct: number): string {
  if (pct >= 80) return "text-[#1B998B]";
  if (pct >= 50) return "text-[#A07D28]";
  return "text-[#8C2C23]";
}

function outcomeColor(outcome: ReviewOutcome): string {
  if (outcome === "correct") return "text-[#1B998B]";
  if (outcome === "incorrect") return "text-[#8C2C23]";
  if (outcome === "cant_assess") return "text-[#4F5D75]";
  return "text-[#BFC0C0]";
}

function outcomeBg(outcome: ReviewOutcome): string {
  if (outcome === "correct") return "bg-[#1B998B1A]";
  if (outcome === "incorrect") return "bg-[#8C2C231A]";
  if (outcome === "cant_assess") return "bg-[#4F5D751A]";
  return "bg-[#E8E8E4]";
}

function outcomeLabel(outcome: ReviewOutcome): string {
  if (outcome === "correct") return "Correct";
  if (outcome === "incorrect") return "Incorrect";
  if (outcome === "cant_assess") return "Can't Assess";
  return "Pending";
}

interface FieldAccuracyRow {
  field: string;
  correct: number;
  incorrect: number;
  cantAssess: number;
  total: number;
}

function AccuracyContent() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const selectedRunId = searchParams.get("run");
  const [postingIdx, setPostingIdx] = useState(0);
  const [focusedFieldIdx, setFocusedFieldIdx] = useState(0);
  const [savedField, setSavedField] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: runs = [] } = useQuery({
    ...getRunsApiV1EvalRunsGetOptions(),
    select: (data) => data as unknown as EvalRun[],
  });

  const { data: results = [], isLoading: resultsLoading } = useQuery({
    ...getRunResultsApiV1EvalRunsRunIdResultsGetOptions({
      path: { run_id: selectedRunId! },
    }),
    enabled: !!selectedRunId,
    select: (data) => data as unknown as EvalResult[],
  });

  const reviewMap = useMemo(() => {
    const map: Record<string, Record<string, FieldReviewState>> = {};
    for (const res of results) {
      map[res.id] = {};
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if ((res as any).field_reviews) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        for (const fr of (res as any).field_reviews) {
          const outcome: ReviewOutcome = fr.is_correct === 1 ? "correct" : fr.is_correct === -1 ? "cant_assess" : "incorrect";
          map[res.id][fr.field_name] = { outcome };
        }
      }
    }
    return map;
  }, [results]);

  const currentResult = results[postingIdx];
  const parsedResult = useMemo(() => (currentResult ? getParsedResult(currentResult) : {}), [currentResult]);
  const currentReviews = useMemo(() => (currentResult ? reviewMap[currentResult.id] ?? {} : {}), [reviewMap, currentResult]);

  const reviewMutation = useMutation({
    ...createFieldReviewApiV1EvalFieldReviewsPostMutation(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: getRunResultsApiV1EvalRunsRunIdResultsGetQueryKey({ path: { run_id: selectedRunId! } }) });
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setSavedField((variables as any).body.field_name);
      savedTimerRef.current = setTimeout(() => setSavedField(null), 600);
    },
  });

  const handleJudgment = useCallback(
    (field: string, outcome: ReviewOutcome) => {
      if (!currentResult || reviewMutation.isPending) return;
      const isCorrect = outcome === "correct" ? 1 : outcome === "cant_assess" ? -1 : 0;
      reviewMutation.mutate({
        body: {
          result_id: currentResult.id,
          field_name: field,
          is_correct: isCorrect,
          model_value: formatFieldValue(parsedResult[field]),
        }
      });
    },
    [currentResult, reviewMutation, parsedResult]
  );

  const fieldAccuracyRows: FieldAccuracyRow[] = useMemo(() => {
    const counters: Record<string, { correct: number; incorrect: number; cantAssess: number }> = {};
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
      total: counters[field].correct + counters[field].incorrect + counters[field].cantAssess,
    }));
  }, [results, reviewMap]);

  const handleRunChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    const params = new URLSearchParams(searchParams.toString());
    if (val) params.set("run", val);
    else params.delete("run");
    router.replace(`${pathname}?${params.toString()}`);
    setPostingIdx(0);
  };

  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId || results.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "SELECT" || target.tagName === "TEXTAREA" || target.tagName === "INPUT") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const field = REVIEWABLE_FIELDS[focusedFieldIdx];

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          setFocusedFieldIdx((p) => Math.max(0, p - 1));
          break;
        case "ArrowDown":
          e.preventDefault();
          setFocusedFieldIdx((p) => Math.min(REVIEWABLE_FIELDS.length - 1, p + 1));
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
          if (field) handleJudgment(field, "correct");
          break;
        case "i":
          if (field) handleJudgment(field, "incorrect");
          break;
        case "n":
          if (field) handleJudgment(field, "cant_assess");
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedRunId, results.length, focusedFieldIdx, postingIdx, handleJudgment]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Accuracy
        </h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">
          Field-level extraction review and accuracy metrics
        </p>
      </div>

      <div className="rounded-lg border border-[#BFC0C0] p-5 bg-white shadow-sm">
        <label htmlFor="run-select" className="mb-2 block font-body text-xs font-medium text-[#4F5D75]">
          Select Run
        </label>
        <select
          id="run-select"
          value={selectedRunId ?? ""}
          onChange={handleRunChange}
          className="w-full rounded border border-[#BFC0C0] px-3 py-2 bg-white font-body text-[13px] text-[#2D3142] focus:outline-none focus:ring-1 focus:ring-[#EF8354]"
        >
          <option value="">
            Choose a run\u2026
          </option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {formatRunLabel(run)}
            </option>
          ))}
        </select>
      </div>

      {selectedRunId && resultsLoading && (
        <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          Loading results\u2026
        </div>
      )}

      {selectedRunId && !resultsLoading && results.length === 0 && (
        <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          No results found for this run.
        </div>
      )}

      {!selectedRunId && (
        <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          Select a run to begin reviewing field accuracy.
        </div>
      )}

      {selectedRunId && results.length > 0 && (
        <>
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setPostingIdx((p) => Math.max(0, p - 1))}
              disabled={postingIdx === 0}
              className="rounded border border-[#BFC0C0] px-3 py-1.5 font-body text-[13px] font-medium text-[#2D3142] bg-white transition-colors duration-150 hover:bg-[#E8E8E4] disabled:opacity-40 disabled:hover:bg-white"
            >
              &larr; Prev
            </button>
            <span className="font-body text-xs text-[#4F5D75]">
              Posting {postingIdx + 1} of {results.length}
            </span>
            <button
              onClick={() => setPostingIdx((p) => Math.min(results.length - 1, p + 1))}
              disabled={postingIdx >= results.length - 1}
              className="rounded border border-[#BFC0C0] px-3 py-1.5 font-body text-[13px] font-medium text-[#2D3142] bg-white transition-colors duration-150 hover:bg-[#E8E8E4] disabled:opacity-40 disabled:hover:bg-white"
            >
              Next &rarr;
            </button>
          </div>

          <div className="mt-4 rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
            <div className="border-b border-[#BFC0C0] px-5 py-3">
              <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                Field Judgments
              </h3>
              {currentResult && (
                <p className="font-mono text-[11px] text-[#4F5D75] mt-0.5">
                  Result {currentResult.id}
                </p>
              )}
            </div>

            {reviewMutation.isError && (
              <div className="mx-3 mt-2 rounded border border-[#8C2C2330] px-3 py-1.5 bg-[#8C2C231A] text-[#8C2C23] font-body text-xs">
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {(reviewMutation.error as any).message || "Failed to save review"}
              </div>
            )}

            <div className="divide-y divide-[#BFC0C01A]">
              {REVIEWABLE_FIELDS.map((field, idx) => {
                const modelVal = parsedResult[field];
                const review = currentReviews[field];
                const outcome: ReviewOutcome = review?.outcome ?? "pending";
                const isFocused = focusedFieldIdx === idx;
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const isBusy = reviewMutation.isPending && (reviewMutation.variables as any)?.body?.field_name === field;

                return (
                  <div
                    key={field}
                    onClick={() => setFocusedFieldIdx(idx)}
                    className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors border-l-2 ${
                      isFocused ? 'border-l-[#EF8354] bg-[#EF83540A]' : 'border-l-transparent'
                    }`}
                  >
                    <div className="w-[22%] shrink-0">
                      <span className="font-body text-[11px] text-[#4F5D75]">
                        {field}
                      </span>
                      {isFocused && (
                        <div className="flex gap-0.5 mt-0.5 font-mono text-[9px] text-[#4F5D75]/40">
                          {["c", "i", "n"].map((k) => <span key={k}>[{k}]</span>)}
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <span className="block truncate font-mono text-xs text-[#2D3142]">
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
                            handleJudgment(field, key);
                          }}
                          disabled={isBusy}
                          className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium transition-colors border ${
                            outcome === key 
                              ? `${outcomeColor(key)} ${outcomeBg(key)} border-current` 
                              : 'text-[#4F5D75] bg-[#E8E8E4] border-[#BFC0C0]'
                          } disabled:opacity-40`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>

                    <div className="shrink-0 w-14 text-right">
                      {savedField === field ? (
                        <span className="animate-pulse font-mono text-[11px] font-medium text-[#1B998B]">
                          &#x2713;
                        </span>
                      ) : (
                        <span className={`font-body text-[10px] ${outcomeColor(outcome)}`}>
                          {outcomeLabel(outcome)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="border-t border-[#BFC0C0] px-4 py-2 bg-[#E8E8E41A]">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {[
                  ["C", "Correct"],
                  ["I", "Incorrect"],
                  ["N", "N/A"],
                  ["\u2191\u2193", "Field"],
                  ["\u2190\u2192", "Posting"],
                ].map(([key, lbl]) => (
                  <span key={key} className="flex items-center gap-1 font-body text-[10px] text-[#4F5D75]/50">
                    <kbd className="rounded border border-[#BFC0C0]/50 bg-[#E8E8E4] px-1 py-0.5 font-mono text-[10px] text-[#4F5D75]">
                      {key}
                    </kbd>
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {fieldAccuracyRows.some((r) => r.total > 0) && (
            <div className="mt-6 rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
              <div className="border-b border-[#BFC0C0] px-5 py-3">
                <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                  Accuracy Summary
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Field accuracy summary">
                  <thead>
                    <tr className="border-b border-[#BFC0C0] bg-[#E8E8E41A]">
                      {[
                        "Field",
                        "Correct",
                        "Incorrect",
                        "Can't Assess",
                        "Accuracy %",
                      ].map((h) => (
                        <th
                          key={h}
                          className="pb-3 pl-5 pt-4 pr-4 text-left last:text-right font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#BFC0C01A]">
                    {fieldAccuracyRows
                      .filter((r) => r.total > 0)
                      .map((row) => {
                        const pct = Math.round((row.correct / row.total) * 100);
                        return (
                          <tr key={row.field} className="hover:bg-[#E8E8E40D]">
                            <td className="py-2.5 pl-5 pr-4 font-body text-xs text-[#4F5D75]">
                              {row.field}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-xs text-[#1B998B]">
                              {row.correct}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-xs text-[#8C2C23]">
                              {row.incorrect}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-xs text-[#4F5D75]">
                              {row.cantAssess}
                            </td>
                            <td className={`py-2.5 pl-4 pr-5 text-right font-mono text-xs font-semibold ${accuracyColor(pct)}`}>
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
    </div>
  );
}

export default function AccuracyPage() {
  return (
    <Suspense fallback={<div className="p-6 font-body text-[#4F5D75]">Loading&hellip;</div>}>
      <AccuracyContent />
    </Suspense>
  );
}
