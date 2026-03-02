"use client";

import { Suspense, useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { EvalRun, EvalResult } from "@/lib/types";
import {
  EVAL_FIELDS as PASS1_FIELDS,
  formatFieldValue,
  formatRunLabel,
  getParsedResult,
} from "@/lib/eval-utils";

type VoteWinner = "a" | "b" | "tie" | "both_bad";

const VOTE_BUTTONS: { label: string; value: VoteWinner }[] = [
  { label: "A is Better", value: "a" },
  { label: "B is Better", value: "b" },
  { label: "Tie", value: "tie" },
  { label: "Both Bad", value: "both_bad" },
];

const VOTE_KEY_MAP: Record<string, VoteWinner> = {
  a: "a",
  b: "b",
  t: "tie",
  x: "both_bad",
};

function FieldComparisonPanel({
  label,
  fields,
  otherFields,
}: {
  label: string;
  fields: Record<string, unknown>;
  otherFields: Record<string, unknown>;
}) {
  return (
    <div
      className="rounded-lg border"
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
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
            fontSize: "14px",
            color: "#2D3142",
          }}
        >
          {label}
        </h3>
      </div>
      <div className="p-1">
        {PASS1_FIELDS.map((field) => {
          const val = formatFieldValue(fields[field]);
          const otherVal = formatFieldValue(otherFields[field]);
          const disagree = val !== otherVal;
          return (
            <div
              key={field}
              className="flex items-baseline justify-between border-b border-[#BFC0C04D] px-4 py-2 last:border-0"
            >
              <span
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "12px",
                  fontWeight: disagree ? 500 : undefined,
                  color: disagree ? "#A07D28" : "#4F5D75",
                }}
              >
                {field}
              </span>
              <span
                style={{
                  fontFamily:
                    "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                  fontSize: "13px",
                  color: disagree ? "#A07D28" : "#2D3142",
                  maxWidth: "60%",
                  wordBreak: "break-word",
                  textAlign: "right",
                }}
              >
                {val}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReviewPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runAId, setRunAId] = useState<string | null>(
    () => searchParams.get("runA"),
  );
  const [runBId, setRunBId] = useState<string | null>(
    () => searchParams.get("runB"),
  );

  const [resultsA, setResultsA] = useState<EvalResult[]>([]);
  const [resultsB, setResultsB] = useState<EvalResult[]>([]);
  const [corpus, setCorpus] = useState<
    Array<{ id: string; title: string; content: string }>
  >([]);
  const [dataLoading, setDataLoading] = useState(false);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [votes, setVotes] = useState<Record<string, VoteWinner>>({});
  const [voteError, setVoteError] = useState<string | null>(null);

  const [lastSavedPostingId, setLastSavedPostingId] = useState<string | null>(
    null,
  );
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [swapMap, setSwapMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    setRunsLoading(true);
    api
      .listEvalRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setRunsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const passMismatch = useMemo(() => {
    if (!runAId || !runBId) return false;
    const runA = runs.find((r) => r.id === runAId);
    const runB = runs.find((r) => r.id === runBId);
    return !!(runA && runB && runA.pass_number !== runB.pass_number);
  }, [runs, runAId, runBId]);

  useEffect(() => {
    if (!runAId || !runBId) {
      setResultsA([]);
      setResultsB([]);
      setCorpus([]);
      setCurrentIndex(0);
      setVotes({});
      setNotes("");
      setSwapMap({});
      setDataLoading(false);
      return;
    }
    if (runs.length === 0) return;

    const runA = runs.find((r) => r.id === runAId);
    const runB = runs.find((r) => r.id === runBId);
    if (runA && runB && runA.pass_number !== runB.pass_number) {
      setDataLoading(false);
      return;
    }

    let cancelled = false;
    setDataLoading(true);

    Promise.all([
      api.getEvalResults(runAId),
      api.getEvalResults(runBId),
      api.getEvalCorpus(),
      api.listComparisons(),
    ])
      .then(([rA, rB, corpusData, existingComparisons]) => {
        if (cancelled) return;
        setResultsA(rA);
        setResultsB(rB);
        setCorpus(corpusData);
        setCurrentIndex(0);
        setNotes("");

        const resultIdsA = new Set(rA.map((r) => r.id));
        const resultIdsB = new Set(rB.map((r) => r.id));

        const restoredVotes: Record<string, VoteWinner> = {};
        for (const comp of existingComparisons) {
          const aInRunA =
            resultIdsA.has(comp.result_a_id) &&
            resultIdsB.has(comp.result_b_id);
          const aInRunB =
            resultIdsA.has(comp.result_b_id) &&
            resultIdsB.has(comp.result_a_id);
          if (aInRunA || aInRunB) {
            restoredVotes[comp.posting_id] = comp.winner;
          }
        }
        setVotes(restoredVotes);

        const idsA = new Set(rA.map((r) => r.posting_id));
        const commonIds = rB
          .map((r) => r.posting_id)
          .filter((id) => idsA.has(id));
        const newSwapMap: Record<string, boolean> = {};
        for (const id of commonIds) {
          newSwapMap[id] = Math.random() > 0.5;
        }
        setSwapMap(newSwapMap);
      })
      .catch(() => {
        if (!cancelled) {
          setResultsA([]);
          setResultsB([]);
          setCorpus([]);
          setSwapMap({});
        }
      })
      .finally(() => {
        if (!cancelled) setDataLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [runAId, runBId, runs]);

  const commonPostings = useMemo(() => {
    const mapA = new Map(resultsA.map((r) => [r.posting_id, r]));
    const mapB = new Map(resultsB.map((r) => [r.posting_id, r]));
    const corpusMap = new Map(corpus.map((c) => [c.id, c]));

    const common: {
      postingId: string;
      resultA: EvalResult;
      resultB: EvalResult;
      posting: { id: string; title: string; content: string } | undefined;
    }[] = [];

    for (const [postingId, rA] of mapA) {
      const rB = mapB.get(postingId);
      if (rB) {
        common.push({
          postingId,
          resultA: rA,
          resultB: rB,
          posting: corpusMap.get(postingId),
        });
      }
    }
    return common;
  }, [resultsA, resultsB, corpus]);

  const totalComparisons = commonPostings.length;
  const currentItem = commonPostings[currentIndex] ?? null;

  const displayedPair = useMemo(() => {
    if (!currentItem) return null;
    const shouldSwap = swapMap[currentItem.postingId] ?? false;
    if (shouldSwap) {
      return {
        displayA: currentItem.resultB,
        displayB: currentItem.resultA,
        actualAIsRunA: false,
      };
    }
    return {
      displayA: currentItem.resultA,
      displayB: currentItem.resultB,
      actualAIsRunA: true,
    };
  }, [currentItem, swapMap]);

  const runALabel = useMemo(() => {
    const run = runs.find((r) => r.id === runAId);
    return run ? formatRunLabel(run) : "Run A";
  }, [runs, runAId]);

  const runBLabel = useMemo(() => {
    const run = runs.find((r) => r.id === runBId);
    return run ? formatRunLabel(run) : "Run B";
  }, [runs, runBId]);

  const displayALabel = displayedPair?.actualAIsRunA ? runALabel : runBLabel;
  const displayBLabel = displayedPair?.actualAIsRunA ? runBLabel : runALabel;

  const fieldsA = useMemo(
    () => (displayedPair ? getParsedResult(displayedPair.displayA) : {}),
    [displayedPair],
  );
  const fieldsB = useMemo(
    () => (displayedPair ? getParsedResult(displayedPair.displayB) : {}),
    [displayedPair],
  );

  const allVoted =
    totalComparisons > 0 && Object.keys(votes).length >= totalComparisons;

  const goNext = useCallback(() => {
    if (currentIndex < totalComparisons - 1) {
      setCurrentIndex((i) => i + 1);
      setNotes("");
    }
  }, [currentIndex, totalComparisons]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
      setNotes("");
    }
  }, [currentIndex]);

  const syncRunParams = useCallback(
    (aId: string | null, bId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (aId) params.set("runA", aId);
      else params.delete("runA");
      if (bId) params.set("runB", bId);
      else params.delete("runB");
      router.replace(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );

  const handleVote = useCallback(
    async (winner: VoteWinner) => {
      if (!currentItem || !displayedPair || submitting) return;
      setSubmitting(true);
      setVoteError(null);

      try {
        await api.recordComparison({
          posting_id: currentItem.postingId,
          result_a_id: displayedPair.displayA.id,
          result_b_id: displayedPair.displayB.id,
          winner,
          notes: notes.trim() || undefined,
        });

        setVotes((prev) => ({ ...prev, [currentItem.postingId]: winner }));
        if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
        setLastSavedPostingId(currentItem.postingId);
        savedTimerRef.current = setTimeout(
          () => setLastSavedPostingId(null),
          800,
        );
        setNotes("");

        if (currentIndex < totalComparisons - 1) {
          setCurrentIndex((i) => i + 1);
        }
      } catch (err) {
        setVoteError(
          err instanceof Error ? err.message : "Failed to save vote",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [
      currentItem,
      displayedPair,
      submitting,
      notes,
      currentIndex,
      totalComparisons,
    ],
  );

  useEffect(() => {
    if (!currentItem || totalComparisons === 0 || passMismatch) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.tagName === "INPUT"
      )
        return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const voteWinner = VOTE_KEY_MAP[e.key];
      if (voteWinner) {
        e.preventDefault();
        void handleVote(voteWinner);
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [currentItem, totalComparisons, passMismatch, handleVote, goPrev, goNext]);

  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  const progressPct =
    totalComparisons > 0
      ? ((Object.keys(votes).length / totalComparisons) * 100).toFixed(1)
      : "0";

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          }}
        >
          Review
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          Head-to-head comparison of extraction quality
        </p>
      </div>

      {/* Run selectors */}
      <div
        className="rounded-lg border p-5"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
          borderRadius: "var(--radius-lg, 8px)",
        }}
      >
        <h3
          className="mb-4 font-semibold"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
            fontSize: "14px",
            color: "#2D3142",
          }}
        >
          Select Runs to Compare
        </h3>
        <div className="flex flex-col gap-4 sm:flex-row">
          {(
            [
              {
                id: "run-a-select",
                label: "Run A",
                value: runAId,
                other: runBId,
                onChange: (id: string | null) => {
                  setRunAId(id);
                  syncRunParams(id, runBId);
                },
              },
              {
                id: "run-b-select",
                label: "Run B",
                value: runBId,
                other: runAId,
                onChange: (id: string | null) => {
                  setRunBId(id);
                  syncRunParams(runAId, id);
                },
              },
            ] as const
          ).map((sel) => (
            <div key={sel.id} className="flex flex-1 flex-col gap-1">
              <label
                htmlFor={sel.id}
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "12px",
                  fontWeight: 500,
                  color: "#4F5D75",
                }}
              >
                {sel.label}
              </label>
              <select
                id={sel.id}
                value={sel.value ?? ""}
                onChange={(e) => {
                  sel.onChange(e.target.value || null);
                }}
                disabled={runsLoading}
                className="rounded border px-2 py-1.5"
                style={{
                  borderColor: "#BFC0C0",
                  backgroundColor: "#FFFFFF",
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "13px",
                  color: "#2D3142",
                  borderRadius: "var(--radius-sm, 4px)",
                }}
              >
                <option value="">
                  {runsLoading
                    ? "Loading runs\u2026"
                    : "Select a run\u2026"}
                </option>
                {runs.map((run) => (
                  <option
                    key={run.id}
                    value={run.id}
                    disabled={run.id === sel.other}
                  >
                    {formatRunLabel(run)}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>

      {passMismatch && (
        <div
          className="mt-4 rounded-lg border px-4 py-3 text-sm"
          role="alert"
          style={{
            backgroundColor: "#8C2C231A",
            borderColor: "#8C2C2330",
            color: "#8C2C23",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            borderRadius: "var(--radius-sm, 4px)",
          }}
        >
          Cannot compare runs with different pass numbers.
        </div>
      )}

      {(!runAId || !runBId) && (
        <div
          className="mt-6 flex items-center justify-center rounded-lg border border-dashed py-12"
          style={{
            borderColor: "#BFC0C0",
            backgroundColor: "#FFFFFF",
            borderRadius: "var(--radius-lg, 8px)",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            Select two runs above to begin reviewing comparisons.
          </p>
        </div>
      )}

      {runAId && runBId && !passMismatch && dataLoading && (
        <div
          className="mt-6 flex items-center justify-center rounded-lg border py-12"
          style={{
            borderColor: "#BFC0C0",
            backgroundColor: "#FFFFFF",
            borderRadius: "var(--radius-lg, 8px)",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            Loading results\u2026
          </p>
        </div>
      )}

      {runAId &&
        runBId &&
        !passMismatch &&
        !dataLoading &&
        totalComparisons === 0 && (
          <div
            className="mt-6 flex items-center justify-center rounded-lg border border-dashed py-12"
            style={{
              borderColor: "#BFC0C0",
              backgroundColor: "#FFFFFF",
              borderRadius: "var(--radius-lg, 8px)",
            }}
          >
            <p
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#4F5D75",
              }}
            >
              No common postings found between these two runs.
            </p>
          </div>
        )}

      {runAId &&
        runBId &&
        !passMismatch &&
        !dataLoading &&
        totalComparisons > 0 && (
          <>
            {/* Posting context */}
            <div
              className="mt-6 rounded-lg border p-5"
              style={{
                backgroundColor: "#FFFFFF",
                borderColor: "#BFC0C0",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-lg, 8px)",
              }}
            >
              <div className="mb-3 flex items-center justify-between">
                <h3
                  className="font-semibold"
                  style={{
                    fontFamily:
                      "var(--font-display, 'Sora Variable', sans-serif)",
                    fontSize: "14px",
                    color: "#2D3142",
                  }}
                >
                  Posting Context
                </h3>
                <div className="flex items-center gap-3">
                  <button
                    onClick={goPrev}
                    disabled={currentIndex === 0}
                    className="rounded border px-2.5 py-1 text-xs font-medium transition-colors duration-150 disabled:opacity-40"
                    style={{
                      borderColor: "#BFC0C0",
                      color: "#4F5D75",
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      borderRadius: "var(--radius-sm, 4px)",
                    }}
                  >
                    Prev
                  </button>
                  <span
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "12px",
                      color: "#4F5D75",
                    }}
                  >
                    {currentIndex + 1} of {totalComparisons}
                  </span>
                  <button
                    onClick={goNext}
                    disabled={currentIndex >= totalComparisons - 1}
                    className="rounded border px-2.5 py-1 text-xs font-medium transition-colors duration-150 disabled:opacity-40"
                    style={{
                      borderColor: "#BFC0C0",
                      color: "#4F5D75",
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      borderRadius: "var(--radius-sm, 4px)",
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
              <div>
                <p
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "13px",
                    fontWeight: 500,
                    color: "#2D3142",
                  }}
                >
                  {currentItem?.posting?.title ?? currentItem?.postingId}
                </p>
                {currentItem?.postingId && !currentItem.posting && (
                  <p
                    style={{
                      fontFamily:
                        "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                      fontSize: "11px",
                      color: "#4F5D75",
                      marginTop: "2px",
                    }}
                  >
                    {currentItem.postingId}
                  </p>
                )}
              </div>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#E8E8E4]">
                <div
                  className="h-full rounded-full transition-[width] duration-500"
                  style={{
                    width: `${progressPct}%`,
                    backgroundColor: "#EF8354",
                  }}
                />
              </div>
              <div className="mt-1.5 flex items-center justify-between">
                <span
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "11px",
                    color: "#4F5D75",
                  }}
                >
                  {Object.keys(votes).length} of {totalComparisons} voted
                </span>
                {votes[currentItem?.postingId ?? ""] && (
                  <span
                    style={{
                      fontFamily:
                        "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                      fontSize: "11px",
                      fontWeight: 500,
                      color: "#EF8354",
                    }}
                  >
                    &#x2713; Voted
                  </span>
                )}
              </div>
            </div>

            {/* Two-column comparison */}
            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <FieldComparisonPanel
                label={displayALabel}
                fields={fieldsA}
                otherFields={fieldsB}
              />
              <FieldComparisonPanel
                label={displayBLabel}
                fields={fieldsB}
                otherFields={fieldsA}
              />
            </div>

            <p
              className="mt-4 text-center"
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                color: "#4F5D7580",
              }}
            >
              Sides are randomized per posting to reduce bias.
            </p>

            {/* Vote section */}
            <div
              className="mt-6 rounded-lg border p-5"
              style={{
                backgroundColor: "#FFFFFF",
                borderColor: "#BFC0C0",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-lg, 8px)",
              }}
            >
              <h3
                className="mb-4 flex items-center gap-2 font-semibold"
                style={{
                  fontFamily:
                    "var(--font-display, 'Sora Variable', sans-serif)",
                  fontSize: "14px",
                  color: "#2D3142",
                }}
              >
                Which extraction is better?
                {lastSavedPostingId && (
                  <span
                    className="animate-pulse"
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "11px",
                      fontWeight: 400,
                      color: "#1B998B",
                    }}
                  >
                    &#x2713; Saved
                  </span>
                )}
              </h3>
              <div className="mb-4">
                <label
                  htmlFor="comparison-notes"
                  className="mb-1 block"
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    fontWeight: 500,
                    color: "#4F5D75",
                  }}
                >
                  Notes (optional)
                </label>
                <textarea
                  id="comparison-notes"
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any observations about this comparison\u2026"
                  className="w-full rounded border px-3 py-2 focus:outline-none"
                  style={{
                    borderColor: "#BFC0C0",
                    backgroundColor: "#FFFFFF",
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "13px",
                    color: "#2D3142",
                    borderRadius: "var(--radius-sm, 4px)",
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {VOTE_BUTTONS.map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => void handleVote(value)}
                    disabled={submitting}
                    className="rounded border border-[#BFC0C0] px-4 py-2.5 font-medium transition-colors duration-150 hover:border-[#EF8354] disabled:cursor-not-allowed disabled:opacity-50"
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "13px",
                      color: "#2D3142",
                      borderRadius: "var(--radius-sm, 4px)",
                    }}
                  >
                    {submitting ? "\u2026" : label}
                  </button>
                ))}
              </div>
              {voteError && (
                <p
                  className="mt-3"
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    color: "#8C2C23",
                  }}
                >
                  {voteError}
                </p>
              )}
              <div className="mt-3 border-t border-[#BFC0C0] pt-2">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {[
                    ["A", "A Better"],
                    ["B", "B Better"],
                    ["T", "Tie"],
                    ["X", "Both Bad"],
                    ["\u2190", "Prev"],
                    ["\u2192", "Next"],
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
              {allVoted && (
                <div
                  className="mt-4 flex items-center justify-between rounded-md border px-4 py-2.5"
                  style={{
                    backgroundColor: "#1B998B1A",
                    borderColor: "#1B998B30",
                    borderRadius: "var(--radius-sm, 4px)",
                  }}
                >
                  <span
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "#1B998B",
                    }}
                  >
                    All {totalComparisons} comparisons complete
                  </span>
                  <Link
                    href="/eval/leaderboard"
                    style={{
                      fontFamily:
                        "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "#EF8354",
                      textDecoration: "none",
                    }}
                  >
                    View updated rankings &#x2192;
                  </Link>
                </div>
              )}
            </div>
          </>
        )}
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<div style={{ padding: "24px", color: "#4F5D75" }}>Loading&hellip;</div>}>
      <ReviewPageContent />
    </Suspense>
  );
}
